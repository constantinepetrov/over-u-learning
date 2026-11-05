"""Lesson discussions and the instructor desk.

Three conversations stay separate entities: comments under a lesson (this module),
personal homework (LMS Assignment Submission) and the answer feed with groups
(community_api). Every endpoint is scoped to the signed-in session; the browser never
supplies a member. Students reach a lesson only when it is theirs and unlocked; staff
reach only the courses they may author. Email addresses are shown to staff only.
"""

from urllib.parse import quote

import frappe
from frappe import _

from lms.lms import utils as lms
from over_u import goals_api, points
from over_u.profile_api import profile_of
from over_u.student_api import (
	KINDS,
	REVIEW_STATUSES,
	_member,
	_open_lesson,
	_text,
	review_courses,
	teacher_assignments,
)

MAX_TEXT = 2000
HOURLY_LIMIT = 30


# ---- access -----------------------------------------------------------------


def _can_moderate(course, user=None):
	from lms.lms.permissions import can_author_course

	user = user or frappe.session.user
	return bool(points.is_staff(user) and can_author_course(course, user=user))


def _staff_course(course):
	"""The course for an instructor who may author it; anyone else is refused."""
	me = _member()
	if not isinstance(course, str) or not course or not frappe.db.exists("LMS Course", course):
		frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
	if not _can_moderate(course, me):
		frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
	return course


def _lessons(course):
	"""number -> (module title, lesson title, kind) for a course outline."""
	result = {}
	for chapter in lms.get_course_outline(course):
		for row in chapter.lessons:
			result[row.number] = (chapter.title, row.title, KINDS.get(row.icon, "text"))
	return result


def _context(course, number):
	"""Return True for a moderator. Students must own an open lesson; staff only need the course."""
	me = _member()
	if _can_moderate(course, me):
		if number not in _lessons(course):
			frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
		return True
	_open_lesson(course, number)
	return False


# ---- lesson comments ---------------------------------------------------------


def _author(row, names):
	return names.get(row.member) or points.short_name(row.member)


def _render(row, names, me, moderator, replies=()):
	author = _author(row, names)
	return {
		"id": row.name,
		"author": author,
		"initial": (author or "?")[:1].upper(),
		"staff": bool(row.staff),
		"mine": row.member == me,
		"when": str(row.creation),
		"text": row.text or "",
		"private": bool(row.private),
		"pinned": bool(row.pinned),
		"hidden": bool(row.hidden),
		"can_delete": bool(moderator or (row.member == me and not row.staff)),
		"replies": list(replies),
	}


def _thread(course, number):
	me = _member()
	moderator = _can_moderate(course, me)
	rows = frappe.get_all(
		"OU Lesson Comment",
		{"course": course, "lesson": number},
		["name", "member", "staff", "reply_to", "text", "private", "pinned", "hidden", "creation"],
		order_by="creation asc",
		limit_page_length=0,
	)
	by_name = {row.name: row for row in rows}

	def root(row):
		return by_name.get(row.reply_to, row) if row.reply_to else row

	visible = []
	for row in rows:
		if moderator:
			visible.append(row)
			continue
		top = root(row)
		if row.hidden or top.hidden:
			continue
		# A private thread belongs to the student who opened it and to the instructors.
		if top.private and top.member != me:
			continue
		visible.append(row)
	names = {}
	for row in visible:
		if row.member not in names:
			names[row.member] = (
				frappe.db.get_value("User", row.member, "full_name") or points.short_name(row.member)
				if row.staff
				else points.short_name(row.member)
			)
	replies_of = {}
	for row in visible:
		if row.reply_to:
			replies_of.setdefault(row.reply_to, []).append(_render(row, names, me, moderator))
	roots = [
		_render(row, names, me, moderator, replies_of.get(row.name, []))
		for row in visible
		if not row.reply_to
	]
	roots.sort(key=lambda item: (not item["pinned"], item["when"]))
	return {
		"enabled": bool(points.setting("feed_enabled", 1)),
		"messages": roots,
		"can_moderate": moderator,
		"count": sum(1 + len(item["replies"]) for item in roots),
	}


