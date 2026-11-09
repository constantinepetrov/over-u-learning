"""Personal goals (2 main + 1 extra), the daily report and the buddy widget.

Everything is scoped to the signed-in session: the browser never supplies a member.
Goals and reports are private to their author and to instructors of the author's
courses. A buddy sees a goal only when its author switched "show to my buddy" on.
Points for a daily report come from the editable rule "daily_report" (seeded switched
off with zero points until the author sets the scale) and are paid once per day.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today

from over_u import points
from over_u.profile_api import profile_of
from over_u.student_api import _member

KINDS = {"Основная": 2, "Дополнительная": 1}
MAX_STEPS = 20
MAX_TITLE = 140
MAX_NOTE = 3000
REPORT_FIELDS = ("goals_done", "insights", "tasks_done", "suggestions")
MIN_REPORT_CHARS = 20


def percent(steps):
	"""Share of finished plan steps; a goal without a plan counts as 0."""
	total = len(steps)
	return round(sum(1 for step in steps if step.get("done")) / total * 100) if total else 0


def overall(goals):
	"""Plain average of the goals' percentages, so every goal weighs the same."""
	return round(sum(goal["percent"] for goal in goals) / len(goals)) if goals else 0


def _goal(doc):
	steps = [
		{
			"title": step.title,
			"due": str(step.due) if step.due else "",
			"done": bool(step.done),
		}
		for step in doc.steps
	]
	return {
		"id": doc.name,
		"kind": doc.kind,
		"title": doc.title,
		"details": doc.details or "",
		"target_date": str(doc.target_date) if doc.target_date else "",
		"shared": bool(doc.shared),
		"steps": steps,
		"percent": percent(steps),
	}


def goals_of(member, only_shared=False):
	filters = {"member": member}
	if only_shared:
		filters["shared"] = 1
	names = frappe.get_all("OU Goal", filters, pluck="name", order_by="creation asc", limit_page_length=0)
	docs = [frappe.get_doc("OU Goal", name) for name in names]
	docs.sort(key=lambda doc: (doc.kind != "Основная", str(doc.creation)))
	return [_goal(doc) for doc in docs]


def _buddy(me):
	"""The partner from my "Бадди" pair: only what they chose to share."""
	rows = frappe.get_all(
		"OU Group Member",
		{"member": me, "parenttype": "OU Group"},
		pluck="parent",
		limit_page_length=0,
	)
	for name in rows:
		group = frappe.db.get_value("OU Group", name, ["kind", "title"], as_dict=True)
		if not group or group.kind != "Бадди":
			continue
		others = [m for m in frappe.get_all("OU Group Member", {"parent": name}, pluck="member") if m != me]
		if not others:
			continue
		partner = others[0]
		shared = goals_of(partner, only_shared=True)
		return {
			"name": points.short_name(partner),
			"title": group.title,
			"points": points.total_for(partner) if points.setting("leaderboard_enabled", 1) else None,
			"goals": shared,
			"percent": overall(shared),
			"hidden": frappe.db.count("OU Goal", {"member": partner, "shared": 0}),
			"profile": profile_of(partner, only_shared=True),
		}
	return None


@frappe.whitelist()
def my_goals():
	me = _member()
	goals = goals_of(me)
	return {
		"goals": goals,
		"percent": overall(goals),
		"limits": KINDS,
		"points": points.total_for(me) if points.setting("leaderboard_enabled", 1) else None,
		"buddy": _buddy(me),
	}


