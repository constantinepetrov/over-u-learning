import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import admin_api as admin
from over_u import points
from over_u import profile_api as profile
from over_u.goals_api import my_goals
from over_u.school import TEACHER, manifest


class TestAdmin(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		points.seed_rules()
		self.course = manifest()["course"]
		users = {}
		for key, first in (("a", "Алиса"), ("b", "Борис"), ("c", "Вера"), ("x", "Чужой")):
			users[key] = self._create_user(
				f"over-u-adm-{key}@example.com", first, "Тест", ["LMS Student"]
			).name
		self.a, self.b, self.c, self.x = users["a"], users["b"], users["c"], users["x"]
		for user in (self.a, self.b, self.c):
			frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": user}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("OU Group", {"course": self.course})
		frappe.db.delete("OU Member Profile", {"member": ["in", [self.a, self.b, self.c]]})
		frappe.db.delete("OU Goal", {"member": ["in", [self.a, self.b, self.c]]})
		frappe.db.delete("OU Points Entry", {"member": ["in", [self.a, self.b, self.c]]})
		frappe.db.set_single_value("OU Settings", "prizes", "")
		for event in ("daily_report", "super_post"):
			frappe.db.set_value("OU Points Rule", event, {"points": 0, "enabled": 0})
		super().tearDown()

	def test_groups_are_instructor_only_and_validated(self):
		frappe.set_user(self.a)
		with self.assertRaises(frappe.PermissionError):
			admin.save_group(self.course, "Бадди", "Пара", [self.a, self.b])
		frappe.set_user(TEACHER)
		data = admin.save_group(self.course, "Бадди", "Пара 1", [self.a, self.b])
		self.assertEqual(len(data["groups"]), 1)
		with self.assertRaises(frappe.ValidationError):
			admin.save_group(self.course, "Бадди", "Пара", [self.a])
		with self.assertRaises(frappe.ValidationError):
			admin.save_group(self.course, "Бадди", "Пара 2", [self.b, self.c])  # b is already paired
		with self.assertRaises(frappe.ValidationError):
			admin.save_group(self.course, "Команда", "Команда", [self.a, self.x])  # not enrolled
		group = data["groups"][0]["id"]
		admin.save_group(self.course, "Бадди", "Пара 1", [self.b, self.c], group=group)
		self.assertEqual(
			sorted(m["member"] for m in admin.teacher_groups()["groups"][0]["members"]),
			sorted([self.b, self.c]),
		)
		admin.delete_group(group)
		self.assertEqual(admin.teacher_groups()["groups"], [])

	def test_buddy_changes_revoke_access(self):
		frappe.set_user(self.a)
		from over_u.goals_api import save_goal

		save_goal("Основная", "Бегать", [{"title": "Шаг"}], shared=1)
		frappe.set_user(TEACHER)
		group = admin.save_group(self.course, "Бадди", "Пара", [self.a, self.b])["groups"][0]["id"]
		frappe.set_user(self.b)
		self.assertEqual(len(my_goals()["buddy"]["goals"]), 1)
		frappe.set_user(TEACHER)
		admin.save_group(self.course, "Бадди", "Пара", [self.a, self.c], group=group)
		frappe.set_user(self.b)
		self.assertIsNone(my_goals()["buddy"])

	def test_points_settings_preview_and_bonus(self):
		frappe.set_user(self.a)
		with self.assertRaises(frappe.PermissionError):
			admin.points_settings()
		with self.assertRaises(frappe.PermissionError):
			admin.save_rule("super_post", 5, 1)
		frappe.set_user(TEACHER)
		preview = admin.preview_rule("super_post", 5, 1)
		self.assertFalse(preview["retroactive"])
		self.assertEqual(preview["new"], 5)
		with self.assertRaises(frappe.ValidationError):
			admin.save_rule("super_post", -1, 1)
		with self.assertRaises(frappe.ValidationError):
			admin.save_rule("super_post", 5000, 1)
		admin.save_rule("super_post", 4, 1, 3)
		self.assertEqual(frappe.db.get_value("OU Points Rule", "super_post", "points"), 4)
		with self.assertRaises(frappe.ValidationError):
			admin.give_bonus(self.a, self.course, 0, "x")
		with self.assertRaises(frappe.ValidationError):
			admin.give_bonus(self.x, self.course, 5, "чужой")
		before = points.total_for(self.a)
		admin.give_bonus(self.a, self.course, 5, "За помощь")
		self.assertEqual(points.total_for(self.a), before + 5)
		board = admin.save_board(1, "Все ученики видят табло", 10, "1 место: по решению автора")
		self.assertEqual(board["prizes"], "1 место: по решению автора")
		frappe.set_user(self.a)
		self.assertEqual(points.leaderboard(self.course, self.a)["prizes"], "1 место: по решению автора")

	def test_profile_is_private_until_shared(self):
		frappe.set_user(self.a)
		profile.save_profile(
			{
				"offer": {"offer": "Помогу с питанием", "shared": 1},
				"help": {"help_needed": "Нужен режим", "help_how": "Чат", "shared": 0},
			}
		)
		frappe.set_user(TEACHER)
		admin.save_group(self.course, "Бадди", "Пара", [self.a, self.b])
		frappe.set_user(self.b)
		shown = my_goals()["buddy"]["profile"]
		self.assertIn("offer", shown)
		self.assertNotIn("help", shown)
		frappe.set_user(self.x)
		self.assertEqual(profile.my_profile()["profile"]["offer"]["offer"], "")
		with self.assertRaises(frappe.ValidationError):
			frappe.set_user(self.a)
			profile.save_profile({"offer": {"offer": "я" * 1600}})

	def test_module_skeleton_is_idempotent_and_hidden_from_learners(self):
		from over_u import modules
		from over_u.student_api import course as snapshot

		frappe.set_user("Administrator")
		first = modules.ensure_skeleton("OU Test Skeleton")
		self.assertEqual(len(first["created"]), 12)
		self.assertFalse(first["published"])
		self.assertEqual(modules.ensure_skeleton("OU Test Skeleton")["created"], [])
		info = modules.status(first["course"])
		self.assertEqual(info["ready"], 0)
		self.assertEqual(len(info["modules"]), 12)
		frappe.get_doc({"doctype": "LMS Enrollment", "course": first["course"], "member": self.a}).insert()
		frappe.db.set_value("LMS Course", first["course"], "published", 1)
		frappe.set_user(self.a)
		self.assertEqual(snapshot(first["course"])["chapters"], [])
		frappe.set_user("Administrator")
		frappe.delete_doc("LMS Course", first["course"], force=True)
