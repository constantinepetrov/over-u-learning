import frappe

from over_u.file_privacy import enforce_assignment_attachment_privacy


def execute():
	"""Disable public attachment behavior for LMS assignment submissions."""
	enforce_assignment_attachment_privacy()
	frappe.clear_cache()
