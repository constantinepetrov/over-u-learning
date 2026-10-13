import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'

const base = process.env.OVER_U_BASE_URL || 'http://127.0.0.1:18000'
const username = process.env.OVER_U_SMOKE_USER
const password = process.env.OVER_U_SMOKE_PASSWORD
assert.ok(username && password, 'Synthetic Course Creator credentials are required')
const { chromium } = await import(pathToFileURL(
	`${process.env.RUNNER_TEMP}/over-u-playwright/node_modules/playwright/index.mjs`,
))

const browser = await chromium.launch({
	args: ['--no-sandbox', '--host-resolver-rules=MAP over-u.localhost 127.0.0.1'],
})
const errors = []
try {
	const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
	page.on('pageerror', (error) => errors.push(error.message))
	page.on('console', (message) => {
		if (message.type() === 'error') errors.push(message.text())
	})

	await page.goto(`${base}/login`, { waitUntil: 'networkidle', timeout: 60000 })
	const login = await page.evaluate(async ({ username, password }) => {
		const response = await fetch('/api/method/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ usr: username, pwd: password }),
		})
		return { status: response.status, body: await response.json() }
	}, { username, password })
	assert.equal(login.status, 200, 'Synthetic author login must succeed')
	assert.ok(['No App', 'Logged In'].includes(login.body.message), 'Login must establish a Frappe session')

	const response = await page.goto(`${base}/lms`, {
		waitUntil: 'networkidle',
		timeout: 60000,
	})
	assert.equal(response?.status(), 200, '/lms must return HTTP 200')
	const heading = page.locator('.author-hero h1')
	await heading.waitFor({ state: 'visible', timeout: 45000 })
	assert.match(await heading.innerText(), /Студия курсов/)
	await page.locator('.author-hero-create').waitFor({ state: 'visible' })
	await page.locator('.author-course').first().waitFor({ state: 'visible', timeout: 30000 })
	const assets = await page.locator('script[src],link[rel="stylesheet"][href]').evaluateAll((nodes) =>
		nodes.map((node) => node.src || node.href).filter((url) => url.includes('/assets/')),
	)
	assert.ok(assets.some((url) => url.includes('/lms/frontend/assets/')), 'Built LMS frontend assets must be served')
	assert.deepEqual(errors, [], `Production image browser errors: ${errors.join('; ')}`)

	await page.screenshot({ path: '/tmp/overu-production-image-lms.png', fullPage: true })
	console.log(JSON.stringify({
		status: 'passed',
		url: page.url(),
		heading: await heading.innerText(),
		courseCards: await page.locator('.author-course').count(),
		frontendAssets: assets,
		javascriptErrors: errors.length,
		screenshot: '/tmp/overu-production-image-lms.png',
	}, null, 2))
} finally {
	await browser.close()
}
