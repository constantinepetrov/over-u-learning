app_name = "over_u"
app_title = "OVER U"
app_publisher = "OVER U"
app_description = "School configuration and assignment completion policy"
app_email = "dev@over-u.example.com"
app_license = "AGPL-3.0"
required_apps = ["lms"]
after_install = "over_u.install.configure"
after_migrate = "over_u.install.configure"
lms_assignment_completion_filters = ["over_u.policy.completion_filters"]
override_whitelisted_methods = {
    "lms.lms.doctype.course_lesson.course_lesson.save_progress": "over_u.policy.save_progress",
}
doc_events = {
    "LMS Assignment Submission": {
        "validate": "over_u.policy.validate_submission",
        "on_update": "over_u.policy.update_assignment_progress",
    },
    "LMS Course Progress": {"validate": "over_u.policy.validate_progress"},
}

website_route_rules = [{"from_route": "/school/<path:app_path>", "to_route": "school"}]
