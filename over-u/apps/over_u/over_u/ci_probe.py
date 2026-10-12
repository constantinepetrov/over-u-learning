"""Temporary data helpers for the isolated GitHub Actions integration run."""

import frappe


def create_private_assignment_file_probe():
	"""Create one synthetic private file owned by the seeded test student."""
	from over_u.school import STUDENTS, manifest

	frappe.set_user(STUDENTS[0])
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "over-u-ci-private-attachment.txt",
			"content": b"OVER_U_SYNTHETIC_PRIVATE_ATTACHMENT",
			"is_private": 1,
		}
	).insert()
	school = manifest()
	# Preserve the LMS `if_owner` behavior while skipping only the unrelated lesson
	# unlock validation in this synthetic access-control fixture.
	frappe.set_user(STUDENTS[0])
	submission = frappe.get_doc(
		{
			"doctype": "LMS Assignment Submission",
			"assignment": school["assignment"],
			"member": STUDENTS[0],
			"type": "Document",
			"answer": "Synthetic CI attachment access probe",
			"assignment_attachment": file_doc.file_url,
		}
	)
	submission.flags.ignore_validate = True
	submission.insert(ignore_permissions=True)
	file_doc.reload()
	return {
		"file_url": file_doc.file_url,
		"file_name": file_doc.name,
		"owner": STUDENTS[0],
		"submission": submission.name,
	}


def cleanup_private_assignment_file_probe():
	"""Remove the temporary attachment and submission after the URL checks."""
	from over_u.school import STUDENTS

	frappe.set_user("Administrator")
	file_url = "/private/files/over-u-ci-private-attachment.txt"
	submission = frappe.db.get_value(
		"LMS Assignment Submission",
		{"assignment_attachment": file_url, "member": STUDENTS[0]},
		"name",
	)
	if submission:
		frappe.delete_doc("LMS Assignment Submission", submission, force=True, ignore_permissions=True)
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if file_name:
		frappe.delete_doc("File", file_name, force=True, ignore_permissions=True)
	return {"removed_submission": bool(submission), "removed_file": bool(file_name)}
