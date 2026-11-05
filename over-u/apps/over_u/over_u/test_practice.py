import frappe
from frappe.utils import add_to_date, now_datetime

from lms.lms.test_helpers import BaseTestUtils
from over_u import points
from over_u import practice_api as practice
from over_u.school import TEACHER, manifest


class TestPractice(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		points.seed_rules()
		self.course = manifest()["course"]
		self.alice = self._create_user(
			"over-u-prac-alice@example.com", "Алиса", "Иванова", ["LMS Student"]
		).name
		self.bob = self._create_user("over-u-prac-bob@example.com", "Борис", "Петров", ["LMS Student"]).name
		self.stranger = self._create_user(
			"over-u-prac-stranger@example.com", "Чужой", "Тест", ["LMS Student"]
		).name
		for user in (self.alice, self.bob):
			frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": user}).insert()
		frappe.set_user(self.alice)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("OU Super Post", {"course": self.course})
		frappe.db.delete("OU Mastermind", {"course": self.course})
		for event in ("super_post", "mastermind_attended"):
			frappe.db.set_value("OU Points Rule", event, {"points": 0, "enabled": 0})
		frappe.db.delete("OU Points Entry", {"member": ["in", [self.alice, self.bob]]})
		super().tearDown()

	def _meeting(self, days=3, **extra):
		frappe.set_user(TEACHER)
		when = str(add_to_date(now_datetime(), days=days))
		data = practice.save_mastermind(
			self.course,
			"Мастермайнд недели",
			when,
			extra.get("topics", "Что получилось\nЧто мешает"),
			extra.get("link", "https://example.com/meet"),
		)
		return (data["upcoming"] + data["past"])[-1 if days < 0 else 0]

	def test_super_wall_visibility_moderation_and_points(self):
		self.assertEqual(frappe.db.get_value("OU Points Rule", "super_post", "enabled"), 0)
		before = points.total_for(self.alice)
		practice.post_super("Сегодня встала в 6 утра!")
		self.assertEqual(points.total_for(self.alice), before)
		frappe.db.set_value("OU Points Rule", "super_post", {"points": 2, "enabled": 1})
		post = practice.post_super("Прогулка перед работой")["posts"][0]
		self.assertEqual(points.total_for(self.alice), before + 2)
		with self.assertRaises(frappe.ValidationError):
			practice.post_super("   ")
		with self.assertRaises(frappe.ValidationError):
			practice.post_super("я" * 301)
		frappe.set_user(self.bob)
		seen = practice.super_feed()
		self.assertEqual(len(seen["posts"]), 2)
		self.assertNotIn("@", str(seen))
		with self.assertRaises(frappe.PermissionError):
			practice.moderate_super(post["id"], "hide")
		with self.assertRaises(frappe.PermissionError):
			practice.moderate_super(post["id"], "delete")
		frappe.set_user(TEACHER)
		hidden = practice.moderate_super(post["id"], "hide")
		self.assertTrue(next(p for p in hidden["posts"] if p["id"] == post["id"])["hidden"])
		frappe.set_user(self.bob)
		self.assertEqual(len(practice.super_feed()["posts"]), 1)
		frappe.set_user(self.alice)
		practice.moderate_super(post["id"], "delete")
		self.assertEqual(points.total_for(self.alice), before)
		frappe.set_user(self.stranger)
		with self.assertRaises(frappe.PermissionError):
			practice.super_feed(self.course)
		with self.assertRaises(frappe.PermissionError):
			practice.post_super("Я тут не учусь", self.course)

	def test_mastermind_schedule_going_and_instructor_only_changes(self):
		meeting = self._meeting()
		frappe.set_user(self.alice)
		data = practice.masterminds()
		self.assertEqual(data["upcoming"][0]["topics"], ["Что получилось", "Что мешает"])
		self.assertTrue(data["tz"])
		self.assertEqual(data["past"], [])
		going = practice.set_going(meeting["id"], 1)
		self.assertTrue(going["upcoming"][0]["going"])
		self.assertEqual(going["upcoming"][0]["going_count"], 1)
		self.assertFalse(practice.set_going(meeting["id"], 0)["upcoming"][0]["going"])
		with self.assertRaises(frappe.PermissionError):
			practice.save_mastermind(self.course, "Свой", str(now_datetime()))
		with self.assertRaises(frappe.PermissionError):
			practice.mark_attendance(meeting["id"], [self.alice])
		with self.assertRaises(frappe.PermissionError):
			practice.delete_mastermind(meeting["id"])
		frappe.set_user(self.stranger)
		with self.assertRaises(frappe.PermissionError):
			practice.masterminds(self.course)
		with self.assertRaises(frappe.PermissionError):
			practice.set_going(meeting["id"], 1)
		frappe.set_user(TEACHER)
		with self.assertRaises(frappe.ValidationError):
			practice.save_mastermind(self.course, "Плохая ссылка", str(now_datetime()), link="javascript:1")
		with self.assertRaises(frappe.ValidationError):
			practice.save_mastermind(self.course, "Плохая дата", "не дата")
		old = self._meeting(days=-2)
		self.assertTrue(old["past"])
		frappe.set_user(self.alice)
		self.assertEqual(len(practice.masterminds()["past"]), 1)

	def test_attendance_is_marked_by_instructor_and_pays_only_with_a_scale(self):
		meeting = self._meeting(days=-1)
		before = points.total_for(self.alice)
		frappe.set_user(TEACHER)
		practice.mark_attendance(meeting["id"], [self.alice])
		self.assertEqual(points.total_for(self.alice), before)
		frappe.db.set_value("OU Points Rule", "mastermind_attended", {"points": 5, "enabled": 1})
		data = practice.mark_attendance(meeting["id"], [self.alice, self.bob, self.stranger])
		people = {p["member"]: p for p in data["past"][0]["people"]}
		self.assertTrue(people[self.alice]["attended"] and people[self.bob]["attended"])
		self.assertNotIn(self.stranger, people)
		self.assertEqual(points.total_for(self.alice), before + 5)
		practice.mark_attendance(meeting["id"], [self.alice, self.bob])
		self.assertEqual(points.total_for(self.alice), before + 5)
		practice.mark_attendance(meeting["id"], [self.bob])
		self.assertEqual(points.total_for(self.alice), before)
		practice.delete_mastermind(meeting["id"])
		self.assertFalse(frappe.db.exists("OU Mastermind", meeting["id"]))
