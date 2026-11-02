import json

import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import community_api as community
from over_u import points
from over_u import student_api as api
from over_u.school import TEACHER, manifest


class TestCommunity(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		points.seed_rules()
		self.school = manifest()
		self.course = self.school["course"]
		self.alice = self._create_user(
			"over-u-feed-alice@example.com", "Алиса", "Иванова", ["LMS Student"]
		).name
		self.bob = self._create_user("over-u-feed-bob@example.com", "Борис", "Петров", ["LMS Student"]).name
		for user in (self.alice, self.bob):
			frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": user}).insert()
			frappe.set_user(user)
			for number in ("1-1", "1-2", "2-1"):
				api.complete_lesson(self.course, number)
			quiz = frappe.get_doc("LMS Quiz", self.school["quiz"])
			answers = [
				frappe.db.get_value("LMS Question", row.question, "option_1") for row in quiz.questions
			]
			api.submit_quiz(self.course, "2-2", answers)
			frappe.set_user("Administrator")
		frappe.set_user(self.alice)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("OU Points Entry", {"member": ["in", [self.alice, self.bob]]})
		super().tearDown()

	def test_other_answers_open_only_after_own_answer(self):
		frappe.set_user(self.bob)
		api.submit_assignment(self.course, "3-1", "Ответ Бориса")
		frappe.set_user(self.alice)
		locked = community.feed(self.course, "3-1")
		self.assertFalse(locked["unlocked"])
		self.assertEqual(locked["others"], 1)
		self.assertNotIn("Борис", json.dumps(locked, ensure_ascii=False))
		with self.assertRaises(frappe.PermissionError):
			community.post_message(self.course, "3-1", "Привет", "")
		api.submit_assignment(self.course, "3-1", "Ответ Алисы")
		opened = community.feed(self.course, "3-1")
		self.assertTrue(opened["unlocked"])
		self.assertCountEqual([m["author"] for m in opened["messages"]], ["Борис П.", "Алиса И."])
		self.assertNotIn("@", json.dumps(opened, ensure_ascii=False))

	def test_chat_reactions_and_points(self):
		frappe.set_user(self.bob)
		api.submit_assignment(self.course, "3-1", "Ответ Бориса")
		frappe.set_user(self.alice)
		api.submit_assignment(self.course, "3-1", "Ответ Алисы")
		bob_answer = next(
			m for m in community.feed(self.course, "3-1")["messages"] if m["author"] == "Борис П."
		)
		before = points.total_for(self.bob)
		with self.assertRaises(frappe.ValidationError):
			community.react(
				self.course,
				"3-1",
				next(m["id"] for m in community.feed(self.course, "3-1")["messages"] if m["mine"]),
				"like",
			)
		feed = community.react(self.course, "3-1", bob_answer["id"], "useful")
		self.assertEqual(points.total_for(self.bob), before + 1)
		reacted = next(m for m in feed["messages"] if m["id"] == bob_answer["id"])
		self.assertTrue(reacted["reactions"]["useful"]["me"])
		# Toggling off takes the point back; repeating never pays twice.
		community.react(self.course, "3-1", bob_answer["id"], "useful")
		self.assertEqual(points.total_for(self.bob), before)
		feed = community.post_message(self.course, "3-1", "Классная мысль!", bob_answer["id"])
		thread = next(m for m in feed["messages"] if m["id"] == bob_answer["id"])
		self.assertEqual([r["text"] for r in thread["replies"]], ["Классная мысль!"])

	def test_hidden_message_is_invisible_to_learners_and_moderation_is_instructor_only(self):
		frappe.set_user(self.bob)
		api.submit_assignment(self.course, "3-1", "Ответ Бориса")
		frappe.set_user(self.alice)
		api.submit_assignment(self.course, "3-1", "Ответ Алисы")
		bob_answer = next(
			m for m in community.feed(self.course, "3-1")["messages"] if m["author"] == "Борис П."
		)
		with self.assertRaises(frappe.PermissionError):
			community.moderate(self.course, "3-1", bob_answer["id"], "hide")
		frappe.db.set_value("OU Feed Message", bob_answer["id"], "hidden", 1)
		self.assertEqual([m["author"] for m in community.feed(self.course, "3-1")["messages"]], ["Алиса И."])

	def test_points_are_awarded_once_and_follow_the_grade(self):
		start = points.total_for(self.alice)
		api.submit_assignment(self.course, "3-1", "Мой план")
		self.assertEqual(points.total_for(self.alice), start + 3)
		api.submit_assignment(self.course, "3-1", "Мой план, версия 2")
		self.assertEqual(points.total_for(self.alice), start + 3)
		frappe.set_user(TEACHER)
		name = frappe.db.get_value(
			"LMS Assignment Submission",
			{"assignment": self.school["assignment"], "member": self.alice},
			"name",
		)
		doc = frappe.get_doc("LMS Assignment Submission", name)
		doc.status = "Pass"
		doc.save()
		self.assertEqual(
			points.total_for(self.alice), start + 14
		)  # 3 submitted + 10 passed + 1 lesson completed by the pass
		doc.status = "Fail"
		doc.save()
		# The pass is taken back; the lesson point stays and is never paid twice.
		self.assertEqual(points.total_for(self.alice), start + 4)

	def test_leaderboard_groups_and_privacy(self):
		points.award(self.bob, "assignment_pass", "test:bob:1", self.course)
		frappe.set_user("Administrator")
		group = frappe.get_doc(
			{
				"doctype": "OU Group",
				"title": "Пара тест",
				"kind": "Бадди",
				"members": [{"member": self.alice}, {"member": self.bob}],
			}
		).insert()
		frappe.set_user(self.alice)
		board = community.leaderboard(self.course, "all")
		self.assertTrue(board["enabled"])
		self.assertNotIn("@", json.dumps(board, ensure_ascii=False))
		self.assertTrue(any(g["title"] == "Пара тест" and g["mine"] for g in board["groups"]))
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "OU Group",
					"title": "Дубль",
					"kind": "Бадди",
					"members": [{"member": self.alice}],
				}
			).insert()
		frappe.set_user(self.alice)
		frappe.db.set_single_value(
			"OU Settings", "leaderboard_visibility", "Ученик видит только свой результат"
		)
		own = community.leaderboard(self.course, "all")
		self.assertTrue(all(row["me"] for row in own["top"]))
		frappe.db.set_single_value("OU Settings", "leaderboard_visibility", "Все ученики видят табло")
		frappe.set_user("Administrator")
		group.delete()

	def test_outsider_cannot_read_feed_or_rating(self):
		frappe.set_user("Administrator")
		stranger = self._create_user(
			"over-u-feed-stranger@example.com", "Чужой", "Тест", ["LMS Student"]
		).name
		frappe.set_user(stranger)
		with self.assertRaises(frappe.PermissionError):
			community.feed(self.course, "3-1")
		with self.assertRaises(frappe.PermissionError):
			community.leaderboard(self.course, "all")
