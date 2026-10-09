import json
import os

import frappe
from frappe.utils.password import update_password

COURSE_TITLE = "OVER U — Основы осознанного обучения"
TEACHER = "teacher@over-u.example.com"
STUDENTS = ["student1@over-u.example.com", "student2@over-u.example.com"]


def _user(email, first_name, roles):
    if not frappe.db.exists("User", email):
        doc = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name,
                              "enabled": 1, "send_welcome_email": 0, "user_type": "Website User",
                              "roles": [{"role": role} for role in roles]})
        doc.insert()
        update_password(email, os.environ["OVER_U_DEMO_PASSWORD"])
    return frappe.get_doc("User", email)


def _content(*blocks):
    return json.dumps({"blocks": [{"type": kind, "data": data} for kind, data in blocks],
                       "version": "2.29.0"}, ensure_ascii=False)


def seed():
    if frappe.session.user != "Administrator":
        frappe.throw("Run seed as Administrator.", frappe.PermissionError)
    _user(TEACHER, "Преподаватель OVER U", ["Course Creator"])
    for i, email in enumerate(STUDENTS, 1):
        _user(email, f"Ученик {i} OVER U", ["LMS Student"])
    existing = frappe.db.exists("LMS Course", {"title": COURSE_TITLE})
    if existing:
        repair_demo_video(existing)
        return manifest(existing)
    course = frappe.get_doc({"doctype": "LMS Course", "title": COURSE_TITLE,
                            "short_introduction": "Демо: уроки, тест 75%, домашнее задание и зачёт преподавателя.",
                            "description": "<p>Три модуля OVER U. Следующий урок открывается после выполнения предыдущего.</p>",
                            "published": 1, "enforce_lesson_completion": 1,
                            "over_u_require_assignment_pass": 1,
                            "instructors": [{"instructor": TEACHER}]}).insert()
    questions = []
    for prompt, correct, wrong in [
        ("Когда откроется следующий обязательный урок?", "После выполнения требований предыдущего", "Сразу после входа"),
        ("Какой проходной балл у этого теста?", "75%", "25%"),
        ("Что необходимо для зачёта домашней работы?", "Преподаватель поставил зачёт", "Только отправка"),
        ("Какой размер цели удобнее для первого шага?", "Один измеримый шаг", "Любая абстрактная мечта"),
    ]:
        questions.append(frappe.get_doc({"doctype": "LMS Question", "question": prompt, "type": "Choices",
                                         "option_1": correct, "is_correct_1": 1, "option_2": wrong,
                                         "marks": 1, "authors": [{"author": TEACHER}]}).insert())
    quiz = frappe.get_doc({"doctype": "LMS Quiz", "title": "OVER U — Проверка основ",
                           "passing_percentage": 75, "max_attempts": 0,
                           "authors": [{"author": TEACHER}],
                           "questions": [{"question": q.name, "marks": 1} for q in questions]}).insert()
    assignment = frappe.get_doc({"doctype": "LMS Assignment", "title": "OVER U — Мой план обучения",
                                 "type": "Text", "grade_assignment": 1, "course": course.name,
                                 "question": "<p>Опишите цель, один измеримый шаг и время выполнения. Преподаватель проверит работу и поставит «Зачтено» или «Не зачтено».</p>",
                                 "authors": [{"author": TEACHER}]}).insert()
    modules = [
        ("1. Начало", [
            ("1.1 Добро пожаловать", _content(("header", {"text": "Ваша школа OVER U", "level": 2}),
                 ("paragraph", {"text": "Сформулируйте, чему хотите научиться. Прочитайте урок и перейдите дальше."}))),
            ("1.2 Видео и первый шаг", _content(("paragraph", {"text": "Посмотрите короткое штатное демо-видео редактора и выберите один шаг."}),
                 ("upload", {"file_url": "/assets/lms/frontend/Quiz.mp4", "file_type": "MP4"}))),
        ]),
        ("2. Проверка знаний", [
            ("2.1 Измеримая цель", _content(("paragraph", {"text": "Хорошая цель включает действие, результат и срок. Пример: пройти один модуль до пятницы."}))),
            ("2.2 Тест — минимум 75%", _content(("quiz", {"quiz": quiz.name}))),
        ]),
        ("3. Практика", [
            ("3.1 Домашнее задание", _content(("assignment", {"assignment": assignment.name}))),
            ("3.2 Подведение итогов", _content(("paragraph", {"text": "Работа зачтена преподавателем. Вы завершили демо-курс OVER U."}))),
        ]),
    ]
    for title, lessons in modules:
        chapter = frappe.get_doc({"doctype": "Course Chapter", "title": title, "course": course.name}).insert()
        course.reload()
        course.append("chapters", {"chapter": chapter.name})
        course.save()
        for lesson_title, content in lessons:
            lesson = frappe.get_doc({"doctype": "Course Lesson", "title": lesson_title,
                                     "course": course.name, "chapter": chapter.name, "content": content}).insert()
            chapter.reload()
            chapter.append("lessons", {"lesson": lesson.name})
            chapter.save()
    for email in STUDENTS:
        frappe.get_doc({"doctype": "LMS Enrollment", "course": course.name, "member": email}).insert()
    for field in ("enforce_quiz_completion", "enforce_assignment_completion", "persona_captured"):
        frappe.db.set_single_value("LMS Settings", field, 1)
    frappe.db.set_single_value("Website Settings", "app_name", "OVER U")
    frappe.db.set_default("setup_complete", 1)
    return manifest(course.name)


