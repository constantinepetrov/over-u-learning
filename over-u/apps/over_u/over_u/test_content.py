import json
import os
import tempfile

import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import content_loader, modules

TITLE = "OU Content Test Course"


class TestContent(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.info = modules.ensure_skeleton(TITLE)
		self.course = self.info["course"]
		self.paths = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for path in self.paths:
			os.unlink(path)
		super().tearDown()

	def _pack(self, data):
		handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
		json.dump(data, handle, ensure_ascii=False)
		handle.close()
		self.paths.append(handle.name)
		return handle.name

	def _chapter(self, number):
		for row in frappe.get_doc("LMS Course", self.course).chapters:
			if modules.module_number(frappe.db.get_value("Course Chapter", row.chapter, "title")) == number:
				return row.chapter

	def test_existing_named_modules_are_not_duplicated(self):
		frappe.db.set_value("Course Chapter", self._chapter(1), "title", "Модуль 1. Квантовый код")
		self.assertEqual(modules.ensure_skeleton(TITLE)["created"], [])
		self.assertEqual(modules.module_number("Модуль 1. Квантовый код"), 1)
		self.assertEqual(modules.module_number("Модуль 12"), 12)
		self.assertIsNone(modules.module_number("Золотой путь. Дело Жизни"))
		self.assertEqual(len(frappe.get_doc("LMS Course", self.course).chapters), 12)

	def test_loader_dry_run_apply_and_repeat(self):
		pack = self._pack(
			{
				"chapters": [
					{
						"title": "Как устроен курс",
						"first": True,
						"lessons": [
							{
								"title": "Цели 2+1",
								"source": "Описание курса.docx",
								"blocks": [
									{"type": "header", "text": "Две основные цели <b>x</b>"},
									{"type": "list", "items": ["Первая", "Вторая"]},
								],
							}
						],
					},
					{
						"module": 1,
						"lessons": [
							{
								"title": "Темы для обсуждения",
								"blocks": [
									{"type": "paragraph", "text": "Вопрос?"},
									{
										"type": "assignment",
										"title": "ДЗ модуля 1",
										"question": ["Вопрос 1", "Вопрос 2"],
									},
								],
							}
						],
					},
				],
				"course_intro": {"short": "Коротко", "paragraphs": ["Описание"]},
			}
		)
		before = frappe.db.count("Course Lesson", {"course": self.course})
		report = content_loader.load(pack, course=TITLE)
		self.assertFalse(report["apply"])
		self.assertEqual(frappe.db.count("Course Lesson", {"course": self.course}), before)
		self.assertEqual(len(report["created"]), 2)
		report = content_loader.load(pack, apply=1, course=TITLE)
		self.assertEqual(frappe.db.count("Course Lesson", {"course": self.course}), before + 2)
		self.assertEqual(report["assignments_created"], ["ДЗ модуля 1"])
		doc = frappe.get_doc("LMS Course", self.course)
		self.assertEqual(
			frappe.db.get_value("Course Chapter", doc.chapters[0].chapter, "title"), "Как устроен курс"
		)
		lesson = frappe.db.get_value("Course Lesson", {"title": "Цели 2+1", "course": self.course}, "content")
		self.assertIn("&lt;b&gt;", lesson)
		self.assertIn("• Первая", lesson)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "Course Lesson", "content": ["like", "%Описание курса.docx%"]},
			)
		)
		self.assertFalse(doc.published)
		self.assertEqual(doc.short_introduction, "Коротко")
		# Second run: nothing new, nothing overwritten.
		again = content_loader.load(pack, apply=1, course=TITLE)
		self.assertEqual(again["created"], [])
		self.assertEqual(again["assignments_created"], [])
		self.assertEqual(len(again["skipped"]), 3)
		self.assertEqual(frappe.db.count("Course Lesson", {"course": self.course}), before + 2)

	def test_existing_content_is_never_overwritten_and_placeholder_is_filled(self):
		chapter = frappe.get_doc("Course Chapter", self._chapter(2))
		written = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": "Уже написано",
				"course": self.course,
				"chapter": chapter.name,
				"content": json.dumps(
					{"blocks": [{"type": "paragraph", "data": {"text": "Авторский текст"}}]},
					ensure_ascii=False,
				),
			}
		).insert()
		blank = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": "Заготовка",
				"course": self.course,
				"chapter": chapter.name,
				"content": json.dumps({"blocks": [{"type": "paragraph", "data": {"text": "..."}}]}),
			}
		).insert()
		chapter.append("lessons", {"lesson": written.name})
		chapter.append("lessons", {"lesson": blank.name})
		chapter.save()
		pack = self._pack(
			{
				"chapters": [
					{
						"module": 2,
						"lessons": [
							{"title": "Уже написано", "blocks": [{"type": "paragraph", "text": "ЗАМЕНА"}]},
							{"title": "Заготовка", "blocks": [{"type": "paragraph", "text": "Новый текст"}]},
						],
					}
				]
			}
		)
		report = content_loader.load(pack, apply=1, course=TITLE)
		self.assertEqual(len(report["skipped"]), 1)
		self.assertEqual(len(report["filled"]), 1)
		self.assertIn("Авторский текст", frappe.db.get_value("Course Lesson", written.name, "content"))
		self.assertIn("Новый текст", frappe.db.get_value("Course Lesson", blank.name, "content"))

	def test_only_administrator_can_load(self):
		frappe.set_user(
			"over-u-teacher@example.com"
			if frappe.db.exists("User", "over-u-teacher@example.com")
			else "Guest"
		)
		with self.assertRaises(frappe.PermissionError):
			content_loader.load("/nonexistent.json")

	def test_renames_map_old_chapters_to_the_authors_scheme(self):
		chapter = self._chapter(1)
		frappe.db.set_value("Course Chapter", chapter, "title", "Модуль 1. Квантовый код")
		pack = self._pack(
			{
				"renames": {"Модуль 1. Квантовый код": "Предстарт"},
				"chapters": [
					{
						"title": "Предстарт",
						"lessons": [{"title": "Темы", "blocks": [{"type": "paragraph", "text": "Текст"}]}],
					}
				],
			}
		)
		dry = content_loader.load(pack, course=TITLE)
		self.assertEqual(dry["renamed"], ["Модуль 1. Квантовый код -> Предстарт"])
		self.assertEqual(dry["chapters_created"], [])
		self.assertEqual(frappe.db.get_value("Course Chapter", chapter, "title"), "Модуль 1. Квантовый код")
		done = content_loader.load(pack, apply=1, course=TITLE)
		self.assertEqual(frappe.db.get_value("Course Chapter", chapter, "title"), "Предстарт")
		self.assertEqual(done["chapters_created"], [])
		self.assertEqual(len(done["created"]), 1)
		again = content_loader.load(pack, apply=1, course=TITLE)
		self.assertEqual(again["renamed"], [])
