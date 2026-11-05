"""Points and rating. All rules live in the "OU Points Rule" list, which the author edits in Desk.

Awarding never raises: a points problem must not break grading, quizzes or progress.
Every automatic entry carries a unique key, so repeating an event never pays twice.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

# event, label, points, daily limit (0 = unlimited). Seeded once; the author changes values freely.
DEFAULT_RULES = (
	("lesson_complete", "Урок пройден", 1, 0),
	("quiz_passed", "Тест сдан", 5, 0),
	("assignment_submitted", "Задание отправлено", 3, 0),
	("assignment_pass", "Задание зачтено", 10, 0),
	("comment_posted", "Сообщение в ленте ответов", 1, 5),
	("reaction_received", "Ваш ответ или сообщение оценили", 1, 10),
)
# Rules the author has not priced yet: seeded switched off with zero points, so nothing is
# paid until the author sets the scale in Desk.
PENDING_RULES = (
	("daily_report", "Ежедневный отчёт", 1),
	("super_post", "Сообщение в «СУПЕР»", 3),
	("mastermind_attended", "Участие в мастермайнде", 0),
)
STAFF_ROLES = {"Course Creator", "Moderator", "Batch Evaluator", "System Manager"}


def seed_rules():
	for event, label, points, daily_limit in DEFAULT_RULES:
		try:
			# nosemgrep: lms-unjustified-ignore-permissions - one-time system seed of default rules
			frappe.get_doc(
				{
					"doctype": "OU Points Rule",
					"event": event,
					"label": label,
					"points": points,
					"enabled": 1,
					"daily_limit": daily_limit,
				}
			).insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			pass  # already seeded; the author's edits are never overwritten
	for event, label, daily_limit in PENDING_RULES:
		if frappe.db.exists("OU Points Rule", event):
			continue
		try:
			# nosemgrep: lms-unjustified-ignore-permissions - one-time system seed of default rules
			frappe.get_doc(
				{
					"doctype": "OU Points Rule",
					"event": event,
					"label": label,
					"points": 0,
					"enabled": 0,
					"daily_limit": daily_limit,
				}
			).insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			pass


def setting(field, default=None):
	value = frappe.db.get_single_value("OU Settings", field)
	return default if value is None else value


def award(member, event, key, course=None, reason=None):
	if not member or not setting("leaderboard_enabled", 1):
		return
	try:
		rule = frappe.db.get_value(
			"OU Points Rule", event, ["points", "enabled", "daily_limit", "label"], as_dict=True
		)
		if not rule or not rule.enabled or not rule.points:
			return
		if frappe.db.exists("OU Points Entry", {"key": key}):
			return
		if rule.daily_limit:
			since = now_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
			spent = frappe.db.count(
				"OU Points Entry", {"member": member, "event": event, "creation": [">=", since]}
			)
			if spent >= rule.daily_limit:
				return
		# nosemgrep: lms-unjustified-ignore-permissions - points are system-awarded after server-side rules; learners have no DocPerm on OU Points Entry
		frappe.get_doc(
			{
				"doctype": "OU Points Entry",
				"member": member,
				"points": rule.points,
				"event": event,
				"reason": reason or rule.label,
				"course": course,
				"key": key,
				"awarded_by": "Administrator",
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="OVER U points: award failed")


def revoke(key):
	try:
		frappe.db.delete("OU Points Entry", {"key": key})
	except Exception:
		frappe.log_error(title="OVER U points: revoke failed")


# ---- document hooks -------------------------------------------------------


def on_submission_insert(doc, method=None):
	award(doc.member, "assignment_submitted", f"as:{doc.assignment}:{doc.member}", doc.course)


def on_submission_update(doc, method=None):
	previous = doc.get_doc_before_save()
	was = previous.status if previous else None
	key = f"ap:{doc.assignment}:{doc.member}"
	if doc.status == "Pass" and was != "Pass":
		award(doc.member, "assignment_pass", key, doc.course)
	elif was == "Pass" and doc.status != "Pass":
		revoke(key)


def on_quiz_submission(doc, method=None):
	if (doc.get("percentage") or 0) >= (doc.get("passing_percentage") or 0):
		course = doc.get("course") or frappe.db.get_value("LMS Quiz", doc.quiz, "course")
		award(doc.member, "quiz_passed", f"qp:{doc.quiz}:{doc.member}", course)


def on_progress(doc, method=None):
	if doc.status == "Complete" and doc.lesson:
		award(doc.member, "lesson_complete", f"lc:{doc.lesson}:{doc.member}", doc.get("course"))


# ---- reading ----------------------------------------------------------------


def is_staff(user):
	return bool(set(frappe.get_roles(user)) & STAFF_ROLES)


def short_name(user):
	first, last = frappe.db.get_value("User", user, ["first_name", "last_name"]) or (user, "")
	return f"{first} {last[:1]}.".strip() if last else (first or user)


def _enrolled(course):
	members = frappe.get_all("LMS Enrollment", {"course": course}, pluck="member", limit_page_length=0)
	return [m for m in dict.fromkeys(members) if not is_staff(m)]


def _sums(members, since=None):
	if not members:
		return {}
	conditions, values = ["member in %(members)s"], {"members": tuple(members)}
	if since:
		conditions.append("creation >= %(since)s")
		values["since"] = since
	rows = frappe.db.sql(
		"select member, sum(points) from `tabOU Points Entry` where "
		+ " and ".join(conditions)
		+ " group by member",
		values,
	)
	return {member: int(total or 0) for member, total in rows}


def _rank(sorted_rows, key):
	"""Standard competition ranking: equal scores share a place."""
	places, last, place = {}, None, 0
	for index, row in enumerate(sorted_rows, 1):
		if row[key] != last:
			place, last = index, row[key]
		places[id(row)] = place
	return places


def total_for(member):
	return int(
		frappe.db.sql("select coalesce(sum(points), 0) from `tabOU Points Entry` where member = %s", member)[
			0
		][0]
	)


def leaderboard(course, member, period="all"):
	if not setting("leaderboard_enabled", 1):
		return {"enabled": False}
	since = add_days(now_datetime(), -7) if period == "week" else None
	members = _enrolled(course)
	if member not in members:
		members.append(member)
	sums = _sums(members, since)
	rows = sorted(
		({"user": m, "points": sums.get(m, 0)} for m in members),
		key=lambda r: (-r["points"], short_name(r["user"])),
	)
	places = _rank(rows, "points")
	for row in rows:
		row["rank"] = places[id(row)]
	mine = next(r for r in rows if r["user"] == member)
	everyone = (
		setting("leaderboard_visibility", "Все ученики видят табло") != "Ученик видит только свой результат"
	)
	limit = max(3, int(setting("leaderboard_limit", 10) or 10))
	top = [
		{"name": short_name(r["user"]), "points": r["points"], "rank": r["rank"], "me": r["user"] == member}
		for r in rows[:limit]
	]
	if everyone and mine["rank"] > top[-1]["rank"] and not any(t["me"] for t in top):
		top.append({"name": short_name(member), "points": mine["points"], "rank": mine["rank"], "me": True})
	groups = []
	for name in frappe.get_all("OU Group", pluck="name", limit_page_length=0):
		group = frappe.get_doc("OU Group", name)
		people = [row.member for row in group.members]
		if group.course and group.course != course:
			continue
		if not group.course and not set(people) & set(members):
			continue
		groups.append(
			{
				"title": group.title,
				"kind": group.kind,
				"points": sum(sums.get(m, 0) for m in people),
				"members": [short_name(m) for m in people],
				"mine": member in people,
			}
		)
	for kind in ("Бадди", "Команда"):
		subset = sorted((g for g in groups if g["kind"] == kind), key=lambda g: -g["points"])
		places = _rank(subset, "points")
		for g in subset:
			g["rank"] = places[id(g)]
	if not everyone:
		top = [t for t in top if t["me"]]
		groups = [g for g in groups if g["mine"]]
	recent = frappe.get_all(
		"OU Points Entry",
		{"member": member},
		["points", "reason", "creation"],
		order_by="creation desc",
		limit_page_length=15,
	)
	return {
		"enabled": True,
		"period": period,
		"everyone": everyone,
		"prizes": setting("prizes", "") or "",
		"me": {"points": mine["points"], "rank": mine["rank"], "of": len(rows), "total": total_for(member)},
		"top": top,
		"groups": sorted(groups, key=lambda g: (g["kind"], g["rank"])),
		"recent": [{"points": r.points, "reason": r.reason or "", "when": str(r.creation)} for r in recent],
		"rules": [
			{"label": r.label, "points": r.points, "daily_limit": r.daily_limit}
			for r in frappe.get_all(
				"OU Points Rule",
				{"enabled": 1, "points": [">", 0]},
				["label", "points", "daily_limit"],
				order_by="points desc",
			)
		],
	}


@frappe.whitelist(methods=["POST"])
def award_bonus(member: str, points: int, reason: str, course: str = ""):
	"""Instructor bonus from a custom button or script; Desk can also create entries by hand."""
	if not is_staff(frappe.session.user):
		frappe.throw(_("Only instructors can award bonus points."), frappe.PermissionError)
	points = int(points)
	if not points or not isinstance(reason, str) or not reason.strip():
		frappe.throw(_("Enter the points and the reason."))
	# nosemgrep: lms-unjustified-ignore-permissions - points are system-awarded after server-side rules; learners have no DocPerm on OU Points Entry
	doc = frappe.get_doc(
		{
			"doctype": "OU Points Entry",
			"member": member,
			"points": points,
			"reason": reason.strip()[:140],
			"course": course or None,
			"event": "bonus",
		}
	).insert(ignore_permissions=True)
	return doc.name
