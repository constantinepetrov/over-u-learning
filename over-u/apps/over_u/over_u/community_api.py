"""Answer feed under assignments and the rating screen.

Same rules as student_api: everything is scoped to the signed-in session, the browser
never supplies a member, and other learners' answers open only after the learner has
submitted their own. Email addresses never leave the server: authors are shown by name.
"""

import frappe
from frappe import _

from over_u import points
from over_u.student_api import _access, _assessment_id, _member, _open_lesson, _rich

REACTIONS = {"like": "Нравится", "useful": "Полезно"}
MAX_TEXT = 2000
HOURLY_LIMIT = 30


def _context(course, number):
	doc = _open_lesson(course, number)
	return _assessment_id(doc, "assignment")


def _can_moderate(course, user=None):
	from lms.lms.permissions import can_author_course

	user = user or frappe.session.user
	return bool(points.is_staff(user) and can_author_course(course, user=user))


def _own_answer(assignment, member):
	answer = frappe.db.get_value(
		"LMS Assignment Submission", {"assignment": assignment, "member": member}, "answer"
	)
	return bool(_rich(answer).strip()) if answer else False


def _sync_answers(assignment, course):
	"""Mirror submissions into the feed so every answer can be discussed and rated."""
	submissions = frappe.get_all(
		"LMS Assignment Submission",
		{"assignment": assignment},
		["name", "member", "answer", "creation"],
		limit_page_length=0,
	)
	known = {
		row.key: row
		for row in frappe.get_all(
			"OU Feed Message",
			{"assignment": assignment, "kind": "Answer"},
			["name", "key", "text"],
			limit_page_length=0,
		)
	}
	for row in submissions:
		html = _rich(row.answer)
		if not html.strip():
			continue
		key = f"a:{row.name}"
		message = known.get(key)
		if message and message.text != html:
			frappe.db.set_value("OU Feed Message", message.name, "text", html, update_modified=False)
		elif not message:
			try:
				# nosemgrep: lms-unjustified-ignore-permissions - feed rows are written for the verified session user after own-answer and enrolment checks; learners have no DocPerm on the feed doctypes
				doc = frappe.get_doc(
					{
						"doctype": "OU Feed Message",
						"assignment": assignment,
						"course": course,
						"member": row.member,
						"kind": "Answer",
						"text": html,
						"key": key,
					}
				).insert(ignore_permissions=True)
				frappe.db.set_value(
					"OU Feed Message", doc.name, "creation", row.creation, update_modified=False
				)
			except frappe.DuplicateEntryError:
				pass  # another request created it a moment earlier


def _render(row, names, reactions, me, moderator, replies=()):
	mine = {kind for (message, who, kind) in reactions if message == row.name and who == me}
	counts = {
		kind: sum(1 for (message, _w, k) in reactions if message == row.name and k == kind)
		for kind in REACTIONS
	}
	author = names.get(row.member) or ""
	item = {
		"id": row.name,
		"kind": row.kind,
		"author": author,
		"initial": author[:1].upper(),
		"mine": row.member == me,
		"when": str(row.creation),
		"pinned": bool(row.pinned),
		"hidden": bool(row.hidden),
		"reactions": {kind: {"count": counts[kind], "me": kind in mine} for kind in REACTIONS},
		"can_delete": bool(moderator or (row.member == me and row.kind == "Comment")),
		"replies": list(replies),
	}
	# Answers are already sanitized rich text; chat messages are plain text, escaped by the browser.
	item["html" if row.kind == "Answer" else "text"] = row.text or ""
	return item


def _feed(course, assignment):
	me = _member()
	if not points.setting("feed_enabled", 1):
		return {"enabled": False}
	moderator = _can_moderate(course)
	_sync_answers(assignment, course)
	own = _own_answer(assignment, me)
	if not own and not moderator:
		others = frappe.db.count(
			"OU Feed Message", {"assignment": assignment, "kind": "Answer", "hidden": 0, "member": ["!=", me]}
		)
		return {"enabled": True, "unlocked": False, "others": others}
	filters = {"assignment": assignment}
	if not moderator:
		filters["hidden"] = 0
	rows = frappe.get_all(
		"OU Feed Message",
		filters,
		["name", "kind", "member", "text", "reply_to", "pinned", "hidden", "creation"],
		order_by="creation asc",
		limit_page_length=0,
	)
	names = {user: points.short_name(user) for user in {row.member for row in rows}}
	ids = [row.name for row in rows]
	reactions = (
		[
			(r.message, r.member, r.kind)
			for r in frappe.get_all(
				"OU Feed Reaction",
				{"message": ["in", ids]},
				["message", "member", "kind"],
				limit_page_length=0,
			)
		]
		if ids
		else []
	)
	replies_of = {}
	for row in rows:
		if row.reply_to:
			replies_of.setdefault(row.reply_to, []).append(_render(row, names, reactions, me, moderator))
	roots = [
		_render(row, names, reactions, me, moderator, replies_of.get(row.name, []))
		for row in rows
		if not row.reply_to
	]
	roots.sort(key=lambda item: (not item["pinned"], item["when"]), reverse=False)
	return {
		"enabled": True,
		"unlocked": True,
		"messages": roots,
		"others": sum(1 for r in rows if r.kind == "Answer" and r.member != me),
		"can_moderate": moderator,
		"reactions": REACTIONS,
	}


