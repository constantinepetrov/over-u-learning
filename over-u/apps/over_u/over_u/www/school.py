import frappe

from over_u.localization import school_messages

no_cache = 1


def can_review_assignments(user=None):
	roles = set(frappe.get_roles(user or frappe.session.user))
	return bool(roles & {"Course Creator", "Moderator", "Batch Evaluator", "System Manager"})


def can_author_courses(user=None):
	roles = set(frappe.get_roles(user or frappe.session.user))
	return bool(roles & {"Course Creator", "Moderator", "System Manager"})


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=%2Fschool"
		raise frappe.Redirect
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"api_version": 1,
		"teacher_tools": can_review_assignments(),
		"author_tools": can_author_courses(),
		**school_messages(),
	}
	return context
