import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import studio_api as studio
from over_u.school import TEACHER, manifest


class TestStudio(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.course = manifest()["course"]
		self.student = self._create_user(
			"over-u-studio-s@example.com", "Ученик", "Студии", ["LMS Student"]
		).name
		frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": self.student}).insert()
		self.created = []

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_learner_cannot_use_the_studio(self):
		frappe.set_user(self.student)
		with self.assertRaises(frappe.PermissionError):
			studio.studio_course(self.course)
		with self.assertRaises(frappe.PermissionError):
			studio.save_module(self.course, "Взлом")
		with self.assertRaises(frappe.PermissionError):
			studio.set_published(self.course, 0)

	def test_instructor_builds_module_and_lesson_with_homework(self):
		frappe.set_user(TEACHER)
		before = studio.studio_course(self.course)
		data = studio.save_module(self.course, "Новый модуль студии")
		self.assertEqual(len(data["modules"]), len(before["modules"]) + 1)
		chapter = data["modules"][-1]["id"]
		with self.assertRaises(frappe.ValidationError):
			studio.save_lesson(self.course, chapter, "  ", "Текст")
		data = studio.save_lesson(
			self.course, chapter, "Первый урок", "# Заголовок\n\nАбзац <script>x</script>", "Опишите шаг"
		)
		lesson = data["modules"][-1]["lessons"][0]
		self.assertTrue(lesson["editable"])
		self.assertTrue(lesson["homework"])
		card = studio.studio_lesson(self.course, lesson["id"])
		self.assertIn("# Заголовок", card["text"])
		self.assertEqual(card["homework"], "Опишите шаг")
		self.assertNotIn("<script>", frappe.db.get_value("Course Lesson", lesson["id"], "content"))
		# Editing keeps the same homework task instead of creating a second one.
		count = frappe.db.count("LMS Assignment", {"course": self.course})
		studio.save_lesson(
			self.course, chapter, "Первый урок v2", "Новый текст", "Опишите два шага", lesson["id"]
		)
		self.assertEqual(frappe.db.count("LMS Assignment", {"course": self.course}), count)
		self.assertEqual(studio.studio_lesson(self.course, lesson["id"])["homework"], "Опишите два шага")
		# Clearing the field never removes the task: students' answers may exist.
		studio.save_lesson(self.course, chapter, "Первый урок v2", "Новый текст", "", lesson["id"])
		self.assertTrue(studio.studio_lesson(self.course, lesson["id"])["homework"])

	def test_lesson_video_by_link(self):
		from over_u import video_api

		frappe.set_user(TEACHER)
		chapter = studio.save_module(self.course, "Модуль с видео")["modules"][-1]["id"]
		link = "https://rutube.ru/video/0123456789abcdef0123456789abcdef/"
		data = studio.save_lesson(self.course, chapter, "Урок с видео", "Текст", "", "", link)
		lesson = data["modules"][-1]["lessons"][0]
		self.assertEqual(lesson["video"], link)
		block = video_api.lesson_block(self.course, "1-1", lesson["id"])
		self.assertEqual(block["type"], "embed")
		self.assertTrue(block["src"].startswith("https://rutube.ru/play/embed/"))
		with self.assertRaises(frappe.ValidationError):
			studio.save_lesson(
				self.course, chapter, "Урок с видео", "Текст", "", lesson["id"], "https://example.com/a.mp4"
			)
		yandex = "https://disk.yandex.ru/i/XZW01pZKSkJmFA"
		studio.save_lesson(self.course, chapter, "Урок с видео", "Текст", "", lesson["id"], yandex)
		block = video_api.lesson_block(self.course, "1-1", lesson["id"])
		self.assertEqual(block["type"], "video")
		self.assertIn("over_u.video_api.stream", block["url"])
		studio.save_lesson(self.course, chapter, "Урок с видео", "Текст", "", lesson["id"], "")
		self.assertIsNone(video_api.lesson_block(self.course, "1-1", lesson["id"]))

	def test_lessons_with_quiz_are_not_editable_here(self):
		frappe.set_user(TEACHER)
		data = studio.studio_course(self.course)
		heavy = [l for m in data["modules"] for l in m["lessons"] if not l["editable"]]
		self.assertTrue(heavy)
		module = next(m for m in data["modules"] if any(l["id"] == heavy[0]["id"] for l in m["lessons"]))
		with self.assertRaises(frappe.ValidationError):
			studio.save_lesson(self.course, module["id"], "Сломать", "Текст", "", heavy[0]["id"])

	def test_move_and_publish_rules(self):
		frappe.set_user(TEACHER)
		data = studio.studio_course(self.course)
		first, second = data["modules"][0]["id"], data["modules"][1]["id"]
		moved = studio.move_item(self.course, "module", second, "up")
		self.assertEqual(moved["modules"][0]["id"], second)
		studio.move_item(self.course, "module", second, "down")
		self.assertEqual(studio.studio_course(self.course)["modules"][0]["id"], first)
		with self.assertRaises(frappe.ValidationError):
			studio.move_item(self.course, "module", first, "sideways")
		self.assertTrue(studio.set_published(self.course, 1)["published"])
