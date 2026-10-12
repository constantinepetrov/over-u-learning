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


def ensure_submission_attachment_write_permission():
    """Allow LMS students to attach uploads to submissions they can access.

    The document permission hook in policy.py narrows this DocPerm grant to the
    submission owner and the course author. Frappe checks DocPerm before it
    validates a File's attached document, so the owner needs a baseline write
    permission for the regular upload endpoint to work.
    """
    doctype = "LMS Assignment Submission"
    if not frappe.db.exists("DocType", doctype):
        return

    doc = frappe.get_doc("DocType", doctype)
    permission = next(
        (
            row
            for row in doc.permissions
            if row.role == "LMS Student" and row.permlevel == 0
        ),
        None,
    )
    if permission and permission.write:
        return

    if permission:
        permission.write = 1
    else:
        doc.append(
            "permissions",
            {"role": "LMS Student", "permlevel": 0, "read": 1, "write": 1},
        )
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype=doctype)