@frappe.whitelist(methods=["POST"])
def lesson_comments(course: str, number: str):
	_context(course, number)
	return _thread(course, number)


@frappe.whitelist(methods=["POST"])
def post_lesson_comment(course: str, number: str, text: str, reply_to: str = "", private: int = 0):
	moderator = _context(course, number)
	me = _member()
	if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_TEXT:
		frappe.throw(_("Write a message between 1 and 2,000 characters."))
	recent = frappe.db.count(
		"OU Lesson Comment",
		{"member": me, "creation": [">=", frappe.utils.add_to_date(None, hours=-1)]},
	)
	if recent >= HOURLY_LIMIT:
		frappe.throw(_("Too many messages. Please try again a little later."))
	parent, make_private = "", bool(int(private or 0))
	if reply_to:
		target = frappe.db.get_value(
			"OU Lesson Comment",
			reply_to,
			["name", "course", "lesson", "reply_to", "hidden", "private", "member"],
			as_dict=True,
		)
		if not target or target.course != course or target.lesson != number:
			frappe.throw(_("Message not found."), frappe.DoesNotExistError)
		top = (
			frappe.db.get_value(
				"OU Lesson Comment", target.reply_to, ["name", "hidden", "private", "member"], as_dict=True
			)
			if target.reply_to
			else target
		)
		if not moderator and (top.hidden or (top.private and top.member != me)):
			frappe.throw(_("Message not found."), frappe.DoesNotExistError)
		# Replies stay one level deep and inherit the privacy of the thread they continue.
		parent, make_private = top.name, bool(top.private)
	# nosemgrep: lms-unjustified-ignore-permissions - comments are written for the verified session user after lesson access checks; learners have no DocPerm on the doctype
	doc = frappe.get_doc(
		{
			"doctype": "OU Lesson Comment",
			"course": course,
			"lesson": number,
			"member": me,
			"staff": 1 if moderator else 0,
			"reply_to": parent or None,
			"text": text.strip(),
			"private": 1 if make_private else 0,
		}
	).insert(ignore_permissions=True)
	if not moderator and not make_private:
		points.award(me, "comment_posted", f"dc:{doc.name}", course)
	return _thread(course, number)


@frappe.whitelist(methods=["POST"])
def moderate_lesson_comment(course: str, number: str, comment: str, action: str):
	moderator = _context(course, number)
	me = _member()
	if action not in ("pin", "unpin", "hide", "unhide", "delete"):
		frappe.throw(_("Unknown action."))
	target = frappe.db.get_value(
		"OU Lesson Comment",
		comment,
		["name", "course", "lesson", "member", "staff", "reply_to"],
		as_dict=True,
	)
	if not target or target.course != course or target.lesson != number:
		frappe.throw(_("Message not found."), frappe.DoesNotExistError)
	if action == "delete":
		if not (moderator or (target.member == me and not target.staff)):
			frappe.throw(_("You cannot delete this message."), frappe.PermissionError)
		for name in [target.name] + frappe.get_all(
			"OU Lesson Comment", {"reply_to": target.name}, pluck="name"
		):
			points.revoke(f"dc:{name}")
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is the author or an instructor of this course
		frappe.delete_doc("OU Lesson Comment", target.name, ignore_permissions=True, force=True)
	else:
		if not moderator:
			frappe.throw(_("Only instructors can moderate the feed."), frappe.PermissionError)
		if action in ("pin", "unpin") and target.reply_to:
			frappe.throw(_("Only a whole discussion can be pinned."))
		field, value = {
			"pin": ("pinned", 1),
			"unpin": ("pinned", 0),
			"hide": ("hidden", 1),
			"unhide": ("hidden", 0),
		}[action]
		frappe.db.set_value("OU Lesson Comment", target.name, field, value)
	return _thread(course, number)


# ---- instructor desk ---------------------------------------------------------


def _titles(courses):
	return {
		row.name: row.title
		for row in frappe.get_all(
			"LMS Course", {"name": ["in", courses]}, ["name", "title"], limit_page_length=0
		)
	}


