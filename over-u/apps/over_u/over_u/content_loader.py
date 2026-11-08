"""Loads author material into draft lessons from a content pack kept outside the repository.

The pack is a JSON file prepared from the author's own documents. The loader only adds:
it never overwrites a lesson that already has content, never deletes, never publishes, and
a dry run (the default) writes nothing. Every created or filled lesson gets an internal
comment naming its source file, so each text can be traced back to the original.

    bench --site <site> execute over_u.content_loader.load --kwargs '{"pack": "/tmp/pack.json"}'
    bench --site <site> execute over_u.content_loader.load --kwargs '{"pack": "/tmp/pack.json", "apply": 1}'
"""

import html
import json
import time

import frappe
from frappe import _

from over_u import modules

PLACEHOLDERS = ("", "...", "материал ожидается")


def _text(value):
	return html.escape(str(value or ""))


def _blocks(specs):
	blocks = []
	for spec in specs:
		kind = spec.get("type")
		if kind in ("header", "paragraph", "quote"):
			data = {"text": _text(spec.get("text"))}
			if kind == "header":
				data["level"] = int(spec.get("level") or 2)
			blocks.append({"type": kind, "data": data})
		elif kind == "list":
			blocks.extend(
				{"type": "paragraph", "data": {"text": "• " + _text(item)}}
				for item in spec.get("items") or []
			)
		elif kind == "delimiter":
			blocks.append({"type": "delimiter", "data": {}})
		elif kind == "assignment":
			blocks.append({"type": "assignment", "data": {"assignment": spec["_name"]}})
		else:
			frappe.throw(_("Unknown block type: {0}").format(kind))
	return json.dumps(
		{"time": int(time.time() * 1000), "blocks": blocks, "version": "2.29.0"}, ensure_ascii=False
	)


def _is_empty(content):
	try:
		blocks = json.loads(content or "{}").get("blocks") or []
	except ValueError:
		return False
	text = " ".join(html.unescape((b.get("data") or {}).get("text", "")) for b in blocks).strip().lower()
	return not blocks or (all(b.get("type") == "paragraph" for b in blocks) and text in PLACEHOLDERS)


def _shown(row, renames):
	"""A chapter's title as it will be once the planned renames are applied (also in a dry run)."""
	title = frappe.db.get_value("Course Chapter", row.chapter, "title")
	return renames.get(title, title)


def _rename(course, renames, apply, report):
	taken = {frappe.db.get_value("Course Chapter", r.chapter, "title") for r in course.get("chapters") or []}
	for old, new in renames.items():
		if old not in taken:
			continue
		if new in taken:
			report["problems"].append(f"cannot rename '{old}': '{new}' already exists")
			continue
		report["renamed"].append(f"{old} -> {new}")
		if apply:
			frappe.db.set_value("Course Chapter", {"course": course.name, "title": old}, "title", new)


def _chapter(course, spec, apply, report, renames):
	if "module" in spec:
		for row in course.get("chapters") or []:
			title = _shown(row, renames)
			if modules.module_number(title) == int(spec["module"]):
				return frappe.get_doc("Course Chapter", row.chapter)
		report["problems"].append(f"module {spec['module']} is missing: run ensure_skeleton first")
		return None
	title = spec["title"]
	for row in course.get("chapters") or []:
		if _shown(row, renames) == title:
			return frappe.get_doc("Course Chapter", row.chapter)
	report["chapters_created"].append(title)
	if not apply:
		return None
	# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
	chapter = frappe.get_doc({"doctype": "Course Chapter", "title": title, "course": course.name}).insert(
		ignore_permissions=True
	)
	order = [row.chapter for row in course.get("chapters") or []]
	# Lesson numbers are part of learners' links, so a new chapter goes first only while no
	# learner can see the course; a published course gets it at the end.
	order = [chapter.name, *order] if not course.published and spec.get("first") else [*order, chapter.name]
	course.set("chapters", [{"chapter": name} for name in order])
	# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
	course.save(ignore_permissions=True)
	return chapter


def _assignment(course, spec, apply, report):
	title = spec["title"]
	name = frappe.db.exists("LMS Assignment", {"title": title, "course": course.name})
	if name or not apply:
		return name or "(new)"
	question = "".join(f"<p>{_text(line)}</p>" for line in spec["question"])
	# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
	doc = frappe.get_doc(
		{
			"doctype": "LMS Assignment",
			"title": title,
			"type": "Text",
			"grade_assignment": 1,
			"course": course.name,
			"question": question,
		}
	).insert(ignore_permissions=True)
	report["assignments_created"].append(title)
	return doc.name


def _lesson(course, chapter, spec, apply, report):
	title = spec["title"]
	label = f"{chapter.title if chapter else spec.get('chapter', '?')} / {title}"
	specs = [dict(s) for s in spec["blocks"]]
	for block in specs:
		if block.get("type") == "assignment":
			block["_name"] = _assignment(course, block, apply, report)
	existing = (
		frappe.db.get_value(
			"Course Lesson",
			{"chapter": chapter.name, "title": title},
			["name", "content", "body"],
			as_dict=True,
		)
		if chapter
		else None
	)
	if existing and (existing.body or not _is_empty(existing.content)):
		report["skipped"].append(label)
		return
	report["filled" if existing else "created"].append(label)
	if not apply:
		return
	content = _blocks(specs)
	if existing:
		doc = frappe.get_doc("Course Lesson", existing.name)
		doc.content = content
		# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
		doc = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": title,
				"course": course.name,
				"chapter": chapter.name,
				"content": content,
			}
		).insert(ignore_permissions=True)
		chapter.append("lessons", {"lesson": doc.name})
		# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
		chapter.save(ignore_permissions=True)
	if spec.get("source"):
		doc.add_comment("Info", "Источник: " + spec["source"])


def load(pack, apply=0, course=None):
	if frappe.session.user != "Administrator":
		frappe.throw(_("Run as Administrator."), frappe.PermissionError)
	with open(pack, encoding="utf-8") as handle:
		data = json.load(handle)
	doc = modules.find_course(course)
	if not doc:
		frappe.throw(_("The course was not found. Run ensure_skeleton first."))
	report = {
		"course": doc.name,
		"published": bool(doc.published),
		"apply": bool(int(apply)),
		"renamed": [],
		"chapters_created": [],
		"assignments_created": [],
		"created": [],
		"filled": [],
		"skipped": [],
		"problems": [],
	}
	renames = data.get("renames") or {}
	_rename(doc, renames, bool(int(apply)), report)
	doc.reload()
	if int(apply):
		renames = {}  # already applied to the database
	for spec in data.get("chapters", []):
		chapter = _chapter(doc, spec, bool(int(apply)), report, renames)
		for lesson in spec.get("lessons", []):
			_lesson(
				doc,
				chapter,
				{**lesson, "chapter": spec.get("title") or f"Модуль {spec.get('module')}"},
				bool(int(apply)),
				report,
			)
		doc.reload()
	if data.get("course_intro") and int(apply):
		if doc.description in (None, "", "<p>Материал ожидается от автора курса.</p>"):
			doc.short_introduction = data["course_intro"].get("short", doc.short_introduction)
			doc.description = "".join(
				f"<p>{_text(p)}</p>" for p in data["course_intro"].get("paragraphs", [])
			)
			# nosemgrep: lms-unjustified-ignore-permissions - administrator-run content import into a draft course
			doc.save(ignore_permissions=True)
			report["created"].append("course introduction")
		else:
			report["skipped"].append("course introduction (already written)")
	return report
