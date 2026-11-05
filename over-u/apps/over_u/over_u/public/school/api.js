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
const practice = new Set([
	"super_feed",
	"post_super",
	"moderate_super",
	"masterminds",
	"set_going",
	"teacher_masterminds",
	"save_mastermind",
	"mark_attendance",
	"delete_mastermind",
]);
const admin = new Set([
	"teacher_groups",
	"save_group",
	"delete_group",
	"points_settings",
	"preview_rule",
	"save_rule",
	"save_board",
	"give_bonus",
	"my_profile",
	"save_profile",
]);
const studio = new Set([
	"studio_course",
	"save_module",
	"save_lesson",
	"move_item",
	"set_published",
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
		!goals.has(method) &&
		!practice.has(method) &&
		!admin.has(method) &&
		!studio.has(method)
	)
		throw new SchoolError(t("ui_136"), 400);
	let response;
	try {
		response = await fetch(
			`/api/method/over_u.${
				studio.has(method)
					? "studio_api"
					: method === "my_profile" || method === "save_profile"
					? "profile_api"
					: admin.has(method)
					? "admin_api"
					: practice.has(method)
					? "practice_api"
					: goals.has(method)
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
	superFeed: (course = "") => request("super_feed", { course }),
	postSuper: (text) => request("post_super", { text }),
	moderateSuper: (post, action) =>
		request("moderate_super", { post, action }),
	masterminds: () => request("masterminds"),
	setGoing: (mastermind, going) =>
		request("set_going", { mastermind, going }),
	teacherMasterminds: () => request("teacher_masterminds"),
	saveMastermind: (values) => request("save_mastermind", values),
	markAttendance: (mastermind, members) =>
		request("mark_attendance", { mastermind, members }),
	deleteMastermind: (mastermind) =>
		request("delete_mastermind", { mastermind }),
	studioCourse: (course) => request("studio_course", { course }),
	saveModule: (values) => request("save_module", values),
	saveLesson: (values) => request("save_lesson", values),
	moveItem: (values) => request("move_item", values),
	setPublished: (course, published) =>
		request("set_published", { course, published }),
	teacherGroups: () => request("teacher_groups"),
	saveGroup: (values) => request("save_group", values),
	deleteGroup: (group) => request("delete_group", { group }),
	pointsSettings: () => request("points_settings"),
	previewRule: (event, points_value, enabled) =>
		request("preview_rule", { event, points_value, enabled }),
	saveRule: (values) => request("save_rule", values),
	saveBoard: (values) => request("save_board", values),
	giveBonus: (values) => request("give_bonus", values),
	myProfile: () => request("my_profile"),
	saveProfile: (blocks) => request("save_profile", { blocks }),
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
