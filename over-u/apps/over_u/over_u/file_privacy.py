"""Keep learner homework attachments private without changing course assets."""

import frappe
from frappe import _

ASSIGNMENT_SUBMISSION = "LMS Assignment Submission"


class PrivateAssignmentFile:
	"""Enforce private storage before Frappe writes an assignment file to disk."""

	def before_insert(self):
		if self.attached_to_doctype == ASSIGNMENT_SUBMISSION:
			self._enforce_private_on_insert()
		super().before_insert()

	def validate(self):
		if self.attached_to_doctype == ASSIGNMENT_SUBMISSION:
			if not self.is_private:
				frappe.throw(_("Homework attachments must be private."), frappe.PermissionError)
			existing = frappe.db.get_value(
				"File",
				{"file_url": self.file_url, "is_private": 0, "name": ["!=", self.name or ""]},
				"name",
			)
			if existing:
				frappe.throw(
					_("A public file cannot be attached to a homework submission."),
					frappe.PermissionError,
				)
		super().validate()

	def _enforce_private_on_insert(self):
		# A new upload has content and no URL yet. Set privacy before File.before_insert
		# writes it, so even upload_file(is_private=0) lands under private/files.
		if self.get_content():
			self.is_private = 1
			return

		# Reusing a public or remote URL would bypass private-file access checks. Do
		# not mutate that File or move a public course asset as a side effect.
		if self.file_url:
			existing = frappe.db.get_value(
				"File", {"file_url": self.file_url}, ["name", "is_private"], as_dict=True
			)
			if self.file_url.startswith(("http://", "https://", "/api/method/")):
				frappe.throw(
					_("External files cannot be attached to a homework submission."),
					frappe.PermissionError,
				)
			if existing and not existing.is_private:
				frappe.throw(
					_("A public file cannot be attached to a homework submission."),
					frappe.PermissionError,
				)
			if not self.file_url.startswith("/private/files/"):
				frappe.throw(_("Homework attachments must use private file storage."), frappe.PermissionError)
			self.is_private = 1


def enforce_assignment_attachment_privacy():
	"""Keep upstream DocType sync from restoring public attachment behavior."""
	if not frappe.db.exists("DocType", ASSIGNMENT_SUBMISSION):
		return
	frappe.db.set_value("DocType", ASSIGNMENT_SUBMISSION, "make_attachments_public", 0, update_modified=False)
	frappe.clear_cache(doctype=ASSIGNMENT_SUBMISSION)
