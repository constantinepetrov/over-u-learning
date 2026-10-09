"""Version 1 student contract. All LMS internals live behind this adapter.

Every endpoint is session-scoped: there is deliberately no member, submission,
quiz or assignment selector supplied by the browser. Assessments are resolved
from the accessible lesson. Document writes retain upstream permissions/hooks.
"""
import json
import re
from urllib.parse import quote, urlsplit

import frappe
from frappe import _
from bs4 import BeautifulSoup

from lms.lms import utils as lms
from lms.lms.html_sanitizer import sanitize_rich_text
from over_u.policy import save_progress

API_VERSION = 1
KINDS = {"icon-youtube": "video", "icon-quiz": "quiz", "icon-assignment": "assignment"}


def _member():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Sign in to school to continue."), frappe.AuthenticationError)
    return user


def _access(course):
    member = _member()
    if not isinstance(course, str) or not lms.get_membership(course, member):
        frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
    # Student portal access is the LMS utility's course rule + own enrollment.
    # LMS Student deliberately has no generic LMS Course DocPerm (authoring Desk).
    if not lms.can_view_course(course):
        frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
    return frappe.get_doc("LMS Course", course)


def _text(value):
    return BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)


def _rich(value):
    return sanitize_rich_text(value or "") or ""


def _url(value):
    if not isinstance(value, str) or "\\" in value or any(ord(char) < 32 for char in value):
        return None
    parts = urlsplit(value)
    if parts.scheme in ("http", "https") and parts.netloc and not parts.username:
        return value
    if value.startswith("/") and not value.startswith("//") and not parts.scheme and not parts.netloc:
        return value
    return None


def _href(course, number=None):
    path = "/school/courses/" + quote(course, safe="")
    return path + "/lessons/" + number if number else path


def _blocks(doc):
    return lms.get_editorjs_blocks(doc.get("content"))


def _assessment_id(doc, kind):
    ids = [(b.get("data") or {}).get(kind) for b in _blocks(doc) if b.get("type") == kind]
    if len(ids) != 1 or not ids[0]:
        frappe.throw(_("This lesson format currently opens in the original learning interface."))
    return ids[0]


def _submission(assignment):
    # Scoped by an assessment in this user's unlocked course lesson and own member.
    rows = frappe.get_all("LMS Assignment Submission", filters={"assignment": assignment, "member": _member()},
                          fields=["name", "status", "answer", "comments", "modified"], limit=1)
    if not rows:
        return None
    return {"status": rows[0].status, "answer": _rich(rows[0].answer),
            "comments": _rich(rows[0].comments), "modified": rows[0].modified}


def _quiz_result(quiz):
    rows = frappe.get_all("LMS Quiz Submission", filters={"quiz": quiz, "member": _member()},
                          fields=["percentage", "score", "score_out_of", "passing_percentage"],
                          order_by="creation desc", limit=1)
    if not rows:
        return None
    row = rows[0]
    return {"percentage": row.percentage or 0, "score": row.score or 0, "score_out_of": row.score_out_of,
            "threshold": row.passing_percentage, "passed": (row.percentage or 0) >= row.passing_percentage}


def _snapshot(course):
    doc = _access(course)
    chapters = []
    for chapter in lms.get_course_outline(course, progress=True):
        lessons = []
        for row in chapter.lessons:
            item = {"title": row.title, "number": row.number, "kind": KINDS.get(row.icon, "text"),
                    "complete": bool(row.get("is_complete")), "locked": bool(row.get("locked")),
                    "href": _href(course, row.number), "chapter_title": chapter.title}
            if not item["locked"] and item["kind"] in ("assignment", "quiz"):
                # No raw content or assessment identifiers leave this summary payload.
                content = frappe.db.get_value("Course Lesson", row.name, "content")
                ids = [(b.get("data") or {}).get(item["kind"]) for b in lms.get_editorjs_blocks(content)
                       if b.get("type") == item["kind"]]
                if len(ids) == 1 and ids[0]:
                    item["assignment"] = _submission(ids[0]) if item["kind"] == "assignment" else None
                    item["quiz_result"] = _quiz_result(ids[0]) if item["kind"] == "quiz" else None
            lessons.append(item)
        chapters.append({"title": chapter.title, "number": chapter.idx, "lessons": lessons})
    flat = [row for chapter in chapters for row in chapter["lessons"]]
    completed = sum(row["complete"] for row in flat)
    current = next((row for row in flat if not row["complete"] and not row["locked"]), None)
    pending = [row for row in flat if (row.get("assignment") or {}).get("status") == "Not Graded"]
    return {"id": doc.name, "title": doc.title, "introduction": _text(doc.short_introduction),
            "chapters": chapters, "total": len(flat), "completed": completed,
            "progress": round(completed / len(flat) * 100, 1) if flat else 0,
            "current": current, "pending": pending, "href": _href(course),
            "next_href": current["href"] if current else _href(course)}


