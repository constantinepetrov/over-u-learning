import frappe

from lms.lms.test_helpers import BaseTestUtils

from over_u.file_privacy import enforce_assignment_attachment_privacy
from over_u.school import STUDENTS, manifest


class TestAssignmentAttachmentPrivacy(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.school = manifest()
		self.submission = frappe.get_doc(
			{
				"doctype": "LMS Assignment Submission",
				"assignment": self.school["assignment"],
				"member": STUDENTS[1],
				"type": "Document",
				"answer": "Synthetic attachment privacy test",
			}
		).insert(ignore_permissions=True)

	def test_doctype_metadata_is_kept_private(self):
		frappe.db.set_value("DocType", "LMS Assignment Submission", "make_attachments_public", 1)
		enforce_assignment_attachment_privacy()
		self.assertEqual(
			frappe.db.get_value("DocType", "LMS Assignment Submission", "make_attachments_public"),
			0,
		)
		self.assertEqual(frappe.get_meta("LMS Assignment Submission").make_attachments_public, 0)

	def test_explicit_public_upload_for_homework_is_saved_privately(self):
		frappe.set_user(STUDENTS[1])
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "over-u-private-homework-test.txt",
				"content": b"synthetic homework attachment",
				"is_private": 0,
				"attached_to_doctype": "LMS Assignment Submission",
				"attached_to_name": self.submission.name,
				"attached_to_field": "assignment_attachment",
			}
		).insert()
		self.assertEqual(file_doc.is_private, 1)
		self.assertTrue(file_doc.file_url.startswith("/private/files/"))

	def test_course_asset_can_remain_public(self):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "over-u-public-course-asset-test.txt",
				"content": b"synthetic public course asset",
				"is_private": 0,
				"attached_to_doctype": "LMS Course",
				"attached_to_name": self.school["course"],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(file_doc.is_private, 0)
		self.assertTrue(file_doc.file_url.startswith("/files/"))

	def test_public_course_file_cannot_be_reused_for_homework(self):
		public_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "over-u-public-reuse-test.txt",
				"content": b"public synthetic course file",
				"is_private": 0,
				"attached_to_doctype": "LMS Course",
				"attached_to_name": self.school["course"],
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": public_file.file_name,
					"file_url": public_file.file_url,
					"is_private": 0,
					"attached_to_doctype": "LMS Assignment Submission",
					"attached_to_name": self.submission.name,
					"attached_to_field": "assignment_attachment",
				}
			).insert(ignore_permissions=True)
		public_file.reload()
		self.assertEqual(public_file.is_private, 0)
		self.assertTrue(public_file.file_url.startswith("/files/"))

	def test_private_homework_file_cannot_be_made_public(self):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "over-u-private-state-test.txt",
				"content": b"synthetic homework state",
				"is_private": 1,
				"attached_to_doctype": "LMS Assignment Submission",
				"attached_to_name": self.submission.name,
				"attached_to_field": "assignment_attachment",
			}
		).insert(ignore_permissions=True)
		file_doc.is_private = 0
		with self.assertRaises(frappe.PermissionError):
			file_doc.save(ignore_permissions=True)
		file_doc.reload()
		self.assertEqual(file_doc.is_private, 1)
		self.assertTrue(file_doc.file_url.startswith("/private/files/"))
