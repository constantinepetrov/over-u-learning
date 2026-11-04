import json

import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import discussion_api as disc
from over_u import points
from over_u import student_api as api
from over_u.school import TEACHER, manifest


class TestDiscussion(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		points.seed_rules()
		self.school = manifest()
		self.course = self.school["course"]
		self.alice = self._create_user(
			"over-u-disc-alice@example.com", "Алиса", "Иванова", ["LMS Student"]
		).name
		self.bob = self._create_user("over-u-disc-bob@example.com", "Борис", "Петров", ["LMS Student"]).name
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
		frappe.db.delete("OU Lesson Comment", {"course": self.course})
		frappe.db.delete("OU Points Entry", {"member": ["in", [self.alice, self.bob]]})
		super().tearDown()

	def test_thread_teacher_reply_and_attention_queue(self):
		root = disc.post_lesson_comment(self.course, "3-1", "Сколько времени уделять практике?")
		comment_id = root["messages"][0]["id"]
		frappe.set_user(self.bob)
		seen = disc.lesson_comments(self.course, "3-1")
		self.assertEqual([m["author"] for m in seen["messages"]], ["Алиса И."])
		self.assertNotIn("@", json.dumps(seen, ensure_ascii=False))
		frappe.set_user(TEACHER)
		before = disc.teacher_desk()
		self.assertTrue(any(q["id"] == comment_id for q in before["questions"]))
		answered = disc.post_lesson_comment(self.course, "3-1", "Начните с десяти минут.", comment_id)
		reply = answered["messages"][0]["replies"][0]
		self.assertTrue(reply["staff"])
		after = disc.teacher_desk()
		self.assertFalse(any(q["id"] == comment_id for q in after["questions"]))
		frappe.set_user(self.alice)
		self.assertTrue(disc.lesson_comments(self.course, "3-1")["messages"][0]["replies"][0]["staff"])
		# A new student message after the instructor's answer brings the thread back to the desk.
		disc.post_lesson_comment(self.course, "3-1", "Спасибо, а по вечерам можно?", comment_id)
		frappe.set_user(TEACHER)
		self.assertTrue(any(q["id"] == comment_id for q in disc.teacher_desk()["questions"]))

	def test_private_thread_stays_between_student_and_instructor(self):
		posted = disc.post_lesson_comment(self.course, "3-1", "Личный вопрос", "", 1)
		comment_id = posted["messages"][0]["id"]
		self.assertTrue(posted["messages"][0]["private"])
		frappe.set_user(self.bob)
		self.assertEqual(disc.lesson_comments(self.course, "3-1")["messages"], [])
		with self.assertRaises(frappe.DoesNotExistError):
			disc.post_lesson_comment(self.course, "3-1", "Подслушиваю", comment_id)
		frappe.set_user(TEACHER)
		self.assertEqual(len(disc.lesson_comments(self.course, "3-1")["messages"]), 1)
		answered = disc.post_lesson_comment(self.course, "3-1", "Ответ лично", comment_id)
		self.assertTrue(answered["messages"][0]["replies"][0]["private"])
		frappe.set_user(self.alice)
		self.assertEqual(len(disc.lesson_comments(self.course, "3-1")["messages"][0]["replies"]), 1)
		frappe.set_user(self.bob)
		self.assertEqual(disc.lesson_comments(self.course, "3-1")["messages"], [])

	def test_moderation_and_ownership(self):
		root = disc.post_lesson_comment(self.course, "3-1", "Первое сообщение")
		comment_id = root["messages"][0]["id"]
		frappe.set_user(self.bob)
		with self.assertRaises(frappe.PermissionError):
			disc.moderate_lesson_comment(self.course, "3-1", comment_id, "hide")
		with self.assertRaises(frappe.PermissionError):
			disc.moderate_lesson_comment(self.course, "3-1", comment_id, "delete")
		frappe.set_user(TEACHER)
		hidden = disc.moderate_lesson_comment(self.course, "3-1", comment_id, "hide")
		self.assertTrue(hidden["messages"][0]["hidden"])
		pinned = disc.moderate_lesson_comment(self.course, "3-1", comment_id, "pin")
		self.assertTrue(pinned["messages"][0]["pinned"])
		frappe.set_user(self.bob)
		self.assertEqual(disc.lesson_comments(self.course, "3-1")["messages"], [])
		frappe.set_user(TEACHER)
		disc.moderate_lesson_comment(self.course, "3-1", comment_id, "unhide")
		frappe.set_user(self.alice)
		disc.moderate_lesson_comment(self.course, "3-1", comment_id, "delete")
		self.assertFalse(frappe.db.exists("OU Lesson Comment", comment_id))

	def test_outsider_and_lock_are_refused(self):
		frappe.set_user("Administrator")
		stranger = self._create_user(
			"over-u-disc-stranger@example.com", "Чужой", "Тест", ["LMS Student"]
		).name
		frappe.set_user(stranger)
		with self.assertRaises(frappe.PermissionError):
			disc.lesson_comments(self.course, "3-1")
		with self.assertRaises(frappe.PermissionError):
			disc.post_lesson_comment(self.course, "3-1", "Я здесь не учусь")
		with self.assertRaises(frappe.PermissionError):
			disc.teacher_desk()
		with self.assertRaises(frappe.PermissionError):
			disc.teacher_student(self.alice)
		frappe.set_user(self.alice)
		with self.assertRaises(frappe.PermissionError):
			disc.teacher_course(self.course)
		with self.assertRaises(frappe.PermissionError):
			disc.teacher_lesson(self.course, "3-1")

	def test_desk_reuses_review_filters_and_student_card(self):
		api.submit_assignment(self.course, "3-1", "План Алисы")
		disc.post_lesson_comment(self.course, "3-1", "Вопрос от Алисы")
		frappe.set_user(TEACHER)
		desk = disc.teacher_desk()
		self.assertTrue(any(row["student"] == self.alice for row in desk["queue"]))
		self.assertGreaterEqual(desk["counters"]["to_review"], 1)
		self.assertEqual(disc.teacher_desk("Pass")["queue"], [])
		with self.assertRaises(frappe.ValidationError):
			disc.teacher_desk("Bogus")
		row = next(r for r in desk["queue"] if r["student"] == self.alice)
		api.review_assignment(row["name"], "Pass", "Хорошо")
		self.assertTrue(
			any(r["student"] == self.alice for r in disc.teacher_desk("Pass", self.course)["queue"])
		)
		self.assertFalse(any(r["student"] == self.alice for r in disc.teacher_desk("Not Graded")["queue"]))
		card = disc.teacher_student(self.alice)
		self.assertEqual(card["student"], self.alice)
		self.assertTrue(card["submissions"])
		self.assertTrue(card["comments"])
		self.assertTrue(card["courses"][0]["progress"]["total"] >= 1)
		course = disc.teacher_course(self.course)
		self.assertTrue(course["modules"])
		self.assertTrue(any(s["student"] == self.alice for s in course["students"]))
		lesson = disc.teacher_lesson(self.course, "3-1")
		self.assertEqual(lesson["number"], "3-1")
		with self.assertRaises(frappe.DoesNotExistError):
			disc.teacher_lesson(self.course, "9-9")