@frappe.whitelist()
def home():
    member = _member()
    courses = []
    # No student-supplied filters/identity: only the current session's enrollments.
    for name in frappe.get_all("LMS Enrollment", {"member": member}, pluck="course", order_by="creation desc"):
        if frappe.db.exists("LMS Course", name):
            courses.append(_snapshot(name))
    user = frappe.get_cached_doc("User", member)
    return {"api_version": API_VERSION, "user": {"first_name": user.first_name, "name": user.full_name,
                                                "email": member}, "courses": courses}


@frappe.whitelist()
def course(course: str):
    return _snapshot(course)


def _lesson(course, number):
    doc = _access(course)
    if not isinstance(number, str) or not re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", number):
        frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
    chapter, index = [int(part) for part in number.split("-")]
    result = lms.get_lesson(doc.name, chapter, index)
    if not result or result.get("not_found"):
        frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
    if result.get("locked"):
        return result
    if result.get("no_preview") or result.get("course") != doc.name or not result.get("name"):
        frappe.throw(_("This lesson is unavailable for your account."), frappe.PermissionError)
    return result


def _open_lesson(course, number):
    result = _lesson(course, number)
    if result.get("locked"):
        frappe.throw(_("Complete the previous lesson's requirements first."), frappe.PermissionError)
    return result


def _quiz(doc):
    quiz_id = _assessment_id(doc, "quiz")
    payload = lms.get_quiz_with_questions(quiz_id)
    quiz = payload["quiz"]
    # v1 deliberately refuses advanced exams instead of silently dropping rules.
    unsupported = any(quiz.get(key) for key in ("duration", "enable_proctoring", "shuffle_questions", "limit_questions_to"))
    rows = []
    for row in quiz.get("questions") or []:
        detail = payload["questions_by_name"].get(row["question"], {})
        unsupported |= detail.get("type") != "Choices" or bool(detail.get("multiple"))
        rows.append({"id": row["question"], "prompt": _text(detail.get("question")),
                     "options": [detail.get(f"option_{i}") for i in range(1, 6) if detail.get(f"option_{i}")]})
    count = frappe.db.count("LMS Quiz Submission", {"quiz": quiz_id, "member": _member()})
    maximum = quiz.get("max_attempts") or 0
    return {"title": quiz["title"], "threshold": quiz["passing_percentage"], "questions": rows,
            "attempts": count, "can_retry": not maximum or count < maximum, "max_attempts": maximum,
            "result": _quiz_result(quiz_id), "unsupported": bool(unsupported),
            "schedule_reason": _text(quiz.get("schedule_block_reason"))}


def _assignment(doc):
    assignment = lms.get_assignment(_assessment_id(doc, "assignment"))
    return {"title": assignment["title"], "instructions": _rich(assignment.get("question")),
            "type": assignment["type"], "submission": _submission(assignment["name"]),
            "schedule_reason": _text(assignment.get("schedule_block_reason"))}


