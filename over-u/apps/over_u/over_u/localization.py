"""Frappe-native language defaults and early LMS translation boot.

No assessment values, permissions, authored content or controllers are changed.
"""
import json

import frappe
from frappe.translate import get_all_translations


@frappe.whitelist(allow_guest=True)
def get_translations():
    from frappe.translate import get_user_lang
    lang = frappe.local.lang if frappe.session.user == "Guest" else get_user_lang()
    return get_all_translations(lang)


def configure_defaults():
    # The wizard and language selectors list only enabled languages.
    # A site default alone does not enable Russian in Framework 16.
    if frappe.db.exists("Language", "ru"):
        frappe.db.set_value("Language", "ru", "enabled", 1, update_modified=False)
    frappe.db.set_single_value("System Settings", "language", "ru")
    frappe.clear_cache()


def set_new_user_language(doc, method=None):
    if not doc.language:
        doc.language = frappe.get_system_settings("language") or "ru"


def migrate_existing_users():
    """One-time, explicitly requested migration. Future language choices survive."""
    configure_defaults()
    for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
        frappe.db.set_value("User", user, "language", "ru", update_modified=False)
        frappe.clear_cache(user=user)
    frappe.clear_cache()


def localize_demo_labels():
    # Explicitly known SYSTEM demo copy only. Never auto-translate authored text.
    from over_u.school import manifest
    demo = manifest()
    old = '<p>Опишите цель, один измеримый шаг и время выполнения. Преподаватель проверит работу и поставит Pass или Fail.</p>'
    if demo.get("assignment") and frappe.db.get_value("LMS Assignment", demo["assignment"], "question") == old:
        frappe.db.set_value("LMS Assignment", demo["assignment"], "question", old.replace("Pass или Fail", "«Зачтено» или «Не зачтено»"))
    if demo.get("quiz"):
        for row in frappe.get_doc("LMS Quiz", demo["quiz"]).questions:
            if frappe.db.get_value("LMS Question", row.question, "option_1") == "Преподаватель поставил Pass":
                frappe.db.set_value("LMS Question", row.question, "option_1", "Преподаватель поставил зачёт")
    frappe.clear_cache()


def guest_language():
    # Frappe normally prefers Accept-Language over site defaults for guests.
    # Honor explicit native cookie/_lang, otherwise start at the school's default.
    if frappe.session.user == "Guest" and not frappe.form_dict.get("_lang"):
        request = frappe.local.request
        if not request.cookies.get("preferred_language"):
            lang = frappe.get_system_settings("language") or "ru"
            frappe.local.lang = lang
            frappe.local.cookie_manager.set_cookie("preferred_language", lang)


def preload_lms_translations(response, request):
    """Standard after_request extension for the standalone LMS template.

    LMS's non-reactive __() is used during setup, before its asynchronous fetch.
    Preload the same Frappe dictionary ahead of the module script to avoid English
    first render. JSON escapes '<' so translations cannot terminate a script.
    """
    if (request.path == "/lms" or request.path.startswith("/lms/")) and response.mimetype == "text/html" and response.status_code == 200:
        from frappe.translate import get_user_lang
        lang = get_user_lang()
        payload = json.dumps(get_translations(), ensure_ascii=False).replace("<", "\\u003c")
        marker = '<script id="over-u-translations">window.translatedMessages=' + payload + ';</script>'
        from pathlib import Path
        editor_file = Path(frappe.get_app_path("over_u", "public", "localization", "editor-ru.json"))
        editor = editor_file.read_text() if lang == "ru" else "{}"
        marker += '<script>window.overUEditorMessages=' + editor.replace("<", "\\u003c") + ';</script>'
        player_file = Path(frappe.get_app_path("over_u", "public", "localization", "player-ru.json"))
        player = player_file.read_text() if lang == "ru" else "{}"
        marker += '<script>window.overUPlyrMessages=' + player.replace("<", "\\u003c") + ';</script>'
        marker += '<script src="/assets/over_u/localization/editor-menu.js"></script>'
        html = response.get_data(as_text=True)
        response.set_data(html.replace("<head>", "<head>" + marker, 1))


def school_messages():
    """Own UI uses one reviewed bilingual catalog; English remains available."""
    from pathlib import Path
    lang = frappe.local.lang or "ru"
    folder = Path(frappe.get_app_path("over_u", "public", "school", "messages"))
    code = "ru" if lang.split("-")[0] == "ru" else "en"
    return {"language": code, "messages": json.loads((folder / f"{code}.json").read_text())}
