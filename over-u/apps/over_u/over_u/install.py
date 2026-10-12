import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def configure():
    create_custom_fields({"LMS Course": [{
        "fieldname": "over_u_require_assignment_pass",
        "label": "OVER U: Require Assignment Pass",
        "fieldtype": "Check",
        "default": "0",
        "insert_after": "enforce_lesson_completion",
        "description": "Complete assignment lessons only after teacher review with Pass.",
    }]})
