"""Temporary data helpers for the isolated GitHub Actions integration run."""

import frappe
from frappe import _


def create_private_assignment_file_probe():
	"""Create one synthetic submission for the live upload and access probes."""
	from over_u.school import STUDENTS, _user, manifest

	school = manifest()
	frappe.set_user("Administrator")
	assignment = frappe.get_doc(
		{
			"doctype": "LMS Assignment",
			"title": "Synthetic CI private attachment probe",
			"type": "Document",
			"grade_assignment": 1,
			"course": school["course"],
			"question": "Synthetic file privacy canary.",
			"authors": [{"author": school["teacher"]}],
		}
	).insert()
	_user("over-u-unrelated-teacher@example.com", "Unrelated Synthetic Teacher", ["Course Creator"])
	frappe.set_user(STUDENTS[0])
	submission = frappe.get_doc(
		{
			"doctype": "LMS Assignment Submission",
			"assignment": assignment.name,
			"member": STUDENTS[0],
			"type": "Document",
			"answer": "Synthetic CI attachment privacy probe",
		}
	).insert()
	frappe.set_user("Administrator")
	print(f"OVER_U_CI_PROBE_SUBMISSION={submission.name}")
	return {"submission": submission.name, "owner": STUDENTS[0]}


def create_http_upload_probe():
	"""Prepare an assignment for normal student HTTP insert and file upload tests."""
	from over_u.school import STUDENTS, TEACHER, _user, manifest

	if frappe.session.user != "Administrator":
		frappe.throw(_("Run upload probe setup as Administrator."), frappe.PermissionError)

	_user("over-u-unrelated-teacher@example.com", "Unrelated Synthetic Teacher", ["Course Creator"])
	school = manifest()
	title = "OVER U CI private PDF upload probe"
	assignment_name = frappe.db.exists("LMS Assignment", {"title": title})
	if assignment_name:
		assignment = frappe.get_doc("LMS Assignment", assignment_name)
	else:
		assignment = frappe.get_doc(
			{
				"doctype": "LMS Assignment",
				"title": title,
				"type": "PDF",
				"grade_assignment": 1,
				"course": school["course"],
				"question": "Upload a synthetic PDF for file privacy testing.",
				"authors": [{"author": TEACHER}],
			}
		).insert()
	return {"assignment": assignment.name, "student": STUDENTS[0]}
