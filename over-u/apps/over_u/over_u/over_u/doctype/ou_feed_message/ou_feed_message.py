import frappe
from frappe.model.document import Document


class OUFeedMessage(Document):
	def on_trash(self):
		# Replies and reactions never outlive their message.
		for name in frappe.get_all("OU Feed Message", {"reply_to": self.name}, pluck="name"):
			# nosemgrep: lms-unjustified-ignore-permissions - cascade delete of replies of a message the caller was already allowed to delete
			frappe.delete_doc("OU Feed Message", name, ignore_permissions=True, force=True)
		frappe.db.delete("OU Feed Reaction", {"message": self.name})
