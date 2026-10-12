"""Temporary data helpers for the isolated GitHub Actions integration run."""

import frappe


def create_http_upload_probe():
	"""Create an isolated course for a student-authenticated upload_file test."""
	import json

	from over_u.school import STUDENTS, TEACHER, _user

	if frappe.session.user != "Administrator":
		frappe.throw("Run upload probe setup as Administrator.", frappe.PermissionError)

	_user("over-u-unrelated-teacher@example.com", "Unrelated Synthetic Teacher", ["Course Creator"])
	title = "OVER U CI private upload probe"
	course_name = frappe.db.exists("LMS Course", {"title": title})
	if not course_name:
		course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": title,
				"published": 1,
				"enforce_lesson_completion": 0,
				"instructors": [{"instructor": TEACHER}],
			}
		).insert()
		chapter = frappe.get_doc({"doctype": "Course Chapter", "title": "Upload probe", "course": course.name}).insert()
		course.append("chapters", {"chapter": chapter.name})
		course.save()
		assignment = frappe.get_doc(
			{
				"doctype": "LMS Assignment",
				"title": "OVER U CI private upload probe",
				"type": "Text",
				"grade_assignment": 1,
				"course": course.name,
				"question": "Submit synthetic text for file privacy testing.",
				"authors": [{"author": TEACHER}],
			}
		).insert()
		lesson = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": "Upload privacy probe",
				"course": course.name,
				"chapter": chapter.name,
				"content": json.dumps(
					{"blocks": [{"type": "assignment", "data": {"assignment": assignment.name}}]},
					ensure_ascii=False,
				),
			}
		).insert()
		chapter.append("lessons", {"lesson": lesson.name})
		chapter.save()
		course_name = course.name
	else:
		assignment = frappe.db.get_value("LMS Assignment", {"title": title}, "name")
		lesson = frappe.db.get_value("Course Lesson", {"course": course_name, "title": "Upload privacy probe"}, "name")

	if not frappe.db.exists("LMS Enrollment", {"course": course_name, "member": STUDENTS[0]}):
		frappe.get_doc({"doctype": "LMS Enrollment", "course": course_name, "member": STUDENTS[0]}).insert()
	return {"course": course_name, "assignment": assignment.name if hasattr(assignment, "name") else assignment,
		"lesson": lesson.name if hasattr(lesson, "name") else lesson, "student": STUDENTS[0]}
