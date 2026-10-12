"""Temporary data helpers for the isolated GitHub Actions integration run."""

import frappe
from frappe import _


def create_http_upload_probe():
	"""Prepare an assignment for normal student HTTP insert and file upload tests."""
	from over_u.school import STUDENTS, TEACHER, _user, manifest

	if frappe.session.user != "Administrator":
		frappe.throw(_("Run upload probe setup as Administrator."), frappe.PermissionError)

	_user("over-u-unrelated-teacher@example.com", "Unrelated Synthetic Teacher", ["Course Creator"])
	school = manifest()
	title = "OVER U CI private upload probe"
	assignment_name = frappe.db.exists("LMS Assignment", {"title": title})
	if assignment_name:
		assignment = frappe.get_doc("LMS Assignment", assignment_name)
	else:
		assignment = frappe.get_doc(
			{
				"doctype": "LMS Assignment",
				"title": title,
				"type": "Text",
				"grade_assignment": 1,
				"course": school["course"],
				"question": "Submit synthetic text for file privacy testing.",
				"authors": [{"author": TEACHER}],
			}
		).insert()
	return {"assignment": assignment.name, "student": STUDENTS[0]}
