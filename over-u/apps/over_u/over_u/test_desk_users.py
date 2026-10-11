"""Regression checks for native Frappe User and role behavior used by Desk."""
import frappe
from lms.lms.test_helpers import BaseTestUtils


from over_u.desk import can_access_desk
from over_u.www.school import can_review_assignments


class TestDeskUserOperations(BaseTestUtils):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_temporary_school_accounts_roles_status_and_permissions(self):
        student = frappe.get_doc({
            "doctype": "User", "email": "desk-student-test@over-u.example.com",
            "first_name": "Временный ученик", "send_welcome_email": 0,
            "roles": [{"role": "LMS Student"}],
        }).insert()
        teacher = frappe.get_doc({
            "doctype": "User", "email": "desk-teacher-test@over-u.example.com",
            "first_name": "Временный преподаватель", "send_welcome_email": 0,
            "roles": [{"role": "LMS Student"}],
        }).insert()
        self.assertEqual(student.language, "ru")
        self.assertEqual(teacher.language, "ru")

        teacher.add_roles("Course Creator")
        teacher.save()
        self.assertIn("Course Creator", frappe.get_roles(teacher.name))
        self.assertTrue(can_review_assignments(teacher.name))
        teacher.remove_roles("Course Creator")
        teacher.save()
        self.assertNotIn("Course Creator", frappe.get_roles(teacher.name))
        self.assertFalse(can_review_assignments(teacher.name))
        teacher.add_roles("Course Creator")
        teacher.save()
        self.assertIn("Course Creator", frappe.get_roles(teacher.name))

        teacher.enabled = 0
        teacher.save()
        self.assertEqual(frappe.db.get_value("User", teacher.name, "enabled"), 0)
        teacher.enabled = 1
        teacher.save()
        self.assertEqual(frappe.db.get_value("User", teacher.name, "enabled"), 1)

        self.assertTrue(can_access_desk())
        self.assertFalse(can_review_assignments(student.name))
        administrator = frappe.get_doc("User", "Administrator")
        for account in (student, teacher):
            frappe.set_user(account.name)
            self.assertFalse(can_access_desk())
            self.assertNotIn("System Manager", frappe.get_roles(account.name))
            self.assertFalse(frappe.has_permission("User", ptype="read", doc=administrator))
            self.assertFalse(frappe.has_permission("User", ptype="create"))
        frappe.set_user("Administrator")
