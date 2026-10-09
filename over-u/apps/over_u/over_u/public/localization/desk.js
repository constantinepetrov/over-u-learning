// Localize the stock setup intro's deliberately multilingual decorative greeting.
// Only this known UI element is touched; no forms, user text or enum values change.
if (frappe.boot?.lang === 'ru') {
  const observer = new MutationObserver(() => {
    const hello = document.querySelector('.setup-intro__hello')
    if (!hello || hello.dataset.overULocalized || !frappe.wizard) return
    clearTimeout(frappe.wizard.hello_timer)
    hello.dataset.overULocalized = '1'
    hello.lang = 'ru'
    hello.textContent = __('Hello')
  })
  observer.observe(document.body, {childList: true, subtree: true})
}
