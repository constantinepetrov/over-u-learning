import frappe

MARK_URL = "/assets/over_u/brand/mark.png"
FILE_NAME = "over-u-mark.png"


def _mark_file_url():
	"""Register the bundled mark as a File row that points at the app asset.

	LMS reads the site logo through File rows (get_file_info). The image itself
	ships inside the app and is served from /assets, so no upload to the files
	volume is needed; db_insert skips the upload hooks that would try to read
	/assets/... as a stored upload.
	"""
	if frappe.db.exists("File", {"file_url": MARK_URL}):
		return MARK_URL
	doc = frappe.new_doc("File")
	doc.update(
		{
			"file_name": FILE_NAME,
			"file_url": MARK_URL,
			"file_type": "PNG",
			"is_private": 0,
			"is_folder": 0,
			"folder": "Home",
		}
	)
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	return MARK_URL


def apply_logo():
	"""Use the OVER U mark as the site logo and favicon (sidebar header, browser tab)."""
	url = _mark_file_url()
	frappe.db.set_single_value("Website Settings", "app_logo", url)
	frappe.db.set_single_value("Website Settings", "banner_image", url)
	frappe.db.set_single_value("Website Settings", "favicon", url)
	frappe.clear_cache()
