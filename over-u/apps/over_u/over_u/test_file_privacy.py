import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u.file_privacy import enforce_assignment_attachment_privacy
from over_u.policy import as_member
from over_u.school import STUDENTS, TEACHER, _user, manifest


def insert_synthetic_fixture(doc):
	# nosemgrep: lms-unjustified-ignore-permissions - test fixtures use synthetic records to exercise file authorization boundaries.
	return doc.insert(ignore_permissions=True)


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
		)
		self.submission = insert_synthetic_fixture(self.submission)

	def test_doctype_metadata_is_kept_private(self):
		frappe.db.set_value("DocType", "LMS Assignment Submission", "make_attachments_public", 1)
		enforce_assignment_attachment_privacy()
		self.assertEqual(
			frappe.db.get_value("DocType", "LMS Assignment Submission", "make_attachments_public"),
			0,
		)
		self.assertEqual(frappe.get_meta("LMS Assignment Submission").make_attachments_public, 0)

	def test_submission_read_access_is_limited_to_owner_and_course_author(self):
		assignment = frappe.get_doc(
			{
				"doctype": "LMS Assignment",
				"title": "Synthetic scoped attachment assignment",
				"type": "Document",
				"grade_assignment": 1,
				"course": self.school["course"],
				"question": "Synthetic access boundary fixture.",
				"authors": [{"author": TEACHER}],
			}
		).insert()
		_user("over-u-unrelated-teacher@example.com", "Unrelated Synthetic Teacher", ["Course Creator"])
		frappe.set_user(STUDENTS[1])
		submission = frappe.get_doc(
			{
				"doctype": "LMS Assignment Submission",
				"assignment": assignment.name,
				"member": STUDENTS[1],
				"type": "Document",
				"answer": "Synthetic private answer.",
			}
		).insert()

		self.assertTrue(frappe.has_permission(submission.doctype, "read", doc=submission, user=STUDENTS[1]))
		self.assertTrue(frappe.has_permission(submission.doctype, "read", doc=submission, user=TEACHER))
		self.assertFalse(frappe.has_permission(submission.doctype, "read", doc=submission, user=STUDENTS[0]))
		self.assertFalse(
			frappe.has_permission(
				submission.doctype,
				"read",
				doc=submission,
				user="over-u-unrelated-teacher@example.com",
			)
		)
		with as_member(STUDENTS[1]):
			self.assertEqual(
				frappe.get_list(submission.doctype, filters={"name": submission.name}, pluck="name"),
				[submission.name],
			)
		with as_member("over-u-unrelated-teacher@example.com"):
			self.assertEqual(
				frappe.get_list(submission.doctype, filters={"name": submission.name}, pluck="name"),
				[],
			)

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
		)
		file_doc = insert_synthetic_fixture(file_doc)
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
		)
		public_file = insert_synthetic_fixture(public_file)
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
			).insert()
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
		)
		file_doc = insert_synthetic_fixture(file_doc)
		file_doc.is_private = 0
		with self.assertRaises(frappe.PermissionError):
			# nosemgrep: lms-unjustified-ignore-permissions - test exercises server-side rejection of a public-state mutation.
			file_doc.save(ignore_permissions=True)
		file_doc.reload()
		self.assertEqual(file_doc.is_private, 1)
		self.assertTrue(file_doc.file_url.startswith("/private/files/"))
