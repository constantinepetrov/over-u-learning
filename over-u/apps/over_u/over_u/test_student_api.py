import json

import frappe
from lms.lms.test_helpers import BaseTestUtils
from over_u import student_api as api
from over_u.school import TEACHER, manifest


class TestStudentAPI(BaseTestUtils):
    def setUp(self):
        super().setUp()
        from frappe.translate import print_language
        self.translation_context = print_language("ru")
        self.translation_context.__enter__()
        frappe.set_user("Administrator")
        self.school = manifest()
        self.course = self.school["course"]
        self.student = self._create_user("over-u-ui-api-test@example.com", "UI", "Test", ["LMS Student"]).name
        self.outsider = self._create_user("over-u-ui-outsider@example.com", "Outside", "Test", ["LMS Student"]).name
        frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": self.student}).insert()
        frappe.set_user(self.student)

    def tearDown(self):
        frappe.set_user("Administrator")
        self.translation_context.__exit__(None, None, None)
        super().tearDown()

    def reach_quiz(self):
        for number in ("1-1", "1-2", "2-1"):
            self.assertTrue(api.complete_lesson(self.course, number)["lesson"]["complete"])

    def answers(self, correct=3):
        quiz = frappe.get_doc("LMS Quiz", self.school["quiz"])
        return [frappe.db.get_value("LMS Question", row.question, "option_1" if i < correct else "option_2")
                for i, row in enumerate(quiz.questions)]

    def reach_homework(self):
        self.reach_quiz()
        return api.submit_quiz(self.course, "2-2", self.answers())

    def test_session_scoping_and_nonmember_denial(self):
        home = api.home()
        self.assertEqual(home["user"]["email"], self.student)
        self.assertEqual(len(home["courses"]), 1)
        self.assertEqual(home["courses"][0]["progress"], 0)
        self.assertNotIn("ASG-SUB-00015", json.dumps(home))
        frappe.set_user(self.outsider)
        self.assertEqual(api.home()["courses"], [])
        with self.assertRaises(frappe.PermissionError):
            api.course(self.course)
        with self.assertRaises(frappe.PermissionError):
            api.lesson(self.course, "1-1")
        frappe.set_user("Guest")
        with self.assertRaises(frappe.AuthenticationError):
            api.home()

    def test_locked_lesson_withholds_all_content_and_assessments(self):
        result = api.lesson(self.course, "2-2")
        self.assertTrue(result["locked"])
        self.assertEqual(result["blocks"], [])
        self.assertNotIn("quiz", result)
        self.assertNotIn("assignment", result)
        with self.assertRaises(frappe.PermissionError):
            api.complete_lesson(self.course, "3-2")
        with self.assertRaises(frappe.PermissionError):
            api.submit_quiz(self.course, "2-2", self.answers())
        with self.assertRaises(frappe.PermissionError):
            api.submit_assignment(self.course, "3-1", "Too early")

    def test_quiz_server_scoring_failure_retry_and_no_answer_key(self):
        self.reach_quiz()
        payload = api.lesson(self.course, "2-2")["quiz"]
        self.assertEqual(payload["threshold"], 75)
        encoded = json.dumps(payload)
        self.assertNotIn("is_correct", encoded)
        self.assertNotIn("explanation", encoded)
        result = api.submit_quiz(self.course, "2-2", self.answers(2))
        self.assertEqual(result["quiz"]["result"]["percentage"], 50)
        self.assertFalse(result["lesson"]["complete"])
        self.assertTrue(result["next"]["locked"])
        self.assertTrue(result["quiz"]["can_retry"])
        result = api.submit_quiz(self.course, "2-2", self.answers(3))
        self.assertTrue(result["quiz"]["result"]["passed"])
        self.assertEqual(result["quiz"]["result"]["percentage"], 75)
        self.assertTrue(result["lesson"]["complete"])
        self.assertFalse(result["next"]["locked"])

    def test_homework_pending_then_stock_teacher_pass_unlocks(self):
        self.reach_homework()
        pending = api.submit_assignment(self.course, "3-1", "My plan <script>alert(1)</script>")
        self.assertEqual(pending["assignment"]["submission"]["status"], "Not Graded")
        self.assertNotIn("<script>", pending["assignment"]["submission"]["answer"])
        self.assertTrue(api.lesson(self.course, "3-2")["locked"])
        self.assertIn("дождитесь проверки", api.lesson(self.course, "3-2")["lock_reason"])
        self.assertEqual(len(api.home()["courses"][0]["pending"]), 1)
        frappe.set_user(TEACHER)
        name = frappe.db.get_value("LMS Assignment Submission", {"assignment": self.school["assignment"], "member": self.student}, "name")
        doc = frappe.get_doc("LMS Assignment Submission", name)
        doc.status = "Pass"
        doc.comments = "<p>Зачёт</p>"
        doc.save()
        frappe.set_user(self.student)
        passed = api.lesson(self.course, "3-1")
        self.assertEqual(passed["assignment"]["submission"]["status"], "Pass")
        self.assertFalse(api.lesson(self.course, "3-2")["locked"])
        self.assertEqual(api.home()["courses"][0]["pending"], [])
        with self.assertRaises(frappe.ValidationError):
            api.submit_assignment(self.course, "3-1", "Replace passed answer")
        self.assertEqual(api.complete_lesson(self.course, "3-2")["course"]["progress"], 100)

    def test_student_cannot_fetch_another_students_answer(self):
        self.reach_homework()
        own = api.submit_assignment(self.course, "3-1", "My own answer")
        self.assertIn("My own answer", own["assignment"]["submission"]["answer"])
        self.assertNotIn("Моя цель", own["assignment"]["submission"]["answer"])
        frappe.set_user(self.outsider)
        with self.assertRaises(frappe.PermissionError):
            api.lesson(self.course, "3-1")

    def test_attempt_limit_and_advanced_quiz_fail_closed(self):
        self.reach_quiz()
        frappe.set_user("Administrator")
        quiz = frappe.get_doc("LMS Quiz", self.school["quiz"])
        quiz.max_attempts = 1
        quiz.save()
        frappe.set_user(self.student)
        api.submit_quiz(self.course, "2-2", self.answers(2))
        self.assertFalse(api.lesson(self.course, "2-2")["quiz"]["can_retry"])
        with self.assertRaises(frappe.ValidationError):
            api.submit_quiz(self.course, "2-2", self.answers(3))
        frappe.set_user("Administrator")
        quiz.max_attempts = 0
        quiz.duration = 60
        quiz.save()
        frappe.set_user(self.student)
        self.assertTrue(api.lesson(self.course, "2-2")["quiz"]["unsupported"])
        with self.assertRaises(frappe.ValidationError):
            api.submit_quiz(self.course, "2-2", self.answers(3))

    def test_instructor_content_and_unsafe_html_are_not_exposed(self):
        frappe.set_user("Administrator")
        lesson = frappe.get_doc("Course Lesson", self.school["lessons"][0].name)
        lesson.instructor_content = json.dumps({"blocks": [{"type": "paragraph", "data": {"text": "INSTRUCTOR_ONLY_SENTINEL"}}]})
        lesson.content = json.dumps({"blocks": [{"type": "paragraph", "data": {"text": '<b>Safe text</b><script>alert(1)</script><img src="x" onerror="alert(1)"><form>fake</form>'}}]})
        lesson.save()
        frappe.set_user(self.student)
        encoded = json.dumps(api.lesson(self.course, "1-1"))
        self.assertNotIn("INSTRUCTOR_ONLY_SENTINEL", encoded)
        self.assertNotIn("instructor_content", encoded)
        self.assertNotIn("onerror", encoded)
        self.assertNotIn("<script", encoded)
        self.assertNotIn("<form", encoded)

    def test_malformed_routes_and_quiz_payloads_are_rejected(self):
        for number in ("0-1", "../2-1", "9-9", "1-1/anything"):
            with self.assertRaises((frappe.DoesNotExistError, frappe.ValidationError)):
                api.lesson(self.course, number)
        self.reach_quiz()
        for answers in ([], ["fake"] * 4, [{"percentage": 100}] * 4):
            with self.assertRaises(frappe.ValidationError):
                api.submit_quiz(self.course, "2-2", answers)
        self.assertEqual(frappe.db.count("LMS Quiz Submission", {"member": self.student}), 0)
