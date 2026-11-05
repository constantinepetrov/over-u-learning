import { t, language } from "./i18n.js";
// The only browser module that knows the server adapter's endpoint names.
const boot = JSON.parse(document.getElementById("school-boot").textContent);
const methods = new Set([
	"home",
	"course",
	"lesson",
	"complete_lesson",
	"submit_quiz",
	"submit_assignment",
	"teacher_assignments",
	"teacher_assignment",
	"review_assignment",
]);
const goals = new Set([
	"my_goals",
	"save_goal",
	"set_step",
	"delete_goal",
	"my_report",
	"save_report",
]);
const discussion = new Set([
	"lesson_comments",
	"post_lesson_comment",
	"moderate_lesson_comment",
	"teacher_desk",
	"teacher_course",
	"teacher_lesson",
	"teacher_student",
]);
const community = new Set([
	"feed",
	"post_message",
	"react",
	"moderate",
	"leaderboard",
]);
export class SchoolError extends Error {
	constructor(message, status) {
		super(message);
		this.status = status;
	}
}
async function request(method, args = {}) {
	if (
		!methods.has(method) &&
		!community.has(method) &&
		!discussion.has(method) &&
		!goals.has(method)
	)
		throw new SchoolError(t("ui_136"), 400);
	let response;
	try {
		response = await fetch(
			`/api/method/over_u.${
				goals.has(method)
					? "goals_api"
					: discussion.has(method)
					? "discussion_api"
					: community.has(method)
					? "community_api"
					: "student_api"
			}.${method}`,
			{
				method: "POST",
				credentials: "same-origin",
				headers: {
					"Content-Type": "application/json",
					"X-Frappe-CSRF-Token": boot.csrf_token,
				},
				body: JSON.stringify(args),
			}
		);
	} catch {
		throw new SchoolError(t("ui_137"), 0);
	}
	const data = await response.json().catch(() => ({}));
	if (!response.ok) {
		let message = response.status === 403 ? t("ui_138") : t("ui_139");
		try {
			const messages = JSON.parse(data._server_messages || "[]");
			const raw = JSON.parse(messages[0] || "{}").message;
			if (raw) {
				const text = new DOMParser().parseFromString(raw, "text/html")
					.body.textContent;
				if (
					(language === "en" || /[А-Яа-яЁё]/.test(text)) &&
					!/doctype|traceback|sql|DocType/i.test(text)
				)
					message = text;
				else if (/maximum number of attempts/i.test(text))
					message = t("ui_140");
			}
		} catch {
			/* Never show tracebacks or raw exception payloads. */
		}
		if (response.status === 401) message = t("ui_141");
		throw new SchoolError(message, response.status);
	}
	return data.message;
}
export const api = {
	home: () => request("home"),
	course: (course) => request("course", { course }),
	lesson: (course, number) => request("lesson", { course, number }),
	complete: (course, number) =>
		request("complete_lesson", { course, number }),
	quiz: (course, number, answers) =>
		request("submit_quiz", { course, number, answers }),
	homework: (course, number, answer) =>
		request("submit_assignment", { course, number, answer }),
	teacherAssignments: (status = "Not Graded", course = "") =>
		request("teacher_assignments", { status, course }),
	teacherDesk: (status = "Not Graded", course = "") =>
		request("teacher_desk", { status, course }),
	teacherCourse: (course) => request("teacher_course", { course }),
	teacherLesson: (course, number) =>
		request("teacher_lesson", { course, number }),
	teacherStudent: (student) => request("teacher_student", { student }),
	myGoals: () => request("my_goals"),
	saveGoal: (goal) => request("save_goal", goal),
	setStep: (goal, index, done) => request("set_step", { goal, index, done }),
	deleteGoal: (goal) => request("delete_goal", { goal }),
	myReport: () => request("my_report"),
	saveReport: (report) => request("save_report", report),
	comments: (course, number) =>
		request("lesson_comments", { course, number }),
	comment: (course, number, text, reply_to = "", priv = 0) =>
		request("post_lesson_comment", {
			course,
			number,
			text,
			reply_to,
			private: priv,
		}),
	moderateComment: (course, number, comment, action) =>
		request("moderate_lesson_comment", { course, number, comment, action }),
	teacherAssignment: (submission) =>
		request("teacher_assignment", { submission }),
	reviewAssignment: (submission, status, comments) =>
		request("review_assignment", { submission, status, comments }),
	feed: (course, number) => request("feed", { course, number }),
	post: (course, number, text, reply_to = "") =>
		request("post_message", { course, number, text, reply_to }),
	react: (course, number, message, kind) =>
		request("react", { course, number, message, kind }),
	moderate: (course, number, message, action) =>
		request("moderate", { course, number, message, action }),
	leaderboard: (course, period) => request("leaderboard", { course, period }),
	logout: async () => {
		let response;
		try {
			response = await fetch("/api/method/logout", {
				method: "POST",
				credentials: "same-origin",
				headers: { "X-Frappe-CSRF-Token": boot.csrf_token },
			});
		} catch {
			throw new SchoolError(t("ui_137"), 0);
		}
		if (!response.ok) throw new SchoolError(t("ui_139"), response.status);
		window.location.assign("/login");
	},
};
