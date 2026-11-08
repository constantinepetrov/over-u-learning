import frappe

from lms.lms.test_helpers import BaseTestUtils
from over_u import discussion_api as disc
from over_u import goals_api as goals
from over_u import points
from over_u.school import TEACHER, manifest

STEPS = [
	{"title": "Записать план", "due": "2026-12-01", "done": 1},
	{"title": "Сделать первую практику", "due": "2026-12-05", "done": 0},
]


class TestGoals(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		points.seed_rules()
		self.course = manifest()["course"]
		self.alice = self._create_user(
			"over-u-goal-alice@example.com", "Алиса", "Иванова", ["LMS Student"]
		).name
		self.bob = self._create_user("over-u-goal-bob@example.com", "Борис", "Петров", ["LMS Student"]).name
		self.stranger = self._create_user(
			"over-u-goal-stranger@example.com", "Чужой", "Тест", ["LMS Student"]
		).name
		for user in (self.alice, self.bob):
			frappe.get_doc({"doctype": "LMS Enrollment", "course": self.course, "member": user}).insert()
		self.pair = frappe.get_doc(
			{
				"doctype": "OU Group",
				"title": "Пара целей",
				"kind": "Бадди",
				"members": [{"member": self.alice}, {"member": self.bob}],
			}
		).insert()
		frappe.set_user(self.alice)

	def tearDown(self):
		frappe.set_user("Administrator")
		self.pair.delete()
		for doctype in ("OU Goal Log", "OU Goal", "OU Daily Report", "OU Points Entry"):
			frappe.db.delete(doctype, {"member": ["in", [self.alice, self.bob, self.stranger]]})
		super().tearDown()

	def test_limits_and_percent_are_transparent(self):
		data = goals.save_goal("Основная", "Вставать в 6 утра", STEPS)
		self.assertEqual(data["goals"][0]["percent"], 50)
		self.assertEqual(data["percent"], 50)
		goals.save_goal("Основная", "Гулять каждый день", [])
		with self.assertRaises(frappe.ValidationError):
			goals.save_goal("Основная", "Третья основная", [])
		goals.save_goal("Дополнительная", "Читать 10 страниц", [{"title": "Выбрать книгу", "done": 1}])
		with self.assertRaises(frappe.ValidationError):
			goals.save_goal("Дополнительная", "Вторая дополнительная", [])
		with self.assertRaises(frappe.ValidationError):
			goals.save_goal("Другая", "Неизвестный вид", [])
		with self.assertRaises(frappe.ValidationError):
			goals.save_goal("Дополнительная", "Плохой срок", [{"title": "Шаг", "due": "не дата"}])
		# No plan counts as 0; the overall figure is the plain average of the three goals.
		self.assertEqual(goals.my_goals()["percent"], round((50 + 0 + 100) / 3))
		goal = goals.my_goals()["goals"][0]["id"]
		goals.set_step(goal, 1, 1)
		self.assertEqual(goals.my_goals()["goals"][0]["percent"], 100)

	def test_buddy_sees_only_shared_goals_and_strangers_see_nothing(self):
		goals.save_goal("Основная", "Открытая цель", STEPS, shared=1)
		goals.save_goal("Основная", "Закрытая цель", STEPS)
		frappe.set_user(self.bob)
		buddy = goals.my_goals()["buddy"]
		self.assertEqual([g["title"] for g in buddy["goals"]], ["Открытая цель"])
		self.assertEqual(buddy["hidden"], 1)
		self.assertEqual(buddy["name"], "Алиса И.")
		self.assertNotIn("@", str(buddy))
		self.assertEqual(goals.my_goals()["goals"], [])
		frappe.set_user(self.stranger)
		self.assertIsNone(goals.my_goals()["buddy"])
		self.assertEqual(goals.my_goals()["goals"], [])

	def test_nobody_edits_someone_elses_goal(self):
		goal = goals.save_goal("Основная", "Моя цель", STEPS)["goals"][0]["id"]
		frappe.set_user(self.bob)
		for call in (
			lambda: goals.set_step(goal, 0, 0),
			lambda: goals.delete_goal(goal),
			lambda: goals.save_goal("Основная", "Подмена", [], goal),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				call()
		self.assertTrue(frappe.db.exists("OU Goal", goal))
		frappe.set_user(self.alice)
		goals.delete_goal(goal)
		self.assertFalse(frappe.db.exists("OU Goal", goal))

	def test_daily_report_pays_once_and_only_after_the_author_sets_a_scale(self):
		text = "Сегодня сделала зарядку и записала план на неделю."
		self.assertEqual(frappe.db.get_value("OU Points Rule", "daily_report", "enabled"), 0)
		before = points.total_for(self.alice)
		goals.save_report(goals_done=text)
		self.assertEqual(points.total_for(self.alice), before)
		frappe.db.set_value("OU Points Rule", "daily_report", {"points": 4, "enabled": 1})
		frappe.db.delete("OU Daily Report", {"member": self.alice})
		goals.save_report(goals_done=text)
		self.assertEqual(points.total_for(self.alice), before + 4)
		data = goals.save_report(goals_done=text + " Ещё поправила.", insights="Лучше утром")
		self.assertEqual(points.total_for(self.alice), before + 4)
		self.assertEqual(frappe.db.count("OU Daily Report", {"member": self.alice}), 1)
		self.assertIn("Ещё поправила", data["report"]["goals_done"])
		with self.assertRaises(frappe.ValidationError):
			frappe.set_user(self.bob)
			goals.save_report(goals_done="мало")

	def test_instructor_sees_goals_and_reports_only_of_own_courses(self):
		goals.save_goal("Основная", "Цель Алисы", STEPS)
		goals.save_report(goals_done="Сегодня выполнила первый шаг плана и сделала запись.")
		frappe.set_user(TEACHER)
		card = disc.teacher_student(self.alice)
		self.assertEqual(card["goals"][0]["title"], "Цель Алисы")
		self.assertEqual(card["goals_percent"], 50)
		self.assertEqual(len(card["reports"]), 1)
		self.assertGreaterEqual(disc.teacher_desk()["counters"]["reports_today"], 1)
		frappe.set_user(self.stranger)
		with self.assertRaises(frappe.PermissionError):
			disc.teacher_student(self.alice)

	def test_goal_history_records_changes_for_the_author_only(self):
		goal = goals.save_goal("Основная", "Первая версия", STEPS)["goals"][0]["id"]
		goals.save_goal("Основная", "Вторая версия", STEPS + [{"title": "Новый шаг"}], goal=goal)
		history = goals.goal_history(goal)["history"]
		self.assertTrue(history)
		self.assertIn("Название", history[0]["changes"])
		self.assertIn("План", history[0]["changes"])
		frappe.set_user(self.bob)
		with self.assertRaises(frappe.DoesNotExistError):
			goals.goal_history(goal)
