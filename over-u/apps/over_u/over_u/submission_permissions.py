"""Minimal record permission needed for private homework uploads."""

import frappe


def ensure_student_write_permission():
	"""Grant baseline write DocPerm; the record hook restricts it to owner/instructor."""
	doctype = "LMS Assignment Submission"
	if not frappe.db.exists("DocType", doctype):
		return

	filters = {"parent": doctype, "role": "LMS Student", "permlevel": 0, "if_owner": 0}
	if not frappe.db.exists("Custom DocPerm", filters):
		frappe.permissions.add_permission(doctype, "LMS Student", 0, ptype="read")
	frappe.permissions.update_permission_property(doctype, "LMS Student", 0, "write", 1)
	frappe.clear_cache(doctype=doctype)
