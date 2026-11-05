"""Instructor tools: pairs and teams, points settings with a dry run, bonus and prizes.

Everything is checked on the server against the courses the caller may author. Rule
changes are never retroactive: they apply to events from the moment they are saved.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from over_u import points
from over_u.discussion_api import _staff_course
from over_u.student_api import _member, review_courses

MAX_TEAM = 12


def _name(user):
	return frappe.db.get_value("User", user, "full_name") or user


# ---- pairs and teams ---------------------------------------------------------


def _group(doc):
	return {
		"id": doc.name,
		"title": doc.title,
		"kind": doc.kind,
		"course": doc.course,
		"members": [{"member": row.member, "name": _name(row.member)} for row in doc.members],
	}


@frappe.whitelist()
def teacher_groups(course: str = ""):
	courses = review_courses(_member())
	if course:
		if course not in courses:
			frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
		courses = [course]
	titles = {
		row.name: row.title
		for row in frappe.get_all(
			"LMS Course", {"name": ["in", courses]}, ["name", "title"], limit_page_length=0
		)
	}
	groups = [
		_group(frappe.get_doc("OU Group", name))
		for name in frappe.get_all(
			"OU Group",
			{"course": ["in", courses]} if courses else {"name": ""},
			pluck="name",
			order_by="creation asc",
			limit_page_length=0,
		)
	]
	return {
		"courses": [
			{
				"id": name,
				"title": titles.get(name, name),
				"participants": [{"member": m, "name": _name(m)} for m in points._enrolled(name)],
			}
			for name in courses
		],
		"groups": groups,
	}


@frappe.whitelist(methods=["POST"])
def save_group(course: str, kind: str, title: str, members: list, group: str = ""):
	_staff_course(course)
	if kind not in ("Бадди", "Команда"):
		frappe.throw(_("Choose pair or team."))
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > 100:
		frappe.throw(_("Write a title of up to 100 characters."))
	if not isinstance(members, list):
		frappe.throw(_("Choose the participants."))
	people = list(dict.fromkeys(m for m in members if isinstance(m, str)))
	allowed = set(points._enrolled(course))
	if any(m not in allowed for m in people):
		frappe.throw(_("Only participants of this course can be added."))
	if kind == "Бадди" and len(people) != 2:
		frappe.throw(_("A pair has exactly two people."))
	if kind == "Команда" and not 2 <= len(people) <= MAX_TEAM:
		frappe.throw(_("A team has from 2 to 12 people."))
	# One buddy pair per person per course; teams may overlap with pairs, not with each other.
	for other in frappe.get_all(
		"OU Group", {"course": course, "kind": kind, "name": ["!=", group or ""]}, pluck="name"
	):
		busy = set(frappe.get_all("OU Group Member", {"parent": other}, pluck="member")) & set(people)
		if busy:
			frappe.throw(_("{0} is already in another {1}.").format(_name(sorted(busy)[0]), kind))
	rows = [{"member": m} for m in people]
	if group:
		doc = frappe.get_doc("OU Group", group) if frappe.db.exists("OU Group", group) else None
		if not doc or doc.course != course:
			frappe.throw(_("Group not found."), frappe.DoesNotExistError)
		doc.update({"title": title.strip(), "kind": kind})
		doc.set("members", rows)
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		frappe.get_doc(
			{"doctype": "OU Group", "course": course, "kind": kind, "title": title.strip(), "members": rows}
		).insert(ignore_permissions=True)
	return teacher_groups()


@frappe.whitelist(methods=["POST"])
def delete_group(group: str):
	doc = (
		frappe.get_doc("OU Group", group)
		if isinstance(group, str) and frappe.db.exists("OU Group", group)
		else None
	)
	if not doc or not doc.course:
		frappe.throw(_("Group not found."), frappe.DoesNotExistError)
	_staff_course(doc.course)
	# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
	frappe.delete_doc("OU Group", doc.name, ignore_permissions=True, force=True)
	return teacher_groups()


# ---- points settings ---------------------------------------------------------


def _staff():
	me = _member()
	if not points.is_staff(me) or not review_courses(me):
		frappe.throw(_("Only instructors can change points."), frappe.PermissionError)
	return me


def _settings():
	since = add_days(now_datetime(), -30)
	counts = dict(
		frappe.db.sql(
			"select event, count(*) from `tabOU Points Entry` where creation >= %s group by event", since
		)
	)
	rules = [
		{
			"event": r.name,
			"label": r.label,
			"points": r.points,
			"enabled": bool(r.enabled),
			"daily_limit": r.daily_limit or 0,
			"last30": int(counts.get(r.name, 0)),
		}
		for r in frappe.get_all(
			"OU Points Rule",
			["name", "label", "points", "enabled", "daily_limit"],
			order_by="creation asc",
			limit_page_length=0,
		)
	]
	courses = review_courses(_member())
	journal = frappe.get_all(
		"OU Points Entry",
		{"course": ["in", courses]} if courses else {"name": ""},
		["member", "points", "reason", "event", "creation", "awarded_by"],
		order_by="creation desc",
		limit_page_length=30,
	)
	return {
		"rules": rules,
		"board": {
			"enabled": bool(points.setting("leaderboard_enabled", 1)),
			"visibility": points.setting("leaderboard_visibility", "Все ученики видят табло"),
			"limit": int(points.setting("leaderboard_limit", 10) or 10),
		},
		"prizes": points.setting("prizes", "") or "",
		"journal": [
			{
				"name": points.short_name(row.member),
				"points": row.points,
				"reason": row.reason or "",
				"event": row.event or "",
				"when": str(row.creation),
			}
			for row in journal
		],
		"participants": [
			{"member": m, "name": _name(m), "course": c} for c in courses for m in points._enrolled(c)
		],
	}


@frappe.whitelist()
def points_settings():
	_staff()
	return _settings()


def _rule(event):
	if not isinstance(event, str) or not frappe.db.exists("OU Points Rule", event):
		frappe.throw(_("Rule not found."), frappe.DoesNotExistError)
	return event


@frappe.whitelist()
def preview_rule(event: str, points_value: int, enabled: int = 1):
	"""Dry run: what the change would have meant for the last 30 days. Nothing is saved."""
	_staff()
	_rule(event)
	new = max(0, int(points_value)) if int(enabled) else 0
	row = frappe.db.get_value("OU Points Rule", event, ["points", "enabled"], as_dict=True)
	old = row.points if row.enabled else 0
	count = frappe.db.count(
		"OU Points Entry", {"event": event, "creation": [">=", add_days(now_datetime(), -30)]}
	)
	return {"events": count, "old": old, "new": new, "delta": count * (new - old), "retroactive": False}


@frappe.whitelist(methods=["POST"])
def save_rule(event: str, points_value: int, enabled: int, daily_limit: int = 0):
	_staff()
	_rule(event)
	value, limit = int(points_value), int(daily_limit or 0)
	if not 0 <= value <= 1000 or not 0 <= limit <= 100:
		frappe.throw(_("Points must be 0-1000 and the daily limit 0-100."))
	frappe.db.set_value(
		"OU Points Rule", event, {"points": value, "enabled": 1 if int(enabled) else 0, "daily_limit": limit}
	)
	return _settings()


@frappe.whitelist(methods=["POST"])
def save_board(enabled: int, visibility: str, limit: int, prizes: str = ""):
	_staff()
	if visibility not in ("Все ученики видят табло", "Ученик видит только свой результат"):
		frappe.throw(_("Choose who sees the board."))
	if not isinstance(prizes, str) or len(prizes) > 3000:
		frappe.throw(_("The text is too long."))
	frappe.db.set_single_value(
		"OU Settings",
		{
			"leaderboard_enabled": 1 if int(enabled) else 0,
			"leaderboard_visibility": visibility,
			"leaderboard_limit": max(3, min(50, int(limit))),
			"prizes": prizes.strip(),
		},
	)
	return _settings()


@frappe.whitelist(methods=["POST"])
def give_bonus(member: str, course: str, value: int, reason: str):
	_staff()
	_staff_course(course)
	if member not in points._enrolled(course):
		frappe.throw(_("Only participants of this course can receive points."))
	if not 1 <= int(value) <= 1000:
		frappe.throw(_("Bonus is from 1 to 1000 points."))
	points.award_bonus(member, int(value), reason, course)
	return _settings()
