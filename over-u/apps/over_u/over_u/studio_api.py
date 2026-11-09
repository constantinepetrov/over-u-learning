"""Course studio for the instructor: modules, lessons, homework and publishing in /school.

Only simple lessons are edited here: headings, paragraphs and one homework task. Lessons that
carry a quiz, an uploaded video or file keep their content untouched and open in the
original editor. Nothing is deleted here, so a mistake never costs students their progress.
Every call is checked against the courses the caller may author.
"""

import html
import json

import frappe
from frappe import _

from over_u import modules
from over_u.discussion_api import _staff_course
from over_u.student_api import _member, review_courses
from over_u.video_api import FIELD as VIDEO_FIELD
from over_u.video_api import clean as clean_video

MAX_TITLE = 140
MAX_TEXT = 30000
MAX_TASK = 5000
SIMPLE = {"paragraph", "header", "assignment"}


def _blocks(lesson):
	try:
		return json.loads(lesson.content or "{}").get("blocks") or []
	except ValueError:
		return []


def _simple(lesson):
	blocks = _blocks(lesson)
	if lesson.body and not lesson.content:
		return False
	return (
		all(b.get("type") in SIMPLE for b in blocks)
		and sum(1 for b in blocks if b.get("type") == "assignment") <= 1
	)


def _to_text(blocks):
	lines = []
	for block in blocks:
		data = block.get("data") or {}
		if block.get("type") == "header":
			lines.append("# " + html.unescape(data.get("text") or ""))
		elif block.get("type") == "paragraph":
			lines.append(html.unescape((data.get("text") or "").replace("<br>", "\n")))
	return "\n\n".join(lines)


def _to_blocks(text):
	blocks = []
	for chunk in (text or "").replace("\r", "").split("\n\n"):
		chunk = chunk.strip()
		if not chunk:
			continue
		if chunk.startswith("# "):
			blocks.append({"type": "header", "data": {"text": html.escape(chunk[2:].strip()), "level": 2}})
		else:
			blocks.append({"type": "paragraph", "data": {"text": html.escape(chunk).replace("\n", "<br>")}})
	return blocks


def _content(blocks):
	return json.dumps({"blocks": blocks, "version": "2.29.0"}, ensure_ascii=False)


def _homework(lesson):
	for block in _blocks(lesson):
		if block.get("type") == "assignment":
			name = (block.get("data") or {}).get("assignment")
			if name and frappe.db.exists("LMS Assignment", name):
				return name, frappe.db.get_value("LMS Assignment", name, "question") or ""
	return None, ""


def _course_data(course):
	doc = frappe.get_doc("LMS Course", course)
	rows = []
	for ref in doc.get("chapters") or []:
		chapter = frappe.get_doc("Course Chapter", ref.chapter)
		lessons = []
		for index, item in enumerate(chapter.get("lessons") or [], 1):
			lesson = frappe.get_doc("Course Lesson", item.lesson)
			lessons.append(
				{
					"id": lesson.name,
					"title": lesson.title,
					"number": f"{ref.idx}-{index}",
					"editable": _simple(lesson),
					"homework": bool(_homework(lesson)[0]),
				}
			)
			if lessons[-1]["editable"]:
				name, task = _homework(lesson)
				lessons[-1]["text"] = _to_text(_blocks(lesson))
				lessons[-1]["video"] = lesson.get(VIDEO_FIELD) or ""
				lessons[-1]["task"] = html.unescape(frappe.utils.strip_html(task)) if name else ""
		rows.append({"id": chapter.name, "number": ref.idx, "title": chapter.title, "lessons": lessons})
	status = modules.status(course)
	return {
		"course": course,
		"title": doc.title,
		"published": bool(doc.published),
		"modules": rows,
		"ready": status["ready"],
	}


@frappe.whitelist()
def studio_courses():
	titles = frappe.get_all(
		"LMS Course", {"name": ["in", review_courses(_member()) or [""]]}, ["name", "title", "published"]
	)
	return {"courses": [{"id": c.name, "title": c.title, "published": bool(c.published)} for c in titles]}


@frappe.whitelist()
def studio_course(course: str):
	_staff_course(course)
	return _course_data(course)


@frappe.whitelist()
def studio_lesson(course: str, lesson: str):
	_staff_course(course)
	doc = _lesson_of(course, lesson)
	name, task = _homework(doc)
	return {
		"id": doc.name,
		"title": doc.title,
		"chapter": doc.chapter,
		"editable": _simple(doc),
		"text": _to_text(_blocks(doc)) if _simple(doc) else "",
		"video": doc.get(VIDEO_FIELD) or "",
		"homework": html.unescape(frappe.utils.strip_html(task)) if name else "",
	}


