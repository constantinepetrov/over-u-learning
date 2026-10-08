import json

import frappe
from lms.lms.test_helpers import BaseTestUtils

from lms.lms.doctype.course_lesson.course_lesson import get_assignment_progress, save_progress
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.permissions import get_locked_lessons
from over_u.school import TEACHER, manifest


class TestSchoolPolicy(BaseTestUtils):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self.school = manifest()
        self.course = self.school["course"]
        self.lessons = self.school["lessons"]
        self.student = "over-u-policy-test@example.com"
        if not frappe.db.exists("User", self.student):
            frappe.get_doc({"doctype": "User", "email": self.student, "first_name": "Policy Test",
                            "send_welcome_email": 0, "roles": [{"role": "LMS Student"}]}).insert()
        frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": self.student}).insert()
        frappe.set_user(self.student)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def quiz(self, number_correct):
        quiz = frappe.get_doc("LMS Quiz", self.school["quiz"])
        rows = []
        for i, row in enumerate(quiz.questions):
            question = frappe.get_doc("LMS Question", row.question)
            rows.append({"question_name": row.question,
                         "answer": [question.option_1 if i < number_correct else question.option_2]})
        return submit_quiz(quiz.name, json.dumps(rows))

    def reach_assignment(self):
        for lesson in self.lessons[:3]:
            save_progress(lesson.name, self.course)
        self.quiz(3)
        save_progress(self.lessons[3].name, self.course)

    def submission(self):
        return frappe.get_doc({"doctype": "LMS Assignment Submission", "assignment": self.school["assignment"],
                               "member": self.student, "answer": "<p>Пройти модуль до пятницы.</p>",
                               "status": "Pass"}).insert()

    def test_sequence_and_failed_quiz_do_not_unlock(self):
        self.assertEqual(len(get_locked_lessons(self.course)), 5)
        with self.assertRaises(frappe.PermissionError):
            save_progress(self.lessons[-1].name, self.course)
        for lesson in self.lessons[:3]:
            save_progress(lesson.name, self.course)
        self.quiz(2)
        save_progress(self.lessons[3].name, self.course)
        self.assertIn(self.lessons[4].name, get_locked_lessons(self.course))
        self.quiz(3)
        save_progress(self.lessons[3].name, self.course)
        self.assertNotIn(self.lessons[4].name, get_locked_lessons(self.course))

    def test_submission_waits_for_teacher_pass(self):
        self.reach_assignment()
        submission = self.submission()
        self.assertEqual(submission.status, "Not Graded")
        self.assertFalse(get_assignment_progress(self.lessons[4].name))
        save_progress(self.lessons[4].name, self.course)
        self.assertIn(self.lessons[5].name, get_locked_lessons(self.course))
        frappe.set_user(TEACHER)
        submission = frappe.get_doc(submission.doctype, submission.name)
        submission.status = "Pass"
        submission.save()
        self.assertEqual(submission.evaluator, TEACHER)
        self.assertEqual(frappe.session.user, TEACHER)
        frappe.set_user(self.student)
        self.assertTrue(get_assignment_progress(self.lessons[4].name))
        self.assertNotIn(self.lessons[5].name, get_locked_lessons(self.course))

    def test_fail_resubmission_and_pass_revocation(self):
        self.reach_assignment()
        submission = self.submission()
        frappe.set_user(TEACHER)
        submission.status = "Fail"
        submission.save()
        frappe.set_user(self.student)
        self.assertIn(self.lessons[5].name, get_locked_lessons(self.course))
        submission = frappe.get_doc(submission.doctype, submission.name)
        submission.answer = "<p>Исправленный план: 20 минут каждый день.</p>"
        submission.save()
        self.assertEqual(submission.status, "Not Graded")
        frappe.set_user(TEACHER)
        submission.status = "Pass"
        submission.save()
        submission.status = "Fail"
        submission.save()
        frappe.set_user(self.student)
        self.assertIn(self.lessons[5].name, get_locked_lessons(self.course))

    def test_generic_progress_write_cannot_bypass_assignment(self):
        self.reach_assignment()
        self.submission()
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc({"doctype": "LMS Course Progress", "lesson": self.lessons[4].name,
                            "course": self.course, "member": self.student, "status": "Complete"}).insert(ignore_permissions=True)

    def test_passed_answer_is_frozen(self):
        self.reach_assignment()
        submission = self.submission()
        frappe.set_user(TEACHER)
        submission.status = "Pass"
        submission.save()
        frappe.set_user(self.student)
        submission = frappe.get_doc(submission.doctype, submission.name)
        submission.answer = "<p>Different answer after approval.</p>"
        with self.assertRaises(frappe.ValidationError):
            submission.save()

    def test_unrelated_course_creator_cannot_grade(self):
        self.reach_assignment()
        submission = self.submission()
        frappe.set_user("Administrator")
        stranger = self._create_user("over-u-other-teacher@example.com", "Other", "Teacher", ["Course Creator"])
        frappe.set_user(stranger.name)
        submission = frappe.get_doc(submission.doctype, submission.name)
        submission.status = "Pass"
        with self.assertRaises(frappe.PermissionError):
            submission.save()

    def test_student_cannot_self_grade_on_update(self):
        self.reach_assignment()
        submission = self.submission()
        submission.status = "Pass"
        submission.evaluator = self.student
        submission.save()
        self.assertEqual(submission.status, "Not Graded")
        self.assertFalse(submission.evaluator)
        self.assertIn(self.lessons[5].name, get_locked_lessons(self.course))

    def test_progress_endpoint_checks_course_against_lesson(self):
        from over_u.policy import save_progress as checked_save_progress
        with self.assertRaises(frappe.PermissionError):
            checked_save_progress(self.lessons[0].name, "different-course")

    def test_policy_is_opt_in(self):
        from over_u.policy import completion_filters
        self.assertEqual(completion_filters(self.lessons[4].name, self.school["assignment"]), {"status": "Pass"})
        frappe.set_user("Administrator")
        course = frappe.get_doc("LMS Course", self.course)
        course.over_u_require_assignment_pass = 0
        course.save()
        self.assertEqual(completion_filters(self.lessons[4].name, self.school["assignment"]), {})
