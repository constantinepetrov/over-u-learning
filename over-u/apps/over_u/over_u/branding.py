import frappe

FILE_NAME = "over-u-mark.png"


def _mark_file_url():
	existing = frappe.db.get_value("File", {"file_name": FILE_NAME, "is_private": 0}, "file_url")
	if existing:
		return existing
	path = frappe.get_app_path("over_u", "public", "brand", "mark.png")
	with open(path, "rb") as handle:
		content = handle.read()
	doc = frappe.get_doc(
		{"doctype": "File", "file_name": FILE_NAME, "content": content, "is_private": 0}
	).insert(ignore_permissions=True)
	return doc.file_url


def apply_logo():
	"""Use the OVER U mark as the site logo and favicon (sidebar header, browser tab).

	LMS reads these through File rows, so the image is stored as a regular public file.
	"""
	url = _mark_file_url()
	frappe.db.set_single_value("Website Settings", "app_logo", url)
	frappe.db.set_single_value("Website Settings", "banner_image", url)
	frappe.db.set_single_value("Website Settings", "favicon", url)
	frappe.clear_cache()
