from contextlib import contextmanager

import frappe
from frappe import _


@contextmanager
def as_member(member):
	previous = frappe.session.user
	try:
		frappe.set_user(member)
		yield
	finally:
		frappe.set_user(previous)


def course_requires_pass(course):
	return bool(course and frappe.get_cached_value("LMS Course", course, "over_u_require_assignment_pass"))


def completion_filters(lesson, assignment):
	course = frappe.db.get_value("Course Lesson", lesson, "course")
	return {"status": "Pass"} if course_requires_pass(course) else {}


@frappe.whitelist()
def save_progress(lesson: str, course: str, scorm_details: dict = None):
	from lms.lms.doctype.course_lesson.course_lesson import save_progress as upstream_save_progress

	if not isinstance(lesson, str) or not isinstance(course, str):
		frappe.throw(_("Lesson and course must be valid document names."))
	actual_course = frappe.db.get_value("Course Lesson", lesson, "course")
	if (course_requires_pass(course) or course_requires_pass(actual_course)) and actual_course != course:
		frappe.throw(_("Progress course must match the lesson course."), frappe.PermissionError)
	return upstream_save_progress(lesson, course, scorm_details)


def assignment_lessons(assignment):
	# Submission.lesson is absent in the stock SPA. Resolve authoritative content,
	# never a lesson/course supplied by a student's submission payload.
	from lms.lms.md import find_macros
	from lms.lms.utils import get_editorjs_blocks

	course = frappe.db.get_value("LMS Assignment", assignment, "course")
	if not course_requires_pass(course):
		return []
	matches = []
	for lesson in frappe.get_all("Course Lesson", {"course": course}, ["name", "course", "content", "body"]):
		if lesson.content:
			found = any(
				block.get("type") == "assignment"
				and (block.get("data") or {}).get("assignment") == assignment
				for block in get_editorjs_blocks(lesson.content)
			)
		else:
			found = ("Assignment", assignment) in find_macros(lesson.body or "")
		if found:
			matches.append(lesson)
	return matches


def assignment_submission_has_permission(doc, user=None, ptype=None, **kwargs):
	"""Limit private submission records to their learner and course authors."""
	from lms.lms.permissions import can_author_course

	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if user == "Administrator" or {"System Manager", "Moderator"} & set(roles):
		return True
	if ptype == "create":
		# Keep create authority with the standard DocPerm checks. The member may
		# only be populated later by LMS's submission controller.
		return True

	if doc.member == user:
		return ptype != "share"

	course = doc.course or frappe.db.get_value("LMS Assignment", doc.assignment, "course")
	return can_author_course(course, user=user)


def assignment_submission_query(user=None):
	"""Keep assignment list queries within the learner and instructor scope."""
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


def validate_submission(doc, method=None):
	previous = doc.get_doc_before_save()
	if previous and (previous.assignment != doc.assignment or previous.member != doc.member):
		if assignment_lessons(previous.assignment):
			frappe.throw(_("A reviewed submission cannot be moved to another learner or assignment."))
	# The stock submission form does not always send its lesson, so fetch_from
	# cannot populate course. Store the authoritative course from the assignment
	# to make instructor queues reliably scoped.
	assignment_course = frappe.db.get_value("LMS Assignment", doc.assignment, "course")
	if assignment_course:
		if doc.course and doc.course != assignment_course:
			frappe.throw(_("Submission course must match its assignment."), frappe.PermissionError)
		doc.course = assignment_course
	lessons = assignment_lessons(doc.assignment)
	if not lessons:
		return
	from lms.lms.permissions import can_author_course, get_locked_lessons

	author = can_author_course(lessons[0].course)
	if not author:
		if doc.member != frappe.session.user:
			frappe.throw(_("Only the learner can submit their own work."), frappe.PermissionError)
		if not frappe.db.exists("LMS Enrollment", {"course": lessons[0].course, "member": doc.member}):
			frappe.throw(_("Enrollment is required to submit this assignment."), frappe.PermissionError)
		if all(lesson.name in get_locked_lessons(lesson.course) for lesson in lessons):
			frappe.throw(
				_("Complete the previous lesson before submitting this assignment."), frappe.PermissionError
			)
	grading_changed = (not previous and doc.status == "Pass") or (previous and previous.status != doc.status)
	if grading_changed and doc.status in ("Pass", "Fail"):
		if not author or doc.member == frappe.session.user:
			frappe.throw(_("Only the course instructor can review this assignment."), frappe.PermissionError)
		doc.evaluator = frappe.session.user
	if not previous:
		return
	if previous.assignment != doc.assignment or previous.member != doc.member:
		frappe.throw(_("A reviewed submission cannot be moved to another learner or assignment."))
	content_changed = any(
		previous.get(field) != doc.get(field) for field in ("answer", "assignment_attachment")
	)
	if previous.status == "Pass" and content_changed:
		frappe.throw(_("A passed assignment is frozen. Change its grade before revising the answer."))
	if content_changed:
		doc.status = "Not Graded"
		doc.evaluator = None


def update_assignment_progress(doc, method=None):
	previous = doc.get_doc_before_save()
	if previous and previous.status == doc.status:
		return
	from lms.lms.doctype.course_lesson.course_lesson import get_assignment_progress, save_progress
	from lms.lms.permissions import get_locked_lessons

	with as_member(doc.member):
		for lesson in assignment_lessons(doc.assignment):
			if doc.status == "Pass":
				if lesson.name not in get_locked_lessons(lesson.course):
					save_progress(lesson.name, lesson.course)
			elif previous and previous.status == "Pass" and not get_assignment_progress(lesson.name):
				for name in frappe.get_all(
					"LMS Course Progress", {"lesson": lesson.name, "member": doc.member}, pluck="name"
				):
					# The grade has already passed the stock grading-permission check.
					frappe.delete_doc("LMS Course Progress", name, ignore_permissions=True)
				frappe.publish_realtime(
					"update_lesson_progress",
					{"course": lesson.course, "lesson": lesson.name},
					user=doc.member,
					after_commit=True,
				)


def validate_progress(doc, method=None):
	if not doc.lesson:
		return
	course = frappe.db.get_value("Course Lesson", doc.lesson, "course")
	if not course_requires_pass(course):
		return
	from lms.lms.doctype.course_lesson.course_lesson import get_assignment_progress, get_quiz_progress
	from lms.lms.permissions import get_locked_lessons

	if doc.course and doc.course != course:
		frappe.throw(_("Progress course must match the lesson course."), frappe.PermissionError)
	with as_member(doc.member):
		if not frappe.db.exists("LMS Enrollment", {"course": course, "member": doc.member}):
			frappe.throw(_("Enrollment is required to record progress."), frappe.PermissionError)
		if doc.lesson in get_locked_lessons(course):
			frappe.throw(_("Complete the previous lesson first."), frappe.PermissionError)
		if doc.status == "Complete" and (
			not get_assignment_progress(doc.lesson) or not get_quiz_progress(doc.lesson)
		):
			frappe.throw(
				_("Pass all required assessments before completing this lesson."), frappe.PermissionError
			)
