"""The 12-module frame of the LIFELONG ENERGY course.

Only the numbered containers are created: the titles, topics and lessons are the author's
to write, so nothing here invents content. The course is created unpublished, and a module
without lessons is never shown to learners (see student_api._snapshot).

Run once, safe to repeat:  bench --site <site> execute over_u.modules.ensure_skeleton
"""

import frappe
from frappe import _

COURSE_TITLE = "LIFELONG ENERGY (Энерголетие)"
MODULES = 12


def _course(title):
	name = frappe.db.exists("LMS Course", {"title": title})
	if name:
		return frappe.get_doc("LMS Course", name)
	return None


def ensure_skeleton(title=COURSE_TITLE, instructor=None):
	if frappe.session.user != "Administrator":
		frappe.throw(_("Run as Administrator."), frappe.PermissionError)
	course = _course(title)
	if not course:
		values = {
			"doctype": "LMS Course",
			"title": title,
			"short_introduction": "Материал ожидается от автора курса.",
			"description": "<p>Материал ожидается от автора курса.</p>",
			"published": 0,
			"enforce_lesson_completion": 1,
			"over_u_require_assignment_pass": 1,
		}
		if instructor:
			values["instructors"] = [{"instructor": instructor}]
		course = frappe.get_doc(values).insert()
	have = {
		frappe.db.get_value("Course Chapter", row.chapter, "title") for row in course.get("chapters") or []
	}
	created = []
	for number in range(1, MODULES + 1):
		module = f"Модуль {number}"
		if module in have:
			continue
		chapter = frappe.get_doc(
			{"doctype": "Course Chapter", "title": module, "course": course.name}
		).insert()
		course.reload()
		course.append("chapters", {"chapter": chapter.name})
		course.save()
		created.append(module)
	return {"course": course.name, "created": created, "published": bool(course.published)}


def status(course):
	"""Per module: how many lessons are filled in. 0 lessons = «Материал ожидается»."""
	rows = []
	doc = frappe.get_doc("LMS Course", course)
	for ref in doc.get("chapters") or []:
		chapter = frappe.get_doc("Course Chapter", ref.chapter)
		count = len(chapter.get("lessons") or [])
		rows.append(
			{
				"number": ref.idx,
				"title": chapter.title,
				"lessons": count,
				"status": "Есть уроки" if count else "Материал ожидается",
			}
		)
	return {
		"course": course,
		"published": bool(doc.published),
		"modules": rows,
		"ready": sum(1 for r in rows if r["lessons"]),
	}
