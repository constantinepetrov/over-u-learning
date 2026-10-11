"""Authoring contract for Website Users with the Course Creator role."""

import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u.school import TEACHER


class TestAuthorWorkspace(BaseTestUtils):
	def test_website_course_creator_can_save_and_reopen_unpublished_draft(self):
		teacher = frappe.get_doc("User", TEACHER)
		self.assertEqual(teacher.user_type, "Website User")
		self.assertIn("Course Creator", frappe.get_roles(TEACHER))
		self.assertNotIn("System Manager", frappe.get_roles(TEACHER))

		frappe.set_user(TEACHER)
		try:
			course = frappe.get_doc(
				{
					"doctype": "LMS Course",
					"title": f"OVER U draft {frappe.generate_hash(length=8)}",
					"short_introduction": "First draft",
					"description": "<p>Author test content</p>",
					"published": 0,
					"instructors": [{"instructor": TEACHER}],
				}
			).insert()
			course.short_introduction = "Draft saved by Course Creator"
			course.save()
			reopened = frappe.get_doc("LMS Course", course.name)
			self.assertEqual(reopened.short_introduction, "Draft saved by Course Creator")
			self.assertEqual(reopened.published, 0)
			self.assertTrue(frappe.has_permission("LMS Course", "write", doc=reopened))
		finally:
			frappe.set_user("Administrator")
