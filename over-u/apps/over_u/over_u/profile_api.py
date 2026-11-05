"""Participant profile for mutual help: what I can give, what I need, mastermind expertise.

Private by default. Each block has its own "show to my buddy" switch; instructors of the
participant's courses always see everything. The browser never supplies the member.
"""

import frappe
from frappe import _

from over_u.student_api import _member

MAX_TEXT = 1500
# block -> (text fields, share flag)
BLOCKS = {
	"about": (("about",), "share_about"),
	"offer": (("offer",), "share_offer"),
	"strengths": (("strengths",), "share_strengths"),
	"help": (("help_needed", "help_how"), "share_help"),
	"expertise": (("expertise",), "share_expertise"),
}
FIELDS = [field for fields, _flag in BLOCKS.values() for field in fields]


def profile_of(member, only_shared=False):
	row = frappe.db.get_value(
		"OU Member Profile", member, [*FIELDS, *[f for _x, f in BLOCKS.values()]], as_dict=True
	)
	data = {}
	for block, (fields, flag) in BLOCKS.items():
		shared = bool(row and row.get(flag))
		if only_shared and not shared:
			continue
		values = {field: (row.get(field) if row else "") or "" for field in fields}
		if only_shared and not any(values.values()):
			continue
		data[block] = {**values, "shared": shared}
	return data


@frappe.whitelist()
def my_profile():
	return {"profile": profile_of(_member())}


@frappe.whitelist(methods=["POST"])
def save_profile(blocks: dict):
	me = _member()
	if not isinstance(blocks, dict):
		frappe.throw(_("Fill in the profile."))
	values = {}
	for block, (fields, flag) in BLOCKS.items():
		item = blocks.get(block)
		if not isinstance(item, dict):
			continue
		for field in fields:
			text = item.get(field) or ""
			if not isinstance(text, str) or len(text) > MAX_TEXT:
				frappe.throw(_("A field is too long."))
			values[field] = text.strip()
		values[flag] = 1 if item.get("shared") else 0
	if frappe.db.exists("OU Member Profile", me):
		doc = frappe.get_doc("OU Member Profile", me)
		doc.update(values)
		# nosemgrep: lms-unjustified-ignore-permissions - the profile belongs to the verified session user; learners have no DocPerm on the doctype
		doc.save(ignore_permissions=True)
	else:
		# nosemgrep: lms-unjustified-ignore-permissions - the profile belongs to the verified session user; learners have no DocPerm on the doctype
		frappe.get_doc({"doctype": "OU Member Profile", "member": me, **values}).insert(
			ignore_permissions=True
		)
	return my_profile()
