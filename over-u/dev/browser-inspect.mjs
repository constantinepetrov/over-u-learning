import fs from 'node:fs'
import { chromium } from 'playwright'

const envFile = process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env'
const env = Object.fromEntries(fs.readFileSync(envFile, 'utf8').trim().split('\n').map(line => {
  const i = line.indexOf('=')
  return [line.slice(0, i), line.slice(i + 1)]
}))
const browser = await chromium.launch({executablePath: '/usr/bin/chromium', args: ['--no-sandbox', '--host-resolver-rules=MAP over-u.localhost 127.0.0.1']})
const context = await browser.newContext({viewport: {width: 1440, height: 1000}})
const page = await context.newPage()
page.on('pageerror', error => console.log('PAGE ERROR:', error.message))
await page.goto('http://over-u.localhost:8000/login')
const result = await page.evaluate(async (password) => {
  const response = await fetch('/api/method/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({usr: 'student2@over-u.example.com', pwd: password})})
  return {status: response.status}
}, env.OVER_U_DEMO_PASSWORD)
console.log('LOGIN', result)
await page.goto('http://over-u.localhost:8000/lms/courses')
await page.waitForTimeout(4000)
console.log('URL', page.url())
console.log('PAGE', (await page.locator('body').innerText()).slice(0, 4500))
console.log('BOOT', await page.evaluate(() => ({globals: Object.keys(window).filter(key => /boot|csrf|frappe/.test(key)), hasCsrf: !!(window.csrf_token || window.boot?.csrf_token || window.frappe?.boot?.csrf_token)})))
await page.screenshot({path: '/workspace/over-u-learning/over-u/evidence/initial-student.png', fullPage: true})
await browser.close()
