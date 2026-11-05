"""The 12-module frame of the LIFELONG ENERGY course.

Only the numbered containers are created: the titles, topics and lessons are the author's
to write, so nothing here invents content. The course is created unpublished, and a module
without lessons is never shown to learners (see student_api._snapshot).

Run once, safe to repeat:  bench --site <site> execute over_u.modules.ensure_skeleton
"""

import re

import frappe
from frappe import _

COURSE_TITLE = "LIFELONG ENERGY (Энерголетие)"
# The production course was created earlier under the name "Энерголетие"; never create a second one.
COURSE_TITLES = ("Энерголетие", "LIFELONG ENERGY", COURSE_TITLE)
MODULES = 12


def find_course(title=None):
	for candidate in (title,) if title else COURSE_TITLES:
		name = frappe.db.exists("LMS Course", {"title": candidate})
		if name:
			return frappe.get_doc("LMS Course", name)
	return None


def module_number(title):
	"""«Модуль 3», «Модуль 1. Квантовый код» and «3. Название» all mean module 3."""
	match = re.match(r"^\s*(?:Модуль\s*)?(\d{1,2})(?:\D|$)", title or "")
	return int(match.group(1)) if match and "Модуль" in (title or "") else None


def ensure_skeleton(title=None, instructor=None):
	if frappe.session.user != "Administrator":
		frappe.throw(_("Run as Administrator."), frappe.PermissionError)
	course = find_course(title)
	if not course:
		values = {
			"doctype": "LMS Course",
			"title": title or COURSE_TITLE,
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
		module_number(frappe.db.get_value("Course Chapter", row.chapter, "title"))
		for row in course.get("chapters") or []
	}
	created = []
	for number in range(1, MODULES + 1):
		if number in have:
			continue
		module = f"Модуль {number}"
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