def _attention(courses):
	"""Open discussions whose last word belongs to a student."""
	if not courses:
		return []
	rows = frappe.get_all(
		"OU Lesson Comment",
		{"course": ["in", courses], "hidden": 0},
		["name", "course", "lesson", "member", "staff", "reply_to", "text", "creation"],
		order_by="creation asc",
		limit_page_length=0,
	)
	threads = {}
	for row in rows:
		threads.setdefault(row.reply_to or row.name, []).append(row)
	lessons, titles, found = {}, _titles(courses), []
	for root_name, items in threads.items():
		first = next((item for item in items if item.name == root_name), None)
		if not first or first.staff:
			continue
		last = items[-1]
		if last.staff:
			continue
		if first.course not in lessons:
			lessons[first.course] = _lessons(first.course)
		module, title, _kind = lessons[first.course].get(first.lesson, ("", first.lesson, "text"))
		found.append(
			{
				"id": root_name,
				"course": first.course,
				"course_title": titles.get(first.course, first.course),
				"module": module,
				"lesson": title,
				"number": first.lesson,
				"author": points.short_name(last.member),
				"student": last.member,
				"text": _text(last.text)[:240],
				"when": str(last.creation),
				"messages": len(items),
				"href": f"/school/teacher/courses/{first.course}/lessons/{first.lesson}",
			}
		)
	found.sort(key=lambda item: item["when"])
	return found


@frappe.whitelist()
def teacher_desk(status: str = "Not Graded", course: str = ""):
	me = _member()
	courses = review_courses(me)
	if status not in REVIEW_STATUSES + ("",):
		frappe.throw(_("Unknown filter."))
	titles = _titles(courses)
	students = set()
	for name in courses:
		students.update(points._enrolled(name))
	pending = teacher_assignments("Not Graded", course) if status != "Not Graded" else None
	queue = teacher_assignments(status, course)
	if pending is None:
		pending = queue
	questions = [q for q in _attention(courses) if not course or q["course"] == course]
	return {
		"counters": {
			"to_review": len(pending),
			"questions": len(questions),
			"students": len(students),
			"courses": len(courses),
			"reports_today": frappe.db.count(
				"OU Daily Report",
				{"report_date": frappe.utils.today(), "member": ["in", list(students) or [""]]},
			),
		},
		"filter": {"status": status, "course": course},
		"courses": [{"id": name, "title": titles.get(name, name)} for name in courses],
		"queue": queue,
		"questions": questions[:50],
	}


def _progress(member, course, total):
	done = frappe.db.count("LMS Course Progress", {"member": member, "course": course, "status": "Complete"})
	return {"completed": done, "total": total, "percent": round(done / total * 100) if total else 0}


def _course_students(course):
	total = len(_lessons(course))
	pending = {}
	for row in frappe.get_all(
		"LMS Assignment Submission",
		{"course": course, "status": "Not Graded"},
		["member"],
		limit_page_length=0,
	):
		pending[row.member] = pending.get(row.member, 0) + 1
	result = []
	for member in points._enrolled(course):
		name = frappe.db.get_value("User", member, "full_name") or member
		result.append(
			{
				"student": member,
				"name": name,
				"progress": _progress(member, course, total),
				"pending": pending.get(member, 0),
				"href": "/school/teacher/students/" + quote(member, safe=""),
			}
		)
	result.sort(key=lambda item: item["name"].lower())
	return result


