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
	# Use a privileged setup user for the probe record so its unrelated lesson
	# unlock policy does not prevent testing the file's access rules.
	frappe.set_user("Administrator")
	frappe.get_doc(
		{
			"doctype": "LMS Assignment Submission",
			"assignment": school["assignment"],
			"member": STUDENTS[0],
			"type": "Document",
			"answer": "Synthetic CI attachment access probe",
			"assignment_attachment": file_doc.file_url,
		}
	).insert()
	file_doc.reload()
	return {"file_url": file_doc.file_url, "owner": STUDENTS[0]}
