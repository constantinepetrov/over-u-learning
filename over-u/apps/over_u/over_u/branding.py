import frappe

MARK = "/assets/over_u/brand/mark.png"


def _file_url(file_url, file_name):
	existing = frappe.db.exists("File", {"file_url": file_url})
	if existing:
		return file_url
	frappe.get_doc(
		{"doctype": "File", "file_name": file_name, "file_url": file_url, "is_private": 0}
	).insert(ignore_permissions=True)
	return file_url


def apply_logo():
	"""Use the OVER U mark as the site logo and favicon (sidebar header, browser tab)."""
	url = _file_url(MARK, "over-u-mark.png")
	frappe.db.set_single_value("Website Settings", "app_logo", url)
	frappe.db.set_single_value("Website Settings", "favicon", url)
	frappe.clear_cache()
