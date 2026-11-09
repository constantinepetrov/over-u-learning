import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def configure():
	from over_u.points import seed_rules

	seed_rules()
	create_custom_fields(
		{
			"Course Lesson": [
				{
					"fieldname": "over_u_video_url",
					"label": "OVER U: Video link",
					"fieldtype": "Data",
					"length": 500,
					"insert_after": "title",
					"description": "Yandex Disk, RuTube, VK Video or YouTube link shown at the top of the lesson.",
				}
			],
			"LMS Course": [
				{
					"fieldname": "over_u_require_assignment_pass",
					"label": "OVER U: Require Assignment Pass",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "enforce_lesson_completion",
					"description": "Complete assignment lessons only after teacher review with Pass.",
				}
			],
		}
	)

	# Learners land in the OVER U school after sign-in; authors keep the Studio.
	# Frappe picks the landing page from the first role that has a home page.
	for role in ("Course Creator", "Moderator", "Batch Evaluator"):
		if frappe.db.exists("Role", role):
			frappe.db.set_value("Role", role, "home_page", "lms", update_modified=False)
	if frappe.db.exists("Role", "LMS Student"):
		frappe.db.set_value("Role", "LMS Student", "home_page", "school", update_modified=False)
