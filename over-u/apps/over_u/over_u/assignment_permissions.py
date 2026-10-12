"""Scope LMS assignment submissions to their learner and course authors."""

import frappe


def assignment_submission_has_permission(doc, user=None, ptype=None, **kwargs):
	from lms.lms.permissions import can_author_course

	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if user == "Administrator" or {"System Manager", "Moderator"} & set(roles):
		return True
	if ptype == "create":
		# Keep create authority with DocPerm; LMS populates the member in validation.
		return True
	if doc.member == user:
		return ptype != "share"

	course = doc.course or frappe.db.get_value("LMS Assignment", doc.assignment, "course")
	return can_author_course(course, user=user)


def assignment_submission_query(user=None):
	from lms.lms.permissions import can_author_course

	user = user or frappe.session.user
	if user == "Administrator" or {"System Manager", "Moderator"} & set(frappe.get_roles(user)):
		return ""

	courses = [
		name
		for name in frappe.get_all("LMS Course", pluck="name", limit_page_length=0)
		if can_author_course(name, user=user)
	]
	member_condition = f"`tabLMS Assignment Submission`.`member` = {frappe.db.escape(user)}"
	if not courses:
		return member_condition

	course_names = ", ".join(frappe.db.escape(name) for name in courses)
	instructor_condition = (
		"`tabLMS Assignment Submission`.`assignment` IN "
		"(SELECT `name` FROM `tabLMS Assignment` "
		f"WHERE `course` IN ({course_names}))"
	)
	return f"({member_condition} OR {instructor_condition})"
