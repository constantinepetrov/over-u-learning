"""The «СУПЕР» wall and mastermind meetings.

Both follow the course author's materials and nothing more: a mastermind has a date and
time, a list of topics and points for taking part; «СУПЕР» is a feed of short messages
about what went especially well. Points come from editable rules that are seeded switched
off with zero points, so nothing is paid until the author sets the scale.

Everything is scoped to the signed-in session. Participants see only the courses they are
enrolled in; instructors manage only the courses they may author. Attendance is marked by
an instructor, never claimed by the participant.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, get_system_timezone, now_datetime

from over_u import points
from over_u.discussion_api import _can_moderate, _staff_course
from over_u.student_api import _access, _member, review_courses

MAX_POST = 300
HOURLY_LIMIT = 20
MAX_TOPICS = 15
MAX_NOTE = 5000


def _course(course):
	"""The course a participant works in: the one asked for, else the newest enrolment."""
	me = _member()
	if not course:
		course = frappe.db.get_value("LMS Enrollment", {"member": me}, "course", order_by="creation desc")
		if not course:
			frappe.throw(_("This course is unavailable for your account."), frappe.PermissionError)
	_access(course)
	return course


# ---- СУПЕР -------------------------------------------------------------------


def _super(course):
	me = _member()
	moderator = _can_moderate(course, me)
	filters = {"course": course}
	if not moderator:
		filters["hidden"] = 0
	rows = frappe.get_all(
		"OU Super Post",
		filters,
		["name", "member", "text", "hidden", "creation"],
		order_by="creation desc",
		limit_page_length=100,
	)
	posts = []
	for row in rows:
		name = points.short_name(row.member)
		posts.append(
			{
				"id": row.name,
				"author": name,
				"initial": name[:1].upper(),
				"mine": row.member == me,
				"when": str(row.creation),
				"text": row.text or "",
				"hidden": bool(row.hidden),
				"can_delete": bool(moderator or row.member == me),
			}
		)
	return {
		"course": course,
		"posts": posts,
		"can_moderate": moderator,
		"rule": frappe.db.get_value("OU Points Rule", "super_post", ["points", "enabled"], as_dict=True)
		or {"points": 0, "enabled": 0},
	}


def _super_course(course):
	me = _member()
	if course and _can_moderate(course, me):
		return course
	return _course(course)


@frappe.whitelist()
def super_feed(course: str = ""):
	return _super(_super_course(course))


@frappe.whitelist(methods=["POST"])
def post_super(text: str, course: str = ""):
	course = _course(course)
	me = _member()
	if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_POST:
		frappe.throw(_("Write a short message of up to 300 characters."))
	recent = frappe.db.count(
		"OU Super Post",
		{"member": me, "creation": [">=", frappe.utils.add_to_date(None, hours=-1)]},
	)
	if recent >= HOURLY_LIMIT:
		frappe.throw(_("Too many messages. Please try again a little later."))
	# nosemgrep: lms-unjustified-ignore-permissions - posts are written for the verified session user after enrolment checks; learners have no DocPerm on the doctype
	doc = frappe.get_doc(
		{"doctype": "OU Super Post", "course": course, "member": me, "text": text.strip()}
	).insert(ignore_permissions=True)
	points.award(me, "super_post", f"sp:{doc.name}", course)
	return _super(course)


@frappe.whitelist(methods=["POST"])
def moderate_super(post: str, action: str):
	me = _member()
	row = frappe.db.get_value("OU Super Post", post, ["name", "course", "member"], as_dict=True)
	if not row:
		frappe.throw(_("Message not found."), frappe.DoesNotExistError)
	moderator = _can_moderate(row.course, me)
	if action not in ("hide", "unhide", "delete"):
		frappe.throw(_("Unknown action."))
	if action == "delete":
		if not (moderator or row.member == me):
			frappe.throw(_("You cannot delete this message."), frappe.PermissionError)
		points.revoke(f"sp:{row.name}")
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is the author or an instructor of this course
		frappe.delete_doc("OU Super Post", row.name, ignore_permissions=True, force=True)
	else:
		if not moderator:
			frappe.throw(_("Only instructors can moderate the feed."), frappe.PermissionError)
		frappe.db.set_value("OU Super Post", row.name, "hidden", 1 if action == "hide" else 0)
	return _super(row.course)


# ---- masterminds -------------------------------------------------------------


def _topics(text):
	return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _meeting(doc, me=None, staff=False):
	people = list(doc.people)
	item = {
		"id": doc.name,
		"course": doc.course,
		"title": doc.title,
		"starts_at": str(get_datetime(doc.starts_at)),
		"topics": _topics(doc.topics),
		"link": doc.link or "",
		"outcome": doc.outcome or "",
		"past": get_datetime(doc.starts_at) < now_datetime(),
		"going_count": sum(1 for p in people if p.going),
	}
	if staff:
		item["people"] = [
			{
				"member": p.member,
				"name": frappe.db.get_value("User", p.member, "full_name") or p.member,
				"going": bool(p.going),
				"attended": bool(p.attended),
			}
			for p in people
		]
	else:
		mine = next((p for p in people if p.member == me), None)
		item["going"] = bool(mine and mine.going)
		item["attended"] = bool(mine and mine.attended)
	return item


def _listing(courses, me, staff=False):
	names = frappe.get_all(
		"OU Mastermind",
		{"course": ["in", courses]} if courses else {"name": ""},
		pluck="name",
		order_by="starts_at asc",
		limit_page_length=0,
	)
	items = [_meeting(frappe.get_doc("OU Mastermind", name), me, staff) for name in names]
	return {
		"tz": get_system_timezone(),
		"upcoming": [m for m in items if not m["past"]],
		"past": sorted((m for m in items if m["past"]), key=lambda m: m["starts_at"], reverse=True),
	}


@frappe.whitelist()
def masterminds(course: str = ""):
	return _listing([_course(course)], _member())


@frappe.whitelist(methods=["POST"])
def set_going(mastermind: str, going: int):
	me = _member()
	doc = (
		frappe.get_doc("OU Mastermind", mastermind) if frappe.db.exists("OU Mastermind", mastermind) else None
	)
	if not doc:
		frappe.throw(_("Meeting not found."), frappe.DoesNotExistError)
	_access(doc.course)
	row = next((p for p in doc.people if p.member == me), None)
	if row:
		row.going = 1 if int(going) else 0
	elif int(going):
		doc.append("people", {"member": me, "going": 1})
	# nosemgrep: lms-unjustified-ignore-permissions - the participant only changes their own row after an enrolment check
	doc.save(ignore_permissions=True)
	return masterminds(doc.course)


# ---- instructor side ----------------------------------------------------------


@frappe.whitelist()
def teacher_masterminds(course: str = ""):
	me = _member()
	courses = review_courses(me)
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
	data = _listing(courses, me, staff=True)
	data["courses"] = [{"id": name, "title": titles.get(name, name)} for name in courses]
	data["participants"] = {
		name: [
			{"member": m, "name": frappe.db.get_value("User", m, "full_name") or m}
			for m in points._enrolled(name)
		]
		for name in courses
	}
	return data


def _staff_meeting(name):
	doc = frappe.get_doc("OU Mastermind", name) if name and frappe.db.exists("OU Mastermind", name) else None
	if not doc:
		frappe.throw(_("Meeting not found."), frappe.DoesNotExistError)
	_staff_course(doc.course)
	return doc


@frappe.whitelist(methods=["POST"])
def save_mastermind(
	course: str,
	title: str,
	starts_at: str,
	topics: str = "",
	link: str = "",
	outcome: str = "",
	mastermind: str = "",
):
	_staff_course(course)
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
		frappe.throw(_("Write the meeting title in up to 140 characters."))
	try:
		when = get_datetime(starts_at)
	except Exception:
		frappe.throw(_("Check the date and time of the meeting."))
	lines = _topics(topics)
	if len(lines) > MAX_TOPICS or any(len(line) > 200 for line in lines):
		frappe.throw(_("Up to 15 topics, each up to 200 characters."))
	link = (link or "").strip()
	if link and not link.lower().startswith(("https://", "http://")):
		frappe.throw(_("The meeting link must start with https://"))
	if not isinstance(outcome, str) or len(outcome) > MAX_NOTE:
		frappe.throw(_("The summary is too long."))
	values = {
		"title": title.strip(),
		"starts_at": when,
		"topics": "\n".join(lines),
		"link": link,
		"outcome": outcome.strip(),
	}
	if mastermind:
		doc = _staff_meeting(mastermind)
		if doc.course != course:
			frappe.throw(_("A meeting cannot move to another course."))
		doc.update(values)
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
		frappe.get_doc({"doctype": "OU Mastermind", "course": course, **values}).insert(
			ignore_permissions=True
		)
	return teacher_masterminds()


@frappe.whitelist(methods=["POST"])
def mark_attendance(mastermind: str, members: list):
	doc = _staff_meeting(mastermind)
	if not isinstance(members, list):
		frappe.throw(_("Choose the participants."))
	allowed = set(points._enrolled(doc.course))
	present = {m for m in members if m in allowed}
	known = {p.member: p for p in doc.people}
	for member in present:
		if member in known:
			known[member].attended = 1
		else:
			doc.append("people", {"member": member, "attended": 1})
	for member, row in known.items():
		if member not in present and row.attended:
			row.attended = 0
	# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
	doc.save(ignore_permissions=True)
	for person in doc.people:
		key = f"ma:{doc.name}:{person.member}"
		if person.attended:
			points.award(person.member, "mastermind_attended", key, doc.course)
		else:
			points.revoke(key)
	return teacher_masterminds()


@frappe.whitelist(methods=["POST"])
def delete_mastermind(mastermind: str):
	doc = _staff_meeting(mastermind)
	for person in doc.people:
		points.revoke(f"ma:{doc.name}:{person.member}")
	# nosemgrep: lms-unjustified-ignore-permissions - the caller is an instructor of this course
	frappe.delete_doc("OU Mastermind", doc.name, ignore_permissions=True, force=True)
	return teacher_masterminds()
