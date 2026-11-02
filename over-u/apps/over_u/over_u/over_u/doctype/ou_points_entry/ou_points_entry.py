import frappe
from frappe.model.document import Document


class OUPointsEntry(Document):
	def before_insert(self):
		# Hand-made bonus entries get a unique key; automatic ones bring their own.
		if not self.key:
			self.key = "manual:" + frappe.generate_hash(length=12)
			self.event = self.event or "manual"
		self.awarded_by = self.awarded_by or frappe.session.user