def _message(name, assignment):
	row = frappe.db.get_value(
		"OU Feed Message",
		name,
		["name", "assignment", "member", "kind", "reply_to", "hidden", "course"],
		as_dict=True,
	)
	if not row or row.assignment != assignment:
		frappe.throw(_("Message not found."), frappe.DoesNotExistError)
	return row


@frappe.whitelist(methods=["POST"])
def feed(course: str, number: str):
	_access(course)
	return _feed(course, _context(course, number))


@frappe.whitelist(methods=["POST"])
def post_message(course: str, number: str, text: str, reply_to: str = ""):
	assignment = _context(course, number)
	me = _member()
	if not points.setting("feed_enabled", 1):
		frappe.throw(_("The answer feed is switched off."))
	if not (_own_answer(assignment, me) or _can_moderate(course)):
		frappe.throw(
			_("Submit your own answer to see and discuss the answers of others."), frappe.PermissionError
		)
	if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_TEXT:
		frappe.throw(_("Write a message between 1 and 2,000 characters."))
	recent = frappe.db.count(
		"OU Feed Message",
		{"member": me, "creation": [">=", frappe.utils.add_to_date(None, hours=-1)]},
	)
	if recent >= HOURLY_LIMIT:
		frappe.throw(_("Too many messages. Please try again a little later."))
	parent = ""
	if reply_to:
		target = _message(reply_to, assignment)
		# Replies stay one level deep: answering a reply continues the same thread.
		parent = target.reply_to or target.name
		if target.hidden and not _can_moderate(course):
			frappe.throw(_("Message not found."), frappe.DoesNotExistError)
	# nosemgrep: lms-unjustified-ignore-permissions - feed rows are written for the verified session user after own-answer and enrolment checks; learners have no DocPerm on the feed doctypes
	doc = frappe.get_doc(
		{
			"doctype": "OU Feed Message",
			"assignment": assignment,
			"course": course,
			"member": me,
			"kind": "Comment",
			"reply_to": parent or None,
			"text": text.strip(),
			"key": "c:" + frappe.generate_hash(length=12),
		}
	).insert(ignore_permissions=True)
	points.award(me, "comment_posted", f"fm:{doc.name}", course)
	return _feed(course, assignment)


@frappe.whitelist(methods=["POST"])
def react(course: str, number: str, message: str, kind: str):
	assignment = _context(course, number)
	me = _member()
	if kind not in REACTIONS:
		frappe.throw(_("Choose one of the available reactions."))
	if not (_own_answer(assignment, me) or _can_moderate(course)):
		frappe.throw(
			_("Submit your own answer to see and discuss the answers of others."), frappe.PermissionError
		)
	target = _message(message, assignment)
	if target.hidden and not _can_moderate(course):
		frappe.throw(_("Message not found."), frappe.DoesNotExistError)
	if target.member == me:
		frappe.throw(_("You cannot rate your own message."))
	key = f"{target.name}:{me}:{kind}"
	existing = frappe.db.get_value("OU Feed Reaction", {"key": key}, "name")
	if existing:
		# nosemgrep: lms-unjustified-ignore-permissions - feed rows are written for the verified session user after own-answer and enrolment checks; learners have no DocPerm on the feed doctypes
		frappe.delete_doc("OU Feed Reaction", existing, ignore_permissions=True, force=True)
		points.revoke(f"fr:{existing}")
	else:
		try:
			# nosemgrep: lms-unjustified-ignore-permissions - feed rows are written for the verified session user after own-answer and enrolment checks; learners have no DocPerm on the feed doctypes
			reaction = frappe.get_doc(
				{
					"doctype": "OU Feed Reaction",
					"message": target.name,
					"member": me,
					"kind": kind,
					"key": key,
				}
			).insert(ignore_permissions=True)
			points.award(target.member, "reaction_received", f"fr:{reaction.name}", course)
		except frappe.DuplicateEntryError:
			pass
	return _feed(course, assignment)


@frappe.whitelist(methods=["POST"])
def moderate(course: str, number: str, message: str, action: str):
	assignment = _context(course, number)
	me = _member()
	target = _message(message, assignment)
	moderator = _can_moderate(course)
	own_comment = target.member == me and target.kind == "Comment"
	if action not in ("pin", "unpin", "hide", "unhide", "delete"):
		frappe.throw(_("Unknown action."))
	if action == "delete":
		if not (moderator or own_comment) or target.kind == "Answer":
			frappe.throw(_("You cannot delete this message."), frappe.PermissionError)
		for entry in frappe.get_all("OU Feed Reaction", {"message": target.name}, pluck="name"):
			points.revoke(f"fr:{entry}")
		points.revoke(f"fm:{target.name}")
		# nosemgrep: lms-unjustified-ignore-permissions - feed rows are written for the verified session user after own-answer and enrolment checks; learners have no DocPerm on the feed doctypes
		frappe.delete_doc("OU Feed Message", target.name, ignore_permissions=True, force=True)
	else:
		if not moderator:
			frappe.throw(_("Only instructors can moderate the feed."), frappe.PermissionError)
		field, value = {
			"pin": ("pinned", 1),
			"unpin": ("pinned", 0),
			"hide": ("hidden", 1),
			"unhide": ("hidden", 0),
		}[action]
		frappe.db.set_value("OU Feed Message", target.name, field, value)
	return _feed(course, assignment)


@frappe.whitelist(methods=["POST"])
def leaderboard(course: str, period: str = "all"):
	_access(course)
	return points.leaderboard(course, _member(), "week" if period == "week" else "all")
