export const boot = JSON.parse(document.getElementById('school-boot').textContent)
const messages = boot.messages || {}
export function t(key, ...values) {
  if (!(key in messages)) throw new Error(`Missing UI translation: ${key}`)
  return messages[key].replace(/\{(\d+)\}/g, (match, i) => values[i] === undefined ? match : String(values[i]))
}
export const language = boot.language || 'ru'
