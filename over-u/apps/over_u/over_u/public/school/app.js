import { openGuide, dismissWelcome } from "./guide.js";
import { t } from "./i18n.js";
import { api } from "./api.js";
import {
	shell,
	homeView,
	learningView,
	courseView,
	lessonView,
	assignmentsView,
	resultsView,
	profileView,
	teacherAssignmentsView,
	teacherAssignmentView,
	loadingView,
	errorView,
} from "./views.js";
const root = document.getElementById("school");
const announce = (message) => {
	document.getElementById("announcements").textContent = message;
};
const drafts = {
	quizTaking: new Set(),
	quizAnswers: new Map(),
	homeworkAnswers: new Map(),
	homeworkEditing: new Set(),
};
let home,
	data,
	route,
	sequence = 0,
	lastPath = "",
	busy = false;
function parseRoute() {
	const parts = location.pathname
		.replace(/\/$/, "")
		.split("/")
		.slice(2)
		.map(decodeURIComponent);
	if (!parts.length) return { view: "home" };
	if (parts[0] === "courses" && parts[1] && parts.length === 2)
		return { view: "course", course: parts[1] };
	if (
		parts[0] === "courses" &&
		parts[1] &&
		parts[2] === "lessons" &&
		parts[3] &&
		parts.length === 4
	)
		return { view: "lesson", course: parts[1], number: parts[3] };
	if (
		parts.length === 1 &&
		["learning", "assignments", "results", "profile"].includes(parts[0])
	)
		return { view: parts[0] };
	if (parts.length === 1 && parts[0] === "teacher")
		return { view: "teacher" };
	if (parts.length === 2 && parts[0] === "teacher" && parts[1])
		return { view: "teacher-detail", submission: parts[1] };
	throw new Error(t("ui_127"));
}
function section() {
	return ["course", "lesson"].includes(route?.view)
		? "learning"
		: route?.view === "teacher-detail"
		? "teacher"
		: route?.view || "home";
}
function paint(content, focus = false) {
	root.innerHTML = shell(content, home, section());
	if (focus) {
		document.getElementById("main").focus({ preventScroll: true });
		window.scrollTo({ top: 0, behavior: "instant" });
	}
}
function showData(focus = false) {
	const views = {
		home: homeView,
		learning: learningView,
		assignments: assignmentsView,
		results: resultsView,
		profile: profileView,
		teacher: teacherAssignmentsView,
	};
	const content =
		route.view === "lesson"
			? lessonView(data, drafts)
			: route.view === "course"
			? courseView(data)
			: route.view === "teacher-detail"
			? teacherAssignmentView(data)
			: views[route.view](route.view === "teacher" ? data : home);
	paint(content, focus);
	const title =
		route.view === "lesson"
			? data.lesson.title
			: route.view === "course"
			? data.title
			: route.view === "teacher-detail"
			? data.assignment
			: {
					home: t("ui_001"),
					learning: t("ui_002"),
					assignments: t("ui_003"),
					results: t("ui_004"),
					profile: t("ui_005"),
					teacher: t("ui_152"),
			  }[route.view];
	document.title = `${title} — OVER U`;
}
async function loadRoute({ refresh = false } = {}) {
	const ticket = ++sequence;
	try {
		route = parseRoute();
		if (!refresh) paint(loadingView());
		const nextHome = await api.home();
		const next =
			route.view === "lesson"
				? await api.lesson(route.course, route.number)
				: route.view === "course"
				? await api.course(route.course)
				: route.view === "teacher"
				? await api.teacherAssignments()
				: route.view === "teacher-detail"
				? await api.teacherAssignment(route.submission)
				: null;
		if (ticket !== sequence) return;
		home = nextHome;
		data = next;
		showData(!refresh);
		lastPath = location.pathname;
	} catch (error) {
		if (ticket === sequence) paint(errorView(error), true);
	}
}
function navigate(href) {
	if (href === location.pathname) return loadRoute({ refresh: true });
	history.pushState({}, "", href);
	loadRoute();
}
window.addEventListener("popstate", () => loadRoute());
root.addEventListener("click", async (event) => {
	const anchor = event.target.closest("a[data-nav]");
	if (
		anchor &&
		event.button === 0 &&
		!event.metaKey &&
		!event.ctrlKey &&
		!event.shiftKey &&
		!event.altKey
	) {
		event.preventDefault();
		navigate(anchor.getAttribute("href"));
		return;
	}
	const control = event.target.closest("button[data-action]");
	if (!control || busy) return;
	const action = control.dataset.action;
	if (action === "retry" || action === "refresh-status")
		return loadRoute({ refresh: true });
	if (action === "guide") return openGuide();
	if (action === "welcome-dismiss") {
		dismissWelcome();
		control.closest(".ou-welcome")?.remove();
		return;
	}
	if (action === "logout") {
		busy = true;
		control.disabled = true;
		try {
			await api.logout();
		} catch (error) {
			const feedback = document.getElementById("logout-feedback");
			if (feedback) feedback.textContent = error.message;
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
	const key = `${route.course}/${route.number}`;
	if (action === "quiz-retry") {
		drafts.quizTaking.add(key);
		showData();
		document.querySelector("#quiz-form input")?.focus();
		return;
	}
	if (action === "homework-edit") {
		drafts.homeworkEditing.add(key);
		showData();
		document.getElementById("homework-answer")?.focus();
		return;
	}
	if (action === "complete") {
		const path = location.pathname;
		busy = true;
		control.disabled = true;
		control.textContent = t("ui_128");
		try {
			const updated = await api.complete(route.course, route.number);
			if (path === location.pathname) {
				data = updated;
				showData();
				announce(updated.lesson.complete ? t("ui_129") : t("ui_130"));
			}
		} catch (error) {
			const feedback = document.getElementById("action-feedback");
			if (feedback) feedback.textContent = error.message;
		} finally {
			busy = false;
			if (control.isConnected) {
				control.disabled = false;
				control.textContent = t("ui_131");
			}
		}
	}
});
root.addEventListener("input", (event) => {
	if (route?.view !== "lesson") return;
	const key = `${route.course}/${route.number}`;
	if (event.target.id === "homework-answer")
		drafts.homeworkAnswers.set(key, event.target.value);
	if (event.target.matches("#quiz-form input[type=radio]")) {
		const answers = drafts.quizAnswers.get(key) || [];
		answers[Number(event.target.name.split("-")[1])] = Number(
			event.target.value
		);
		drafts.quizAnswers.set(key, answers);
	}
});
root.addEventListener("submit", async (event) => {
	const form = event.target;
	if (
		!["quiz-form", "homework-form", "teacher-review-form"].includes(form.id)
	)
		return;
	event.preventDefault();
	if (busy || !form.reportValidity()) return;
	const current = { ...route },
		path = location.pathname,
		key = `${current.course}/${current.number}`;
	const submit = form.querySelector("button[type=submit]"),
		original = submit.innerHTML;
	const feedback = form.querySelector("#form-feedback");
	feedback.textContent = "";
	busy = true;
	submit.disabled = true;
	submit.textContent = t("ui_132");
	try {
		let updated;
		if (form.id === "teacher-review-form") {
			updated = await api.reviewAssignment(
				new FormData(form).get("submission"),
				new FormData(form).get("status"),
				new FormData(form).get("comments")
			);
			navigate("/school/teacher");
		} else if (form.id === "quiz-form") {
			const values = new FormData(form);
			const answers = data.quiz.questions.map(
				(q, i) => q.options[Number(values.get(`question-${i}`))]
			);
			updated = await api.quiz(current.course, current.number, answers);
			drafts.quizTaking.delete(key);
			drafts.quizAnswers.delete(key);
		} else {
			updated = await api.homework(
				current.course,
				current.number,
				new FormData(form).get("answer")
			);
			drafts.homeworkEditing.delete(key);
			drafts.homeworkAnswers.delete(key);
		}
		if (path === location.pathname) {
			data = updated;
			showData();
			const target = document.querySelector(
				".quiz-result h2, .homework-status strong"
			);
			if (target) {
				target.tabIndex = -1;
				target.focus({ preventScroll: true });
			}
			announce(form.id === "quiz-form" ? t("ui_133") : t("ui_134"));
		}
	} catch (error) {
		if (form.isConnected) {
			feedback.textContent = error.message;
			feedback.tabIndex = -1;
			feedback.focus();
		}
	} finally {
		busy = false;
		if (submit.isConnected) {
			submit.disabled = false;
			submit.innerHTML = original;
		}
	}
});
// Refresh only a read-only, waiting assignment. Never replace a draft or quiz in progress.
async function checkGrade() {
	if (
		document.hidden ||
		busy ||
		route?.view !== "lesson" ||
		data?.assignment?.submission?.status !== "Not Graded"
	)
		return;
	const key = `${route.course}/${route.number}`;
	if (drafts.homeworkEditing.has(key)) return;
	const path = location.pathname;
	try {
		const updated = await api.lesson(route.course, route.number);
		if (
			path === location.pathname &&
			path === lastPath &&
			updated.assignment?.submission?.status !==
				data.assignment.submission.status
		) {
			data = updated;
			showData();
			announce(t("ui_135"));
		}
	} catch {
		/* Keep the last saved answer visible; explicit refresh exposes errors. */
	}
}
window.addEventListener("focus", checkGrade);
document.addEventListener("visibilitychange", checkGrade);
setInterval(checkGrade, 15000);
loadRoute();