@frappe.whitelist()
def teacher_course(course: str):
	_staff_course(course)
	title = frappe.db.get_value("LMS Course", course, "title")
	pending_by_lesson = {}
	for row in frappe.get_all(
		"LMS Assignment Submission",
		{"course": course, "status": "Not Graded"},
		["lesson"],
		limit_page_length=0,
	):
		pending_by_lesson[row.lesson] = pending_by_lesson.get(row.lesson, 0) + 1
	open_questions = {}
	for item in _attention([course]):
		open_questions[item["number"]] = open_questions.get(item["number"], 0) + 1
	comments = {}
	for row in frappe.get_all("OU Lesson Comment", {"course": course}, ["lesson"], limit_page_length=0):
		comments[row.lesson] = comments.get(row.lesson, 0) + 1
	modules = []
	for chapter in lms.get_course_outline(course):
		modules.append(
			{
				"title": chapter.title,
				"lessons": [
					{
						"number": row.number,
						"title": row.title,
						"kind": KINDS.get(row.icon, "text"),
						"pending": pending_by_lesson.get(row.name, 0),
						"questions": open_questions.get(row.number, 0),
						"comments": comments.get(row.number, 0),
						"href": f"/school/teacher/courses/{course}/lessons/{row.number}",
					}
					for row in chapter.lessons
				],
			}
		)
	return {
		"id": course,
		"title": title,
		"modules": modules,
		"students": _course_students(course),
		"questions": _attention([course]),
		"counters": {
			"to_review": sum(pending_by_lesson.values()),
			"questions": sum(open_questions.values()),
			"students": len(points._enrolled(course)),
		},
	}


@frappe.whitelist()
def teacher_lesson(course: str, number: str):
	_staff_course(course)
	lessons = _lessons(course)
	if number not in lessons:
		frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
	module, title, kind = lessons[number]
	return {
		"course": course,
		"course_title": frappe.db.get_value("LMS Course", course, "title"),
		"module": module,
		"number": number,
		"title": title,
		"kind": kind,
		"discussion": _thread(course, number),
	}


@frappe.whitelist()
def teacher_student(student: str):
	me = _member()
	courses = review_courses(me)
	if not isinstance(student, str) or not frappe.db.exists("User", student):
		frappe.throw(_("Student not found."), frappe.DoesNotExistError)
	shared = [
		name for name in courses if frappe.db.exists("LMS Enrollment", {"course": name, "member": student})
	]
	if not shared or points.is_staff(student):
		frappe.throw(_("Student not found."), frappe.DoesNotExistError)
	titles = _titles(shared)
	cards = []
	for name in shared:
		lessons = _lessons(name)
		cards.append(
			{"id": name, "title": titles.get(name, name), "progress": _progress(student, name, len(lessons))}
		)
	submissions = []
	for row in frappe.get_all(
		"LMS Assignment Submission",
		{"member": student, "course": ["in", shared]},
		["name", "assignment_title", "course", "status", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	):
		submissions.append(
			{
				"name": row.name,
				"assignment": row.assignment_title or row.name,
				"course": titles.get(row.course, row.course),
				"status": row.status,
				"created": str(row.creation),
				"href": "/school/teacher/" + quote(row.name, safe=""),
			}
		)
	comments = []
	for row in frappe.get_all(
		"OU Lesson Comment",
		{"member": student, "course": ["in", shared]},
		["name", "course", "lesson", "text", "hidden", "private", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	):
		module, title, _kind = _lessons(row.course).get(row.lesson, ("", row.lesson, "text"))
		comments.append(
			{
				"text": _text(row.text)[:300],
				"course": titles.get(row.course, row.course),
				"lesson": title,
				"hidden": bool(row.hidden),
				"private": bool(row.private),
				"when": str(row.creation),
				"href": f"/school/teacher/courses/{row.course}/lessons/{row.lesson}",
			}
		)
	groups = [
		{"title": g.title, "kind": g.kind}
		for g in frappe.get_all(
			"OU Group",
			{"name": ["in", frappe.get_all("OU Group Member", {"member": student}, pluck="parent")]},
			["title", "kind"],
		)
	]
	goals = goals_api.goals_of(student)
	return {
		"student": student,
		"name": frappe.db.get_value("User", student, "full_name") or student,
		"goals": goals,
		"goals_percent": goals_api.overall(goals),
		"reports": goals_api.reports_of(student, limit=14),
		"points": points.total_for(student),
		"courses": cards,
		"submissions": submissions,
		"comments": comments,
		"groups": groups,
		"profile": profile_of(student),
	}
