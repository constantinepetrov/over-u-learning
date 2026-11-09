import frappe
from frappe.model.document import Document


class OULessonComment(Document):
	def on_trash(self):
		# Replies never outlive their message.
		for name in frappe.get_all("OU Lesson Comment", {"reply_to": self.name}, pluck="name"):
			# nosemgrep: lms-unjustified-ignore-permissions - cascade delete of replies of a comment the caller was already allowed to delete
			frappe.delete_doc("OU Lesson Comment", name, ignore_permissions=True, force=True)
