// Native List View extension: translate the displayed user type, keeping the
// original enum and filters intact. All other stock User settings stay in place.
frappe.listview_settings.User = frappe.listview_settings.User || {}
frappe.listview_settings.User.formatters = {
  ...frappe.listview_settings.User.formatters,
  user_type(value) {
    return frappe.utils.escape_html(__(value || ''))
  },
}
