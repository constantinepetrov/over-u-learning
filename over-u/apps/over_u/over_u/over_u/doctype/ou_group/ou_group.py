import frappe
from frappe import _
from frappe.model.document import Document


class OUGroup(Document):
	def validate(self):
		seen = set()
		for row in self.members:
			if row.member in seen:
				frappe.throw(_("{0} is listed twice.").format(row.member))
			seen.add(row.member)
			# A learner belongs to one buddy pair and one team, never two of a kind.
			clash = frappe.db.sql(
				"""select g.title from `tabOU Group` g join `tabOU Group Member` m on m.parent = g.name
				where g.kind = %s and m.member = %s and g.name != %s limit 1""",
				(self.kind, row.member, self.name or ""),
			)
			if clash:
				frappe.throw(
					_("{0} is already in the group {1}.").format(row.member, clash[0][0])
				)