def _lesson_of(course, lesson):
	if not isinstance(lesson, str) or not frappe.db.exists("Course Lesson", lesson):
		frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Course Lesson", lesson)
	if doc.course != course:
		frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
	return doc


def _chapter_of(course, chapter):
	if not isinstance(chapter, str) or not frappe.db.exists("Course Chapter", chapter):
		frappe.throw(_("Module not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Course Chapter", chapter)
	if doc.course != course:
		frappe.throw(_("Module not found."), frappe.DoesNotExistError)
	return doc


def _title(title):
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE:
		frappe.throw(_("Write a title of up to 140 characters."))
	return title.strip()


@frappe.whitelist(methods=["POST"])
def save_module(course: str, title: str, chapter: str = ""):
	_staff_course(course)
	title = _title(title)
	if chapter:
		doc = _chapter_of(course, chapter)
		doc.title = title
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		doc = frappe.get_doc({"doctype": "Course Chapter", "title": title, "course": course}).insert(
			ignore_permissions=True
		)
		parent = frappe.get_doc("LMS Course", course)
		parent.append("chapters", {"chapter": doc.name})
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		parent.save(ignore_permissions=True)
	return _course_data(course)


@frappe.whitelist(methods=["POST"])
def save_lesson(
	course: str, chapter: str, title: str, text: str, homework: str = "", lesson: str = "", video: str = ""
):
	_staff_course(course)
	title = _title(title)
	video = clean_video(video)
	if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
		frappe.throw(_("Write the lesson text."))
	if not isinstance(homework, str) or len(homework) > MAX_TASK:
		frappe.throw(_("The homework text is too long."))
	module = _chapter_of(course, chapter)
	blocks = _to_blocks(text)
	task = homework.strip()
	if lesson:
		doc = _lesson_of(course, lesson)
		if not _simple(doc):
			frappe.throw(_("This lesson has a quiz, video or file. Edit it in the original editor."))
		if doc.chapter != module.name:
			frappe.throw(_("A lesson cannot move to another module here."))
		name, _old = _homework(doc)
	else:
		doc, name = None, None
	if task:
		question = "<p>" + html.escape(task).replace("\n", "<br>") + "</p>"
		if name:
			frappe.db.set_value("LMS Assignment", name, "question", question)
		else:
			authors = [{"author": _member()}]
			# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
			created = frappe.get_doc(
				{
					"doctype": "LMS Assignment",
					"title": f"{title} (ДЗ)"[:140],
					"type": "Text",
					"grade_assignment": 1,
					"course": course,
					"question": question,
					"authors": authors,
				}
			).insert(ignore_permissions=True)
			name = created.name
		blocks.append({"type": "assignment", "data": {"assignment": name}})
	elif name:
		# The task stays (submissions may exist); the instructor clears it only in the original editor.
		blocks.append({"type": "assignment", "data": {"assignment": name}})
	if doc:
		doc.update({"title": title, "content": _content(blocks), VIDEO_FIELD: video})
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		new = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": title,
				"course": course,
				"chapter": module.name,
				"content": _content(blocks),
				VIDEO_FIELD: video,
			}
		).insert(ignore_permissions=True)
		module.append("lessons", {"lesson": new.name})
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		module.save(ignore_permissions=True)
	return _course_data(course)


@frappe.whitelist(methods=["POST"])
def move_item(course: str, kind: str, item: str, direction: str):
	_staff_course(course)
	if direction not in ("up", "down") or kind not in ("module", "lesson"):
		frappe.throw(_("Unknown action."))
	if kind == "module":
		parent, table, field = frappe.get_doc("LMS Course", course), "chapters", "chapter"
		_chapter_of(course, item)
	else:
		lesson = _lesson_of(course, item)
		parent, table, field = _chapter_of(course, lesson.chapter), "lessons", "lesson"
	rows = parent.get(table)
	index = next((i for i, r in enumerate(rows) if r.get(field) == item), None)
	if index is None:
		frappe.throw(_("Item not found."), frappe.DoesNotExistError)
	other = index - 1 if direction == "up" else index + 1
	if 0 <= other < len(rows):
		order = [r.get(field) for r in rows]
		order[index], order[other] = order[other], order[index]
		parent.set(table, [{field: name} for name in order])
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		parent.save(ignore_permissions=True)
	return _course_data(course)


@frappe.whitelist(methods=["POST"])
def set_published(course: str, published: int):
	_staff_course(course)
	if int(published) and _course_data(course)["ready"] == 0:
		frappe.throw(_("Add at least one lesson before publishing the course."))
	frappe.db.set_value("LMS Course", course, "published", 1 if int(published) else 0)
	return _course_data(course)