def _own(goal, me):
	if not isinstance(goal, str) or not goal:
		frappe.throw(_("Goal not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc("OU Goal", goal) if frappe.db.exists("OU Goal", goal) else None
	if not doc or doc.member != me:
		frappe.throw(_("Goal not found."), frappe.DoesNotExistError)
	return doc


def _clean_steps(steps):
	if not isinstance(steps, list) or len(steps) > MAX_STEPS:
		frappe.throw(_("A plan can have up to 20 steps."))
	clean = []
	for step in steps:
		if not isinstance(step, dict):
			continue
		title = str(step.get("title") or "").strip()
		if not title:
			continue
		if len(title) > MAX_TITLE:
			frappe.throw(_("A step is too long."))
		due = str(step.get("due") or "").strip()
		try:
			due = str(getdate(due)) if due else None
		except Exception:
			frappe.throw(_("Check the date of the step."))
		clean.append({"title": title, "due": due, "done": 1 if step.get("done") else 0})
	return clean


@frappe.whitelist(methods=["POST"])
def save_goal(
	kind: str,
	title: str,
	steps: list,
	goal: str = "",
	details: str = "",
	target_date: str = "",
	shared: int = 0,
):
	me = _member()
	if kind not in KINDS:
		frappe.throw(_("Choose the kind of goal."))
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE:
		frappe.throw(_("Write the goal in up to 140 characters."))
	if not isinstance(details, str) or len(details) > MAX_NOTE:
		frappe.throw(_("The description is too long."))
	try:
		target = str(getdate(target_date)) if target_date else None
	except Exception:
		frappe.throw(_("Check the target date."))
	clean = _clean_steps(steps)
	values = {
		"kind": kind,
		"title": title.strip(),
		"details": details.strip(),
		"target_date": target,
		"shared": 1 if int(shared or 0) else 0,
	}
	if goal:
		doc = _own(goal, me)
		taken = frappe.db.count("OU Goal", {"member": me, "kind": kind, "name": ["!=", doc.name]})
		if taken >= KINDS[kind]:
			frappe.throw(_("This kind of goal is already full."))
		_log_changes(doc, values, clean)
		doc.update(values)
		doc.set("steps", clean)
		# nosemgrep: lms-unjustified-ignore-permissions - the goal belongs to the verified session user; learners have no DocPerm on the doctype
		doc.save(ignore_permissions=True)
	else:
		if frappe.db.count("OU Goal", {"member": me, "kind": kind}) >= KINDS[kind]:
			frappe.throw(_("This kind of goal is already full."))
		# nosemgrep: lms-unjustified-ignore-permissions - the goal belongs to the verified session user; learners have no DocPerm on the doctype
		frappe.get_doc({"doctype": "OU Goal", "member": me, "steps": clean, **values}).insert(
			ignore_permissions=True
		)
	return my_goals()


HISTORY_LABELS = {
	"title": "Название",
	"details": "Описание",
	"target_date": "Срок",
	"shared": "Показ бадди",
	"kind": "Тип цели",
}


@frappe.whitelist()
def goal_history(goal: str):
	"""What the author changed in the goal and when, newest first. Only the author sees it."""
	doc = _own(goal, _member())
	rows = frappe.get_all(
		"OU Goal Log",
		{"goal": doc.name},
		["creation", "summary"],
		order_by="creation desc",
		limit_page_length=30,
	)
	return {"history": [{"when": str(r.creation), "changes": r.summary.split(", ")} for r in rows]}


def _log_changes(doc, values, clean):
	"""Record which parts of the goal were edited (a title change, a new plan, a new date...)."""
	changed = [
		label
		for field, label in HISTORY_LABELS.items()
		if str(doc.get(field) or "") != str(values.get(field) or "")
	]
	before = [(s.title, str(s.due or ""), int(s.done or 0)) for s in doc.steps]
	after = [(s["title"], str(s["due"] or ""), int(s["done"])) for s in clean]
	if [x[:2] for x in before] != [x[:2] for x in after]:
		changed.append("План")
	if changed:
		# nosemgrep: lms-unjustified-ignore-permissions - the log belongs to the verified session user; learners have no DocPerm on the doctype
		frappe.get_doc(
			{"doctype": "OU Goal Log", "goal": doc.name, "member": doc.member, "summary": ", ".join(changed)}
		).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def set_step(goal: str, index: int, done: int):
	me = _member()
	doc = _own(goal, me)
	index = int(index)
	if index < 0 or index >= len(doc.steps):
		frappe.throw(_("Step not found."), frappe.DoesNotExistError)
	doc.steps[index].done = 1 if int(done) else 0
	# nosemgrep: lms-unjustified-ignore-permissions - the goal belongs to the verified session user; learners have no DocPerm on the doctype
	doc.save(ignore_permissions=True)
	return my_goals()


@frappe.whitelist(methods=["POST"])
def delete_goal(goal: str):
	me = _member()
	doc = _own(goal, me)
	# nosemgrep: lms-unjustified-ignore-permissions - the goal belongs to the verified session user; learners have no DocPerm on the doctype
	frappe.delete_doc("OU Goal", doc.name, ignore_permissions=True, force=True)
	return my_goals()


# ---- daily report -----------------------------------------------------------


def _report(row):
	return {
		"date": str(row.report_date),
		**{field: row.get(field) or "" for field in REPORT_FIELDS},
	}


def reports_of(member, limit=14):
	return [
		_report(row)
		for row in frappe.get_all(
			"OU Daily Report",
			{"member": member},
			["report_date", *REPORT_FIELDS],
			order_by="report_date desc",
			limit_page_length=limit,
		)
	]


@frappe.whitelist()
def my_report():
	me = _member()
	history = reports_of(me)
	current = next((row for row in history if row["date"] == today()), None)
	return {
		"today": today(),
		"report": current,
		"history": [row for row in history if row["date"] != today()],
		"rule": frappe.db.get_value("OU Points Rule", "daily_report", ["points", "enabled"], as_dict=True)
		or {"points": 0, "enabled": 0},
	}


@frappe.whitelist(methods=["POST"])
def save_report(goals_done: str = "", insights: str = "", tasks_done: str = "", suggestions: str = ""):
	me = _member()
	values = {
		"goals_done": goals_done,
		"insights": insights,
		"tasks_done": tasks_done,
		"suggestions": suggestions,
	}
	for text in values.values():
		if not isinstance(text, str) or len(text) > MAX_NOTE:
			frappe.throw(_("A field is too long."))
	values = {name: text.strip() for name, text in values.items()}
	# A report with almost nothing in it is not a report: no record, no points.
	body = "".join(values[name] for name in ("goals_done", "insights", "tasks_done"))
	if len(body) < MIN_REPORT_CHARS:
		frappe.throw(_("Tell a little more about the day."))
	day = today()
	key = f"{me}:{day}"
	existing = frappe.db.get_value("OU Daily Report", {"key": key}, "name")
	if existing:
		doc = frappe.get_doc("OU Daily Report", existing)
		doc.update(values)
		# nosemgrep: lms-unjustified-ignore-permissions - the report belongs to the verified session user; learners have no DocPerm on the doctype
		doc.save(ignore_permissions=True)
	else:
		course = frappe.db.get_value("LMS Enrollment", {"member": me}, "course", order_by="creation desc")
		try:
			# nosemgrep: lms-unjustified-ignore-permissions - the report belongs to the verified session user; learners have no DocPerm on the doctype
			frappe.get_doc(
				{
					"doctype": "OU Daily Report",
					"member": me,
					"course": course,
					"report_date": day,
					"key": key,
					**values,
				}
			).insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Today's report is already saved. Open it to edit."))
		points.award(me, "daily_report", f"dr:{me}:{day}", course)
	return my_report()