@frappe.whitelist()
def lesson(course: str, number: str):
    snapshot = _snapshot(course)
    doc = _lesson(course, number)
    flat = [item for chapter in snapshot["chapters"] for item in chapter["lessons"]]
    item = next((item for item in flat if item["number"] == number), None)
    if not item:
        frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
    response = {"course": snapshot, "lesson": item, "blocks": [], "locked": bool(doc.get("locked"))}
    if response["locked"]:
        current = snapshot["current"] or {}
        submission = current.get("assignment") or {}
        response["lock_reason"] = (_("Wait for your teacher to review the homework first.") if submission.get("status") == "Not Graded"
                                   else _("Revise the homework and receive a pass first.") if submission.get("status") == "Fail"
                                   else _("Reach the quiz passing score first.") if current.get("kind") == "quiz"
                                   else _("Complete the previous lesson first."))
        return response
    for block in _blocks(doc):
        data = block.get("data") or {}
        kind = block.get("type")
        if kind in ("paragraph", "header", "quote"):
            response["blocks"].append({"type": kind, "html": _rich(data.get("text")),
                                       "level": min(4, max(2, int(data.get("level") or 2)))})
        elif kind == "upload":
            url = _url(data.get("file_url"))
            if url:
                media = "video" if (data.get("file_type") or "").lower() in ("mp4", "webm", "ogg", "mov") else "material"
                response["blocks"].append({"type": media, "url": url, "title": _text(data.get("file_name") or _("Lesson material"))})
        elif kind == "quiz":
            response["quiz"] = _quiz(doc)
        elif kind == "assignment":
            response["assignment"] = _assignment(doc)
        elif kind == "delimiter":
            response["blocks"].append({"type": "divider"})
        else:
            response["unsupported_content"] = True
    if doc.get("body") and not doc.get("content"):
        response["unsupported_content"] = True
    next_index = flat.index(item) + 1
    response["next"] = flat[next_index] if next_index < len(flat) else None
    return response


@frappe.whitelist(methods=["POST"])
def complete_lesson(course: str, number: str):
    doc = _open_lesson(course, number)
    save_progress(doc.name, course)
    return lesson(course, number)


@frappe.whitelist(methods=["POST"])
def submit_quiz(course: str, number: str, answers: list):
    from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz as upstream_submit
    doc = _open_lesson(course, number)
    quiz = _quiz(doc)
    if quiz["unsupported"]:
        frappe.throw(_("This quiz format currently opens in the original learning interface."))
    if not quiz["can_retry"]:
        frappe.throw(_("You have no attempts left. Contact your teacher."))
    if not isinstance(answers, list) or len(answers) != len(quiz["questions"]):
        frappe.throw(_("Answer every question."))
    results = []
    for question, answer in zip(quiz["questions"], answers, strict=True):
        if not isinstance(answer, str) or answer not in question["options"]:
            frappe.throw(_("Choose one of the available answers."))
        results.append({"question_name": question["id"], "answer": [answer]})
    result = upstream_submit(_assessment_id(doc, "quiz"), json.dumps(results))
    # Keep core progression semantics, including all assessments on a lesson.
    if result["pass"]:
        save_progress(doc.name, course)
    return lesson(course, number)


@frappe.whitelist(methods=["POST"])
def submit_assignment(course: str, number: str, answer: str):
    doc = _open_lesson(course, number)
    details = _assignment(doc)
    if details["type"] != "Text":
        frappe.throw(_("This assignment format currently opens in the original learning interface."))
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 20_000:
        frappe.throw(_("Write an answer between 1 and 20,000 characters."))
    assignment = _assessment_id(doc, "assignment")
    existing = frappe.db.get_value("LMS Assignment Submission", {"assignment": assignment, "member": _member()}, "name")
    # Accept text only. Never accept status, evaluator, member, attachment or a document id.
    from html import escape
    value = "<p>" + escape(answer.strip()).replace("\n", "<br>") + "</p>"
    if existing:
        submission = frappe.get_doc("LMS Assignment Submission", existing)
        submission.answer = value
        submission.save()
    else:
        frappe.get_doc({"doctype": "LMS Assignment Submission", "assignment": assignment,
                        "member": _member(), "type": details["type"], "answer": value}).insert()
    return lesson(course, number)
