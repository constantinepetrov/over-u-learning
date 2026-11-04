import { pathToFileURL } from "node:url";
import fs from "node:fs";

const base = process.env.OVER_U_BASE_URL;
const username = process.env.OVER_U_SMOKE_USER;
const password = process.env.OVER_U_SMOKE_PASSWORD;
const out = "/tmp/overu-brand-shots";
fs.mkdirSync(out, { recursive: true });
const { chromium } = await import(
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
const page = await browser.newPage({
	viewport: { width: 1440, height: 1000 },
	ignoreHTTPSErrors: true,
});
const shots = [];
async function shot(name, url, wait = 2500) {
	try {
		await page.goto(`${base}${url}`, {
			waitUntil: "networkidle",
			timeout: 60000,
		});
		await page.waitForTimeout(wait);
		await page.screenshot({ path: `${out}/${name}.png`, fullPage: false });
		shots.push(name);
	} catch (error) {
		console.log(`shot ${name} failed: ${error.message}`);
	}
}
try {
	await shot("01-login", "/login");
	await page.goto(`${base}/login`, { waitUntil: "networkidle" });
	await page.evaluate(
		async ({ username, password }) => {
			await fetch("/api/method/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ usr: username, pwd: password }),
			});
		},
		{ username, password }
	);
	await shot("02-studio-home", "/lms");
	await shot("03-courses", "/lms/courses");
	await shot("04-course-new", "/lms/courses/new");
	await shot("05-course-page", "/lms/courses/over-u");
	try {
		await page.goto(`${base}/lms/courses/over-u`, { waitUntil: "networkidle" });
		await page.getByText("Редактор курса").first().click({ timeout: 8000 });
		await page.waitForTimeout(2500);
		await page.screenshot({ path: `${out}/05b-course-editor.png` });
		shots.push("05b-course-editor");
	} catch (error) {
		console.log(`course editor shot failed: ${error.message}`);
	}
	await shot("05c-lesson", "/lms/courses/over-u/learn/1-1", 4000);
	try {
		await page
			.getByRole("button", { name: /Редактировать|Edit/ })
			.first()
			.click({ timeout: 6000 });
		await page.waitForTimeout(3000);
		await page.screenshot({ path: `${out}/05d-lesson-edit.png` });
		shots.push("05d-lesson-edit");
	} catch (error) {
		console.log(`lesson edit shot failed: ${error.message}`);
	}
	await shot("06-quizzes", "/lms/quizzes");
	await shot("07-assignments", "/lms/assignments");
	await shot("08-batches", "/lms/batches");
	await shot("09-statistics", "/lms/statistics");
	await shot("10-programs", "/lms/programs");
} finally {
	await browser.close();
	console.log(JSON.stringify({ shots }));
}
