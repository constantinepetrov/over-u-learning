import { teacherGroupsView, teacherPointsView } from "./admin.js";
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
	ratingPage,
	loadingView,
	errorView,
} from "./views.js";
import {
	teacherDeskView,
	teacherAssignmentView,
	teacherCourseView,
	teacherLessonView,
	teacherStudentView,
	teacherMastermindsView,
	teacherSuperView,
} from "./teacher.js";
import {
	goalsView,
	reportView,
	buddyView,
	newStepRow,
	superView,
	mastermindsView,
	helpProfileView,
} from "./goals.js";
const root = document.getElementById("school");
const announce = (message) => {
	document.getElementById("announcements").textContent = message;
};
const drafts = {
	quizTaking: new Set(),
	quizAnswers: new Map(),
	homeworkAnswers: new Map(),
	homeworkEditing: new Set(),
	feedText: new Map(),
};
let home,
	data,
	feed = null,
	disc = null,
	desk = { status: "Not Graded", course: "" },
	period = "all",
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
		["learning", "assignments", "results", "profile", "rating"].includes(
			parts[0]
		)
	)
		return { view: parts[0] };
	if (parts[0] === "goals" && parts.length === 1) return { view: "goals" };
	if (
		parts[0] === "goals" &&
		parts.length === 2 &&
		["report", "buddy", "profile", "masterminds", "super"].includes(
			parts[1]
		)
	)
		return { view: "goals-" + parts[1] };
	if (parts.length === 1 && parts[0] === "teacher")
		return { view: "teacher" };
	if (parts[0] === "teacher" && parts[1] === "courses" && parts[2]) {
		if (parts[3] === "lessons" && parts[4] && parts.length === 5)
			return {
				view: "teacher-lesson",
				course: parts[2],
				number: parts[4],
			};
		if (parts.length === 3)
			return { view: "teacher-course", course: parts[2], tab: "content" };
		if (
			parts.length === 4 &&
			["students", "discussions"].includes(parts[3])
		)
			return { view: "teacher-course", course: parts[2], tab: parts[3] };
	}
	if (
		parts.length === 3 &&
		parts[0] === "teacher" &&
		parts[1] === "students" &&
		parts[2]
	)
		return { view: "teacher-student", student: parts[2] };
	if (
		parts.length === 2 &&
		parts[0] === "teacher" &&
		parts[1] === "masterminds"
	)
		return { view: "teacher-masters" };
	if (
		parts.length === 2 &&
		parts[0] === "teacher" &&
		["groups", "points"].includes(parts[1])
	)
		return { view: "teacher-" + parts[1] };
	if (
		parts.length === 3 &&
		parts[0] === "teacher" &&
		parts[1] === "super" &&
		parts[2]
	)
		return { view: "teacher-super", course: parts[2] };
	if (parts.length === 2 && parts[0] === "teacher" && parts[1])
		return { view: "teacher-detail", submission: parts[1] };
	throw new Error(t("ui_127"));
}
function section() {
	return ["course", "lesson"].includes(route?.view)
		? "learning"
		: String(route?.view || "").startsWith("teacher-")
		? "teacher"
		: String(route?.view || "").startsWith("goals")
		? "goals"
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
		rating: () => ratingPage(data, period),
		teacher: () => teacherDeskView(data),
	};
	const content =
		route.view === "lesson"
			? lessonView(data, drafts, feed, disc)
			: route.view === "course"
			? courseView(data)
			: route.view === "teacher-detail"
			? teacherAssignmentView(data)
			: route.view === "teacher-course"
			? teacherCourseView(data, route.tab)
			: route.view === "teacher-lesson"
			? teacherLessonView(data, drafts)
			: route.view === "teacher-student"
			? teacherStudentView(data)
			: route.view === "goals"
			? goalsView(data)
			: route.view === "goals-report"
			? reportView(data)
			: route.view === "goals-buddy"
			? buddyView(data)
			: route.view === "goals-masterminds"
			? mastermindsView(data)
			: route.view === "goals-super"
			? superView(data)
			: route.view === "goals-profile"
			? helpProfileView(data)
			: route.view === "teacher-groups"
			? teacherGroupsView(data)
			: route.view === "teacher-points"
			? teacherPointsView(data)
			: route.view === "teacher-masters"
			? teacherMastermindsView(data)
			: route.view === "teacher-super"
			? teacherSuperView(data)
			: views[route.view](home);
	paint(content, focus);
	const title =
		route.view === "lesson"
			? data.lesson.title
			: route.view === "course"
			? data.title
			: route.view === "teacher-detail"
			? data.assignment
			: route.view === "teacher-masters"
			? t("ui_326")
			: route.view === "teacher-super"
			? t("ui_319")
			: route.view.startsWith("goals")
			? t("ui_262")
			: ["teacher-course", "teacher-lesson", "teacher-student"].includes(
					route.view
			  )
			? data.title || data.name
			: {
					home: t("ui_001"),
					learning: t("ui_002"),
					assignments: t("ui_003"),
					results: t("ui_004"),
					profile: t("ui_005"),
					teacher: t("ui_152"),
					rating: t("ui_186"),
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
				? await api.teacherDesk(desk.status, desk.course)
				: route.view === "teacher-detail"
				? await api.teacherAssignment(route.submission)
				: route.view === "teacher-course"
				? await api.teacherCourse(route.course)
				: route.view === "teacher-lesson"
				? await api.teacherLesson(route.course, route.number)
				: route.view === "teacher-student"
				? await api.teacherStudent(route.student)
				: ["goals", "goals-buddy"].includes(route.view)
				? await api.myGoals()
				: route.view === "goals-report"
				? await api.myReport()
				: route.view === "goals-masterminds"
				? await api.masterminds()
				: route.view === "goals-super"
				? await api.superFeed()
				: route.view === "goals-profile"
				? await api.myProfile()
				: route.view === "teacher-groups"
				? await api.teacherGroups()
				: route.view === "teacher-points"
				? await api.pointsSettings()
				: route.view === "teacher-masters"
				? await api.teacherMasterminds()
				: route.view === "teacher-super"
				? await api.superFeed(route.course)
				: route.view === "rating"
				? nextHome.courses[0]
					? await api.leaderboard(nextHome.courses[0].id, period)
					: { enabled: false }
				: null;
		const nextFeed =
			route.view === "lesson" && next.assignment && !next.locked
				? await api.feed(route.course, route.number).catch(() => null)
				: null;
		const nextDisc =
			route.view === "lesson" && !next.locked
				? await api
						.comments(route.course, route.number)
						.catch(() => null)
				: null;
		if (ticket !== sequence) return;
		home = nextHome;
		data = next;
		feed = nextFeed;
		disc = route.view === "teacher-lesson" ? next.discussion : nextDisc;
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
	if (action === "rating-period") {
		period = control.dataset.period === "week" ? "week" : "all";
		return loadRoute({ refresh: true });
	}
	if (action === "goal-add-step") {
		control
			.closest("fieldset")
			.querySelector(".step-rows")
			.insertAdjacentHTML("beforeend", newStepRow());
		return;
	}
	if (["step-toggle", "goal-delete"].includes(action)) {
		if (action === "goal-delete" && !window.confirm(t("ui_278"))) return;
		const path = location.pathname;
		busy = true;
		control.disabled = true;
		try {
			const updated =
				action === "step-toggle"
					? await api.setStep(
							control.dataset.goal,
							Number(control.dataset.idx),
							Number(control.dataset.done)
					  )
					: await api.deleteGoal(control.dataset.goal);
			if (path === location.pathname) {
				data = updated;
				showData();
			}
		} catch (error) {
			announce(error.message);
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
	if (action === "rule-preview") {
		const form = control.closest("form");
		const out = form.querySelector(".preview-out");
		busy = true;
		control.disabled = true;
		try {
			const r = await api.previewRule(
				form.dataset.event,
				Number(form.elements.points.value || 0),
				form.elements.enabled.checked ? 1 : 0
			);
			out.textContent = t("ui_394", r.events, r.delta);
		} catch (error) {
			announce(error.message);
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
	if (["super-moderate", "mm-going", "mm-delete", "group-delete"].includes(action)) {
		if (action === "mm-delete" && !window.confirm(t("ui_351"))) return;
		if (action === "group-delete" && !window.confirm(t("ui_380")))
			return;
		const path = location.pathname;
		busy = true;
		control.disabled = true;
		try {
			const updated =
				action === "super-moderate"
					? await api.moderateSuper(
							control.dataset.id,
							control.dataset.mod
					  )
					: action === "mm-going"
					? await api.setGoing(
							control.dataset.id,
							Number(control.dataset.going)
					  )
					: action === "group-delete"
					? await api.deleteGroup(control.dataset.id)
					: await api.deleteMastermind(control.dataset.id);
			if (path === location.pathname) {
				data = updated;
				showData();
			}
		} catch (error) {
			announce(error.message);
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
	if (action === "desk-filter") {
		desk = { ...desk, status: control.dataset.status };
		return loadRoute({ refresh: true });
	}
	if (action === "disc-moderate") {
		const current = { ...route },
			path = location.pathname;
		busy = true;
		control.disabled = true;
		try {
			setDisc(
				await api.moderateComment(
					current.course,
					current.number,
					control.dataset.id,
					control.dataset.mod
				),
				path
			);
		} catch (error) {
			announce(error.message);
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
	if (["feed-react", "feed-moderate"].includes(action)) {
		const current = { ...route },
			path = location.pathname;
		busy = true;
		control.disabled = true;
		try {
			const updated =
				action === "feed-react"
					? await api.react(
							current.course,
							current.number,
							control.dataset.id,
							control.dataset.kind
					  )
					: await api.moderate(
							current.course,
							current.number,
							control.dataset.id,
							control.dataset.mod
					  );
			if (path === location.pathname) {
				feed = updated;
				showData();
			}
		} catch (error) {
			announce(error.message);
		} finally {
			busy = false;
			if (control.isConnected) control.disabled = false;
		}
		return;
	}
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
function setDisc(updated, path) {
	if (path !== location.pathname) return;
	disc = updated;
	if (route.view === "teacher-lesson")
		data = { ...data, discussion: updated };
	showData();
}
root.addEventListener("change", (event) => {
	if (event.target.matches("[data-desk-course]")) {
		desk = { ...desk, course: event.target.value };
		loadRoute({ refresh: true });
	}
});
root.addEventListener("input", (event) => {
	const draft = event.target.dataset?.draft;
	if (draft) drafts.feedText.set(draft, event.target.value);
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
	const submit = event.submitter || form.querySelector("button[type=submit]"),
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
				submit.value,
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
			if (form.id === "homework-form" && updated.assignment)
				feed = await api
					.feed(current.course, current.number)
					.catch(() => feed);
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
root.addEventListener("submit", async (event) => {
	const form = event.target;
	if (
		form.matches(
			"[data-super-form], [data-mm-form], [data-attend-form], [data-group-form], [data-rule-form], [data-board-form], [data-bonus-form], [data-profile-form]"
		)
	) {
		event.preventDefault();
		if (busy || !form.reportValidity()) return;
		const path = location.pathname;
		const submit = form.querySelector("button[type=submit]");
		const box = form.querySelector(".feed-error");
		const values = new FormData(form);
		busy = true;
		submit.disabled = true;
		try {
			let updated;
			if (form.matches("[data-super-form]"))
				updated = await api.postSuper(values.get("text"));
			else if (form.matches("[data-group-form]"))
				updated = await api.saveGroup({
					group: form.dataset.id || "",
					course: form.dataset.course,
					kind: values.get("kind"),
					title: values.get("title"),
					members: values.getAll("member"),
				});
			else if (form.matches("[data-rule-form]"))
				updated = await api.saveRule({
					event: form.dataset.event,
					points_value: Number(values.get("points")),
					enabled: values.get("enabled") ? 1 : 0,
					daily_limit: Number(values.get("daily_limit") || 0),
				});
			else if (form.matches("[data-board-form]"))
				updated = await api.saveBoard({
					enabled: values.get("enabled") ? 1 : 0,
					visibility: values.get("visibility"),
					limit: Number(values.get("limit")),
					prizes: values.get("prizes") || "",
				});
			else if (form.matches("[data-bonus-form]")) {
				const chosen = form.elements.member.selectedOptions[0];
				updated = await api.giveBonus({
					member: values.get("member"),
					course: chosen.dataset.course,
					value: Number(values.get("value")),
					reason: values.get("reason"),
				});
			} else if (form.matches("[data-profile-form]")) {
				const blocks = {};
				for (const [key, value] of values.entries()) {
					const [block, field] = key.split("__");
					blocks[block] = blocks[block] || { shared: false };
					if (field === "shared") blocks[block].shared = true;
					else blocks[block][field] = value;
				}
				["about", "offer", "strengths", "help", "expertise"].forEach(
					(b) => (blocks[b] = blocks[b] || { shared: false })
				);
				updated = await api.saveProfile(blocks);
			} else if (form.matches("[data-attend-form]"))
				updated = await api.markAttendance(
					form.dataset.id,
					values.getAll("member")
				);
			else
				updated = await api.saveMastermind({
					mastermind: form.dataset.id || "",
					course: form.dataset.id
						? form.elements.course.value
						: values.get("course"),
					title: values.get("title"),
					starts_at: String(values.get("starts_at")).replace(
						"T",
						" "
					),
					link: values.get("link") || "",
					topics: values.get("topics") || "",
					outcome: values.get("outcome") || "",
				});
			if (path === location.pathname) {
				data = updated;
				showData();
			}
		} catch (error) {
			if (box) box.textContent = error.message;
			announce(error.message);
		} finally {
			busy = false;
			if (submit.isConnected) submit.disabled = false;
		}
		return;
	}
	if (form.matches("[data-goal-form], [data-report-form]")) {
		event.preventDefault();
		if (busy || !form.reportValidity()) return;
		const path = location.pathname;
		const submit = form.querySelector("button[type=submit]");
		const box = form.querySelector(".feed-error");
		const values = new FormData(form);
		busy = true;
		submit.disabled = true;
		try {
			let updated;
			if (form.matches("[data-goal-form]")) {
				const steps = [...form.querySelectorAll(".step-row")].map(
					(row) => ({
						title: row.querySelector("[name=step_title]").value,
						due: row.querySelector("[name=step_due]").value,
						done: row.querySelector("[name=step_done]").checked
							? 1
							: 0,
					})
				);
				updated = await api.saveGoal({
					goal: form.dataset.goal || "",
					kind: values.get("kind") || undefined,
					title: values.get("title"),
					details: values.get("details") || "",
					target_date: values.get("target_date") || "",
					shared: form.elements.shared.checked ? 1 : 0,
					steps,
				});
			} else {
				updated = await api.saveReport({
					goals_done: values.get("goals_done") || "",
					insights: values.get("insights") || "",
					tasks_done: values.get("tasks_done") || "",
					suggestions: values.get("suggestions") || "",
				});
			}
			if (path === location.pathname) {
				data = updated;
				showData();
			}
		} catch (error) {
			if (box) box.textContent = error.message;
			announce(error.message);
		} finally {
			busy = false;
			if (submit.isConnected) submit.disabled = false;
		}
		return;
	}
	if (form.matches("[data-disc-form]")) {
		event.preventDefault();
		if (busy || !form.reportValidity()) return;
		const current = { ...route },
			path = location.pathname;
		const submit = form.querySelector("button[type=submit]");
		const slot = form.dataset.reply
			? `d:reply:${form.dataset.reply}`
			: "d:main";
		busy = true;
		submit.disabled = true;
		try {
			const updated = await api.comment(
				current.course,
				current.number,
				form.elements.text.value,
				form.dataset.reply || "",
				form.elements.private?.checked ? 1 : 0
			);
			drafts.feedText.delete(slot);
			setDisc(updated, path);
		} catch (error) {
			const box =
				form.querySelector(".feed-error") ||
				document.getElementById("announcements");
			box.textContent = error.message;
			announce(error.message);
		} finally {
			busy = false;
			if (submit.isConnected) submit.disabled = false;
		}
		return;
	}
	if (!form.matches("[data-feed-form]")) return;
	event.preventDefault();
	if (busy || !form.reportValidity()) return;
	const current = { ...route },
		path = location.pathname;
	const field = form.elements.text,
		submit = form.querySelector("button[type=submit]");
	const slot = form.dataset.reply ? `reply:${form.dataset.reply}` : "main";
	busy = true;
	submit.disabled = true;
	try {
		const updated = await api.post(
			current.course,
			current.number,
			field.value,
			form.dataset.reply || ""
		);
		drafts.feedText.delete(slot);
		if (path === location.pathname) {
			feed = updated;
			showData();
		}
	} catch (error) {
		const box =
			form.querySelector(".feed-error") ||
			document.getElementById("announcements");
		box.textContent = error.message;
		announce(error.message);
	} finally {
		busy = false;
		if (submit.isConnected) submit.disabled = false;
	}
});
// Pull in new messages while the learner is reading, but never while they are typing.
async function refreshDisc() {
	if (
		document.hidden ||
		busy ||
		!["lesson", "teacher-lesson"].includes(route?.view) ||
		!disc
	)
		return;
	if (document.activeElement?.closest?.(".discussion")) return;
	const path = location.pathname;
	try {
		const updated = await api.comments(route.course, route.number);
		if (JSON.stringify(updated) !== JSON.stringify(disc))
			setDisc(updated, path);
	} catch {
		/* Keep the last loaded discussion. */
	}
}
setInterval(refreshDisc, 20000);
async function refreshFeed() {
	if (document.hidden || busy || route?.view !== "lesson" || !feed?.unlocked)
		return;
	if (document.activeElement?.closest?.(".feed")) return;
	const path = location.pathname;
	try {
		const updated = await api.feed(route.course, route.number);
		if (
			path === location.pathname &&
			JSON.stringify(updated) !== JSON.stringify(feed)
		) {
			feed = updated;
			showData();
		}
	} catch {
		/* Keep the last loaded messages. */
	}
}
setInterval(refreshFeed, 20000);
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
