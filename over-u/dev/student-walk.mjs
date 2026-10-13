import { pathToFileURL } from "node:url";
import fs from "node:fs";

const base = process.env.OVER_U_BASE_URL;
const username = process.env.OVER_U_STUDENT_USER;
const password = process.env.OVER_U_STUDENT_PASSWORD;
const out = "/tmp/overu-student-walk";
fs.mkdirSync(out, { recursive: true });
const { chromium, devices } = await import(
	pathToFileURL(
		`${process.env.RUNNER_TEMP}/over-u-playwright/node_modules/playwright/index.mjs`
	)
);
const browser = await chromium.launch({
	args: [
		"--no-sandbox",
		"--ignore-certificate-errors",
		"--host-resolver-rules=MAP over-u.localhost 127.0.0.1",
	],
});
const log = { landing: null, shots: [], notes: [] };

async function shoot(page, name, url, wait = 2500) {
	try {
		if (url) {
			await page.goto(`${base}${url}`, {
				waitUntil: "networkidle",
				timeout: 60000,
			});
		}
		await page.waitForTimeout(wait);
		await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
		log.shots.push(name);
	} catch (error) {
		log.notes.push(`${name}: ${error.message}`);
	}
}

try {
	const desktop = await browser.newContext({
		viewport: { width: 1440, height: 1000 },
		ignoreHTTPSErrors: true,
	});
	const page = await desktop.newPage();
	await page.goto(`${base}/school`, {
		waitUntil: "networkidle",
		timeout: 60000,
	});
	log.notes.push(`logged-out /school -> ${page.url()}`);
	await shoot(page, "d01-login", null, 1500);
	await page.fill("#login_email", username);
	await page.fill("#login_password", password);
	await Promise.all([
		page
			.waitForURL((url) => !url.pathname.startsWith("/login"), {
				timeout: 30000,
			})
			.catch(() => {}),
		page.click('button[type="submit"]'),
	]);
	await page.waitForLoadState("networkidle").catch(() => {});
	log.landing = page.url();
	await shoot(page, "d02-after-login", null, 3000);
	await shoot(page, "d03-school-home", "/school");
	await shoot(page, "d04-learning", "/school/learning");
	await shoot(page, "d05-course", "/school/courses/over-u");
	await shoot(page, "d06-lesson-1-1", "/school/courses/over-u/lessons/1.1");
	await shoot(
		page,
		"d07-lesson-1-2-locked",
		"/school/courses/over-u/lessons/1.2"
	);
	await shoot(page, "d08-assignments", "/school/assignments");
	await shoot(page, "d09-results", "/school/results");
	await shoot(page, "d10-profile", "/school/profile");
	await shoot(page, "d11-lms-as-student", "/lms");
	await shoot(page, "d12-update-password-form", "/update-password");

	const mobile = await browser.newContext({
		...devices["iPhone 13"],
		ignoreHTTPSErrors: true,
	});
	const mp = await mobile.newPage();
	await mp.goto(`${base}/login`, { waitUntil: "networkidle", timeout: 60000 });
	await shoot(mp, "m01-login", null, 1500);
	await mp.fill("#login_email", username);
	await mp.fill("#login_password", password);
	await Promise.all([
		mp
			.waitForURL((url) => !url.pathname.startsWith("/login"), {
				timeout: 30000,
			})
			.catch(() => {}),
		mp.click('button[type="submit"]'),
	]);
	await mp.waitForLoadState("networkidle").catch(() => {});
	await shoot(mp, "m02-after-login", null, 3000);
	await shoot(mp, "m03-school-home", "/school");
	await shoot(mp, "m04-lesson-1-1", "/school/courses/over-u/lessons/1.1");
	await shoot(mp, "m05-profile", "/school/profile");
} finally {
	await browser.close();
	console.log(JSON.stringify(log));
}
