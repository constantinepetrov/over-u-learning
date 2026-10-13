import frappe

AUTHOR_ROLES = {"Course Creator", "Moderator", "Batch Evaluator", "System Manager"}


def on_login(login_manager):
	"""Send learners to the OVER U school after sign-in; authors keep the Studio.

	Frappe fills response["home_page"] after the on_login hooks run, so it cannot be
	set here. It does read `redirect_after_login` for the user at that point, which
	is the supported way to choose the landing page from a hook.
	"""
	user = getattr(login_manager, "user", None) or frappe.session.user
	if not user or user in ("Administrator", "Guest"):
		return
	if set(frappe.get_roles(user)) & AUTHOR_ROLES:
		return
	frappe.cache.hset("redirect_after_login", user, "/school")