def manifest(course=None):
    course = course or frappe.db.exists("LMS Course", {"title": COURSE_TITLE})
    return {"course": course, "teacher": TEACHER, "students": STUDENTS,
            "lessons": frappe.get_all("Course Lesson", {"course": course}, ["name", "title", "chapter"], order_by="creation asc"),
            "quiz": frappe.db.exists("LMS Quiz", {"title": "OVER U — Проверка основ"}),
            "assignment": frappe.db.exists("LMS Assignment", {"title": "OVER U — Мой план обучения"})}


def repair_demo_video(course=None):
    course = course or frappe.db.exists("LMS Course", {"title": COURSE_TITLE})
    name = frappe.db.exists("Course Lesson", {"course": course, "title": "1.2 Видео и первый шаг"})
    if not name:
        return
    lesson = frappe.get_doc("Course Lesson", name)
    data = json.loads(lesson.content)
    changed = False
    for block in data.get("blocks", []):
        item = block.get("data") or {}
        if block.get("type") == "upload" and item.get("file_url") == "/assets/lms/frontend/Quiz.mp4" and item.get("file_type") == "video/mp4":
            item["file_type"] = "MP4"
            changed = True
    if changed:
        lesson.content = json.dumps(data, ensure_ascii=False)
        lesson.save()


def runtime_summary():
    import lms
    from over_u.policy import as_member
    from lms.lms.permissions import get_locked_lessons

    data = manifest()
    course = frappe.get_doc("LMS Course", data["course"])
    students = []
    for email in STUDENTS:
        with as_member(email):
            students.append({"user": email,
                             "progress": frappe.db.get_value("LMS Enrollment", {"course": course.name, "member": email}, "progress"),
                             "locked_lessons": len(get_locked_lessons(course.name))})
    return {"frappe_version": frappe.__version__, "lms_version": lms.__version__,
            "installed_apps": frappe.get_installed_apps(), "course": course.name,
            "chapters": len(course.chapters), "lessons": len(data["lessons"]),
            "sequential_completion": bool(course.enforce_lesson_completion),
            "assignment_requires_pass": bool(course.over_u_require_assignment_pass),
            "quiz_passing_percentage": frappe.db.get_value("LMS Quiz", data["quiz"], "passing_percentage"),
            "administrator_exists": bool(frappe.db.exists("User", "Administrator")),
            "teacher_roles": frappe.get_roles(TEACHER), "students": students,
            "quiz_submissions": frappe.get_all("LMS Quiz Submission", {"quiz": data["quiz"], "member": ["in", STUDENTS]}, ["name", "member", "percentage"]),
            "assignments": frappe.get_all("LMS Assignment Submission", {"assignment": data["assignment"], "member": ["in", STUDENTS]}, ["name", "member", "status", "evaluator"])}
