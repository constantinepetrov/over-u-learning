import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const base = process.env.OVER_U_BASE_URL || "http://127.0.0.1:18000";
const username = process.env.OVER_U_SMOKE_USER;
const password = process.env.OVER_U_SMOKE_PASSWORD;
assert.ok(
	username && password,
	"Synthetic Course Creator credentials are required"
);
const { chromium } = await import(
	pathToFileURL(
		`${process.env.RUNNER_TEMP}/over-u-playwright/node_modules/playwright/index.mjs`
	)
);

const browser = await chromium.launch({
	args: [
		"--no-sandbox",
		"--host-resolver-rules=MAP over-u.localhost 127.0.0.1",
	],
});
const errors = [];
const requestFailures = [];
try {
	const page = await browser.newPage({
		viewport: { width: 1440, height: 1000 },
	});
	page.on("pageerror", (error) => errors.push(error.message));
	page.on("requestfailed", (request) => {
		requestFailures.push({
			url: request.url(),
			failure: request.failure()?.errorText || "unknown",
		});
	});
	const httpFailures = [];
	page.on("response", (response) => {
		if (response.status() >= 400) {
			const path = new URL(response.url()).pathname;
			const failure = response.status() + " " + response.url();
			if (
				path.startsWith("/api/") ||
				/\\.(js|css)$/.test(path) ||
				response.status() !== 404
			) {
				errors.push(failure);
			} else {
				httpFailures.push(failure);
			}
		}
	});
	page.on("console", (message) => {
		if (
			message.type() === "error" &&
			!message
				.text()
				.startsWith(
				"Failed to load resource: the server responded with a status of 404"
			)
		) {
			errors.push(message.text());
		}
	});

	await page.goto(`${base}/login`, {
		waitUntil: "networkidle",
		timeout: 60000,
	});
	const login = await page.evaluate(
		async ({ username, password }) => {
			const response = await fetch("/api/method/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ usr: username, pwd: password }),
			});
			return { status: response.status, body: await response.json() };
		},
		{ username, password }
	);
	assert.equal(login.status, 200, "Synthetic author login must succeed");
	assert.ok(
		["No App", "Logged In"].includes(login.body.message),
		"Login must establish a Frappe session"
	);

	const response = await page.goto(`${base}/lms`, {
		waitUntil: "networkidle",
		timeout: 60000,
	});
	assert.equal(response?.status(), 200, "/lms must return HTTP 200");
	const heading = page.locator(".author-hero h1");
	await page.waitForTimeout(3000);
	const diagnostic = await page.evaluate(async () => {
		const identity = await fetch("/api/method/frappe.auth.get_logged_user")
			.then((response) => response.json())
			.catch(() => ({}));
		return {
			url: location.href,
			loggedInUser: identity.message || null,
			appMounted: Boolean(document.querySelector("#app")),
			bodyText: document.body.innerText.slice(0, 1600),
			lmsAssets: [...document.querySelectorAll("script[src],link[href]")]
				.map((node) => node.src || node.href)
				.filter((url) => url.includes("/assets/")),
		};
	});
	if (!(await heading.isVisible().catch(() => false))) {
		await page.screenshot({
			path: "/tmp/overu-production-image-lms.png",
			fullPage: true,
		});
		throw new Error(
			`Branded Course Studio is missing: ${JSON.stringify({
				...diagnostic,
				javascriptErrors: errors,
			})}`
		);
	}
	assert.match(await heading.innerText(), /Студия курсов/);
	await page.locator(".author-hero-create").waitFor({ state: "visible" });
	await page
		.locator(".author-course")
		.first()
		.waitFor({ state: "visible", timeout: 30000 });
	const assets = await page
		.locator('script[src],link[rel="stylesheet"][href]')
		.evaluateAll((nodes) =>
			nodes
				.map((node) => node.src || node.href)
				.filter((url) => url.includes("/assets/"))
		);
	assert.ok(
		assets.some((url) => url.includes("/lms/frontend/assets/")),
		"Built LMS frontend assets must be served"
	);
	await page.screenshot({
		path: "/tmp/overu-production-image-lms.png",
		fullPage: true,
	});
	assert.deepEqual(
		errors,
		[],
		`Production image browser errors: ${JSON.stringify({
			errors,
			requestFailures,
		})}`
	);
	if (httpFailures.length) console.log("Non-JavaScript HTTP 404s: " + JSON.stringify(httpFailures));
	console.log(
		JSON.stringify(
			{
				status: "passed",
				url: page.url(),
				heading: await heading.innerText(),
				courseCards: await page.locator(".author-course").count(),
				frontendAssets: assets,
				javascriptErrors: errors.length,
				screenshot: "/tmp/overu-production-image-lms.png",
			},
			null,
			2
		)
	);
} finally {
	await browser.close();
}
