"""Development-only snapshot helpers; never exposed as HTTP API."""
import hashlib
import json
import frappe

POC_USERS = ["teacher@over-u.example.com", "student1@over-u.example.com", "student2@over-u.example.com"]
TRAINING_DOCTYPES = ["LMS Course", "Course Chapter", "Chapter Reference", "Course Lesson", "Lesson Reference",
                     "LMS Quiz", "LMS Question", "LMS Quiz Question", "LMS Quiz Submission", "LMS Quiz Result",
                     "LMS Assignment", "LMS Assignment Submission", "LMS Enrollment", "LMS Course Progress"]


def development_only():
    if not frappe.conf.allow_tests or frappe.session.user != "Administrator":
        frappe.throw("Development administrator only", frappe.PermissionError)


def snapshot():
    """Only counts/digests leave the database; no answers, passwords or secrets."""
    development_only()
    result = {"tables": {}, "accounts": {}}
    for doctype in TRAINING_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        rows = frappe.get_all(doctype, fields=["*"], order_by="name")
        payload = json.dumps(rows, default=str, ensure_ascii=False, sort_keys=True).encode()
        result["tables"][doctype] = {"count": len(rows), "sha256": hashlib.sha256(payload).hexdigest()}
    for user in POC_USERS:
        values = frappe.db.get_value("User", user, ["enabled", "language", "user_type", "first_name"], as_dict=True)
        result["accounts"][user] = {**values, "roles": sorted(frappe.get_roles(user))}
    result["progress"] = frappe.get_all("LMS Enrollment", filters={"course": "over-u"}, fields=["member", "progress"], order_by="member")
    return result


def prepare_existing_school_setup():
    """Use the native per-app completion marker to skip LMS's demo-data seeder.

    That seeder elevates an existing arbitrary user to Moderator. An already
    populated OVER U clone must preserve its roles and authored school instead.
    Framework's wizard itself still runs normally and completes its own stages.
    """
    development_only()
    if frappe.local.site != "over-u-desk.localhost":
        frappe.throw("Only the dedicated Desk clone may be prepared", frappe.PermissionError)
    if not frappe.db.exists("LMS Course", "over-u") or len(snapshot()["progress"]) != 2:
        frappe.throw("Restore and verify the existing school first")
    from frappe.core.doctype.installed_applications.installed_applications import get_setup_wizard_completed_apps
    from frappe.desk.page.setup_wizard.setup_wizard import enable_setup_wizard_complete
    # Frappe 16's update_versions labels all non-Frappe/ERPNext apps as having
    # no wizard, even when LMS declares setup_wizard_complete. Record both flags
    # through the native Installed Applications document, otherwise the engine's
    # completed-app filter would ignore the LMS completion marker.
    apps = frappe.get_single("Installed Applications")
    lms = next(row for row in apps.installed_applications if row.app_name == "lms")
    lms.has_setup_wizard = 1
    lms.is_setup_complete = 1
    apps.save()
    enable_setup_wizard_complete("lms")
    frappe.clear_cache()
    if "lms" not in get_setup_wizard_completed_apps():
        frappe.throw("LMS demo seeder is not safely excluded")
    return {"completedApps": get_setup_wizard_completed_apps(), "frameworkSetupComplete": bool(frappe.is_setup_complete())}
