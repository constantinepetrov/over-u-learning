import json
import re
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.translate import print_language
from werkzeug.wrappers import Request, Response
from lms.lms.test_helpers import BaseTestUtils
from over_u import localization, student_api
from over_u.school import manifest

BROWSER_USER = "localization-test@over-u.example.com"


def browser_fixture():
    """Dev-only fixture; existing students and their credentials stay untouched."""
    import os
    from frappe.utils.password import update_password
    if not frappe.conf.allow_tests or frappe.session.user != "Administrator":
        frappe.throw("Development test fixture only", frappe.PermissionError)
    if not frappe.db.exists("User", BROWSER_USER):
        frappe.get_doc({"doctype": "User", "email": BROWSER_USER, "first_name": "Проверка русификации OVER U",
                        "send_welcome_email": 0, "language": "ru",
                        "roles": [{"role": "LMS Student"}]}).insert()
        update_password(BROWSER_USER, os.environ["OVER_U_DEMO_PASSWORD"])
    course = manifest()["course"]
    if not frappe.db.exists("LMS Enrollment", {"course": course, "member": BROWSER_USER}):
        frappe.get_doc({"doctype": "LMS Enrollment", "course": course, "member": BROWSER_USER}).insert()
    return {"user": BROWSER_USER, "course": course}


def remove_browser_fixture():
    if not frappe.conf.allow_tests or frappe.session.user != "Administrator":
        frappe.throw("Development test fixture only", frappe.PermissionError)
    for doctype in ("LMS Quiz Submission", "LMS Assignment Submission", "LMS Course Progress", "LMS Enrollment"):
        for name in frappe.get_all(doctype, {"member": BROWSER_USER}, pluck="name"):
            frappe.delete_doc(doctype, name, force=True)
    if frappe.db.exists("User", BROWSER_USER):
        frappe.delete_doc("User", BROWSER_USER, force=True)
    return {"removed": True}


class TestLocalization(BaseTestUtils):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_new_user_default_and_explicit_english(self):
        for suffix, language in [("default", None), ("english", "en")]:
            user = frappe.get_doc({"doctype": "User", "email": f"ru-ui-{suffix}@example.com",
                                   "first_name": "Locale", "send_welcome_email": 0, "language": language}).insert()
            self.assertEqual(user.language, language or "ru")
        localization.configure_defaults()
        self.assertEqual(frappe.db.get_value("User", "ru-ui-english@example.com", "language"), "en")

    def test_merged_native_glossary_and_fallback_language(self):
        with print_language("ru"):
            for english, russian in [("Pass", "Зачтено"), ("Fail", "Не зачтено"),
                                     ("Not Graded", "Ожидает проверки"), ("Assignments", "Домашние задания"),
                                     ("Welcome! Please sign in to continue.", "Добро пожаловать! Войдите, чтобы продолжить.")]:
                self.assertEqual(frappe._(english), russian)
        user = self._create_user("ru-ui-no-language@example.com", "Locale", "Fallback", ["LMS Student"])
        frappe.db.set_value("User", user.name, "language", None)
        frappe.clear_cache(user=user.name)
        frappe.set_user(user.name)
        self.assertEqual(localization.get_translations()["Pass"], "Зачтено")

    def test_student_catalog_parity_and_placeholder_preservation(self):
        folder = Path(frappe.get_app_path("over_u", "public", "school", "messages"))
        ru = json.loads((folder / "ru.json").read_text())
        en = json.loads((folder / "en.json").read_text())
        self.assertEqual(set(ru), set(en))
        for key in ru:
            self.assertTrue(ru[key]); self.assertTrue(en[key])
            self.assertEqual(re.findall(r"\{\d+\}", ru[key]), re.findall(r"\{\d+\}", en[key]))
        source = "\n".join((folder.parent / name).read_text() for name in ["views.js", "components.js", "app.js", "api.js"])
        self.assertEqual(set(re.findall(r"t\('(ui_\d+)'", source)), set(ru))

    def test_native_catalog_preserves_interpolation_and_technical_values(self):
        import csv
        with open(frappe.get_app_path("over_u", "translations", "ru.csv")) as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), len({r[0] for r in rows}))
        for source, target in rows:
            self.assertEqual(sorted(re.findall(r"\{\d+\}", source)), sorted(re.findall(r"\{\d+\}", target)), source)
            self.assertEqual(sorted(re.findall(r"\{\{.*?\}\}", source)), sorted(re.findall(r"\{\{.*?\}\}", target)), source)
        options = frappe.get_meta("LMS Assignment Submission").get_field("status").options
        self.assertEqual(options.splitlines(), ["Pass", "Fail", "Not Graded", "Not Applicable"])

    def test_localized_locks_do_not_translate_author_content_or_change_progress(self):
        demo = manifest()
        student = self._create_user("ru-ui-contract@example.com", "Locale", "Contract", ["LMS Student"])
        frappe.get_doc({"doctype": "LMS Enrollment", "course": demo["course"], "member": student.name}).insert()
        frappe.set_user(student.name)
        for lang, message in [("ru", "Сначала завершите предыдущий урок."), ("en", "Complete the previous lesson first.")]:
            with print_language(lang):
                data = student_api.lesson(demo["course"], "3-2")
                self.assertEqual(data["lock_reason"], message)
                self.assertEqual(data["course"]["title"], "OVER U — Основы осознанного обучения")
                self.assertEqual(data["course"]["progress"], 0)
                self.assertTrue(data["locked"])
                self.assertEqual(localization.school_messages()["language"], lang)

    def test_early_lms_boot_is_scoped_and_script_safe(self):
        request = Request.from_values(path="/lms/courses")
        response = Response("<html><head></head><body></body></html>", content_type="text/html")
        with patch("over_u.localization.get_translations", return_value={"unsafe": "</script><script>evil()"}):
            localization.preload_lms_translations(response, request)
        html = response.get_data(as_text=True)
        self.assertIn("over-u-translations", html)
        self.assertIn("\\u003c/script>", html)
        self.assertNotIn("<script>evil()", html)
        for path in ("/school", "/api/method/login", "/desk"):
            untouched = Response("<head></head>", content_type="text/html")
            localization.preload_lms_translations(untouched, Request.from_values(path=path))
            self.assertEqual(untouched.get_data(as_text=True), "<head></head>")
