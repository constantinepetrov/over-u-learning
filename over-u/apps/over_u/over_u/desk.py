"""Role-gated entry point to the native Frappe Users workspace."""
import frappe


def can_access_desk():
    return "System Manager" in frappe.get_roles(frappe.session.user)
