app_name = "over_u"
app_title = "OVER U"
app_publisher = "OVER U"
app_description = "School configuration and assignment completion policy"
app_email = "dev@over-u.example.com"
app_license = "AGPL-3.0"
required_apps = ["lms"]
after_install = [
	"over_u.install.configure",
	"over_u.submission_permissions.ensure_student_write_permission",
	"over_u.localization.migrate_existing_users",
	"over_u.file_privacy.enforce_assignment_attachment_privacy",
]
after_migrate = [
	"over_u.install.configure",
	"over_u.submission_permissions.ensure_student_write_permission",
	"over_u.localization.configure_defaults",
	"over_u.file_privacy.enforce_assignment_attachment_privacy",
]
extend_doctype_class = {
	"File": ["over_u.file_privacy.PrivateAssignmentFile"],
}
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
has_permission = {
	"LMS Assignment Submission": "over_u.policy.assignment_submission_has_permission",
}
permission_query_conditions = {
	"LMS Assignment Submission": "over_u.policy.assignment_submission_query",
}

website_route_rules = [{"from_route": "/school/<path:app_path>", "to_route": "school"}]
before_request = ["over_u.localization.guest_language"]
after_request = ["over_u.localization.preload_lms_translations"]
after_build = "over_u.build.after_build"
app_include_js = ["/assets/over_u/localization/desk.js"]
web_include_css = ["/assets/over_u/brand/login.css"]
# Native extension point for the one stock list column that skips __().
doctype_list_js = {"User": "public/localization/user-list.js"}

# Send administrators directly to the native Users workspace after login.
app_home = "/desk/users"
add_to_apps_screen = [
	{
		"name": "over_u",
		"title": "OVER U",
		"route": "/desk/users",
		"has_permission": "over_u.desk.can_access_desk",
	}
]
