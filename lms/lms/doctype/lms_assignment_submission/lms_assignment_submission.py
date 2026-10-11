# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.model.document import Document
from frappe.utils import validate_url

from lms.lms.html_sanitizer import sanitize_rich_text
from lms.lms.schedule_utils import assert_within_schedule
from lms.lms.utils import PRIVILEGED_ROLES, get_lms_route


class LMSAssignmentSubmission(Document):
	def validate(self):
		self.enforce_member_ownership()
		self.enforce_grading_permission()
		self.sanitize_rich_text_fields()
		self.validate_schedule_window()
		self.validate_duplicates()
		self.validate_url()
		self.validate_status()
		self.validate_assignment_attachment()

	def sanitize_rich_text_fields(self):
		"""Drop form controls the framework's allowlist keeps: `comments` is mailed as
		`email_content`, and both fields render outside the SPA where v-safe-html does not."""
		for field in ("comments", "answer"):
			self.set(field, sanitize_rich_text(self.get(field)))

	def validate_schedule_window(self):
		"""Students cannot create or edit submission content outside the window.

		Privileged roles may still grade (and manage submissions) outside the
		schedule.
		"""
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return

		if not self.assignment:
			return

		schedule = frappe.db.get_value(
			"LMS Assignment",
			self.assignment,
			["title", "enable_scheduling", "schedule_start", "schedule_end"],
			as_dict=True,
		)
		if not schedule:
			return

		assert_within_schedule(
			schedule.enable_scheduling,
			schedule.schedule_start,
			schedule.schedule_end,
			label=schedule.title or _("This assignment"),
		)

	def enforce_grading_permission(self):
		"""Only evaluators/instructors may set the grading fields.

		Prevents a student from grading their own submission (e.g. flipping status from
		"Not Graded" to "Pass" via frappe.client.set_value). On create the grading fields
		are reset to their defaults; on update they are reverted to the stored values.
		"""
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return

		# Revert grading fields to their stored values on update, or to safe defaults on
		# create / when no baseline is available (fail closed, never fail open).
		previous = None if self.is_new() else self.get_doc_before_save()
		defaults = {"status": "Not Graded", "comments": None, "evaluator": None}
		for field, default in defaults.items():
			setattr(self, field, previous.get(field) if previous else default)

	def enforce_member_ownership(self):
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return
		if self.member and self.member != frappe.session.user:
			frappe.throw(
				_("You can only submit assignments for your own account."),
				frappe.PermissionError,
			)
		self.member = frappe.session.user

	def on_update(self):
		self.validate_private_attachments()

	def validate_duplicates(self):
		if frappe.db.exists(
			"LMS Assignment Submission",
			{"assignment": self.assignment, "member": self.member, "name": ["!=", self.name]},
		):
			title = (
				frappe.db.get_value("Course Lesson", self.lesson, "title")
				if self.lesson
				else frappe.db.get_value("LMS Assignment", self.assignment, "title")
			)
			frappe.throw(_("A submission for {0} by {1} already exists.").format(title, self.member_name))

	def validate_url(self):
		if self.type == "URL" and not validate_url(self.answer, True, ["http", "https"]):
			frappe.throw(_("Please enter a valid URL."))

	def validate_status(self):
		if self.is_new():
			return
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return
		if doc_before_save.status != self.status or doc_before_save.comments != self.comments:
			self.trigger_update_notification()

	def validate_private_attachments(self):
		if self.type == "Text":
			from bs4 import BeautifulSoup

			soup = BeautifulSoup(self.answer, "html.parser")
			images = soup.find_all("img")
			self.attach_images_to_document(images)

	def validate_assignment_attachment(self):
		"""Keep uploaded homework files private and scoped to their submission."""
		if not self.assignment_attachment:
			return

		from urllib.parse import parse_qs, urlsplit

		parsed_url = urlsplit(self.assignment_attachment)
		if parsed_url.scheme or parsed_url.netloc:
			frappe.throw(
				_("External links cannot be used as private assignment attachments."),
				frappe.PermissionError,
			)
		file_url = parsed_url.path
		file_ids = parse_qs(parsed_url.query).get("fid", [])
		if file_ids:
			file_name = file_ids[0]
		else:
			files = frappe.get_all(
				"File", filters={"file_url": file_url}, fields=["name", "owner"]
			)
			file_name = next(
				(file.name for file in files if file.owner == frappe.session.user),
				files[0].name if files and PRIVILEGED_ROLES & set(frappe.get_roles()) else None,
			)
		if not file_name or frappe.db.get_value("File", file_name, "file_url") != file_url:
			frappe.throw(
				_("Please upload the assignment file to this school before submitting it."),
				frappe.PermissionError,
			)

		file_doc = frappe.get_doc("File", file_name)
		if file_doc.is_remote_file or not file_url.startswith(("/files/", "/private/files/")):
			frappe.throw(
				_("External links cannot be used as private assignment attachments."),
				frappe.PermissionError,
			)

		privileged = bool(PRIVILEGED_ROLES & set(frappe.get_roles()))
		if not privileged and file_doc.owner != frappe.session.user:
			frappe.throw(
				_("You can only attach files uploaded from your own account."),
				frappe.PermissionError,
			)

		temporary_name = self.get("__temporary_name")
		already_attached_elsewhere = (
			file_doc.attached_to_doctype
			and file_doc.attached_to_name
			and (
				file_doc.attached_to_doctype != self.doctype
				or file_doc.attached_to_name not in {self.name, temporary_name}
			)
		)
		if already_attached_elsewhere:
			frappe.throw(
				_("This file is already attached to another record."),
				frappe.PermissionError,
			)

		if not file_doc.is_private and file_doc.content_hash:
			shared_file = frappe.db.exists(
				"File", {"content_hash": file_doc.content_hash, "name": ["!=", file_doc.name]}
			)
			if shared_file:
				frappe.throw(
					_("This file is shared by other records. Upload a separate copy for your homework."),
					frappe.PermissionError,
				)
		elif not file_doc.is_private:
			frappe.throw(
				_("This file cannot be secured. Upload it again before submitting your homework."),
				frappe.PermissionError,
			)

		file_doc.attached_to_doctype = self.doctype
		file_doc.attached_to_name = self.name
		file_doc.attached_to_field = "assignment_attachment"
		file_doc.is_private = 1
		file_doc.save(ignore_permissions=True)
		self.assignment_attachment = file_doc.file_url

	def attach_images_to_document(self, images):
		for img in images:
			src = img.get("src", "")
			if src.startswith("/private/files/"):
				file_name = frappe.db.get_value("File", {"file_url": src}, "name")
				if file_name:
					frappe.db.set_value(
						"File",
						file_name,
						{
							"attached_to_doctype": self.doctype,
							"attached_to_name": self.name,
							"attached_to_field": "answer",
						},
					)

	def trigger_update_notification(self):
		notification = frappe._dict(
			{
				"subject": _("The instructor has left a comment on your assignment {0}").format(
					frappe.bold(self.assignment_title)
				),
				"email_content": self.comments,
				"document_type": self.doctype,
				"document_name": self.name,
				"from_user": self.evaluator,
				"type": "Alert",
				"link": get_lms_route(f"assignment-submission/{self.assignment}/{self.name}"),
			}
		)
		make_notification_logs(notification, [self.member])
