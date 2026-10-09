app_name = "over_u"
app_title = "OVER U"
app_publisher = "OVER U"
app_description = "School configuration and assignment completion policy"
app_email = "dev@over-u.example.com"
app_license = "AGPL-3.0"
required_apps = ["lms"]
after_install = ["over_u.install.configure", "over_u.localization.migrate_existing_users"]
after_migrate = ["over_u.install.configure", "over_u.localization.configure_defaults"]
lms_assignment_completion_filters = ["over_u.policy.completion_filters"]
override_whitelisted_methods = {
    "lms.lms.api.get_translations": "over_u.localization.get_translations",
    "lms.lms.doctype.course_lesson.course_lesson.save_progress": "over_u.policy.save_progress",
}
doc_events = {
    "User": {"before_insert": "over_u.localization.set_new_user_language"},
    "LMS Assignment Submission": {
        "validate": "over_u.policy.validate_submission",
        "on_update": "over_u.policy.update_assignment_progress",
    },
    "LMS Course Progress": {"validate": "over_u.policy.validate_progress"},
}

website_route_rules = [{"from_route": "/school/<path:app_path>", "to_route": "school"}]
before_request = ["over_u.localization.guest_language"]
after_request = ["over_u.localization.preload_lms_translations"]
after_build = "over_u.build.after_build"
app_include_js = ["/assets/over_u/localization/desk.js"]
