import frappe
from over_u.localization import school_messages

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=%2Fschool"
        raise frappe.Redirect
    context.boot = {"csrf_token": frappe.sessions.get_csrf_token(), "api_version": 1, **school_messages()}
    return context
