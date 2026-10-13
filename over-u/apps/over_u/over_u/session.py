import frappe

AUTHOR_ROLES = {"Course Creator", "Moderator", "Batch Evaluator", "System Manager"}


def on_login(login_manager):
	"""Send learners to the OVER U school after sign-in; authors keep the Studio."""
	user = getattr(login_manager, "user", None) or frappe.session.user
	if not user or user in ("Administrator", "Guest"):
		return
	if set(frappe.get_roles(user)) & AUTHOR_ROLES:
		return
	frappe.local.response["home_page"] = "/school"
