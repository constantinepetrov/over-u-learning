import { t } from "./i18n.js";
import { escape as e, icon, link, richText } from "./components.js";
import { when, plain, day } from "./community.js";
import { discussionView } from "./discussion.js";
import { superPosts } from "./goals.js";

const studentHref = (email) =>
	"/school/teacher/students/" + encodeURIComponent(email);
const courseHref = (id, tab = "") =>
	"/school/teacher/courses/" +
	encodeURIComponent(id) +
	(tab ? "/" + tab : "");
const status = (value) =>
	({ "Not Graded": t("ui_255"), Pass: t("ui_256"), Fail: t("ui_257") }[
		value
	] || e(value));
export const heading = (eyebrow, title, lead = "") =>
	`<div class="page-heading"><span class="eyebrow">${eyebrow}</span><h1>${e(
		title
	)}</h1>${lead ? `<p>${lead}</p>` : ""}</div>`;
export const crumbs = (items) =>
	`<div class="breadcrumbs">${items
		.map(([href, label]) =>
			href ? link(href, e(label)) : `<span>${e(label)}</span>`
		)
		.join(` ${icon("chevron")} `)}</div>`;
const bar = (p) =>
	`<div class="desk-progress"><progress max="100" value="${
		p.percent
	}" aria-label="${p.percent}%">${p.percent}%</progress><span>${t(
		"ui_247",
		p.completed,
		p.total
	)}</span></div>`;
const empty = (text) => `<p class="desk-empty">${text}</p>`;

function queueRow(row) {
	return `<article class="assignment-row teacher-queue-row"><div><span class="eyebrow">${e(
		row.course
	)} · ${e(row.lesson)}</span><h3>${e(row.assignment)}</h3><p>${link(
		studentHref(row.student),
		e(row.member),
		"student-link"
	)} <span class="desk-status st-${
		row.status === "Not Graded"
			? "new"
			: row.status === "Pass"
			? "ok"
			: "bad"
	}">${status(row.status)}</span></p></div>${link(
		row.href,
		`${t("ui_234")}${icon("arrow")}`,
		"button secondary"
	)}</article>`;
}
function questionRow(q) {
	return `<article class="assignment-row teacher-queue-row"><div><span class="eyebrow">${e(
		q.course_title
	)} · ${e(q.lesson)}</span><h3>${e(q.author)}</h3><p class="desk-quote">${e(
		q.text
	)}</p><span class="help">${when(q.when)} · ${t(
		"ui_217",
		q.messages
	)}</span></div>${link(
		q.href,
		`${t("ui_258")}${icon("arrow")}`,
		"button secondary"
	)}</article>`;
}

export function teacherDeskView(desk) {
	const f = desk.filter;
	const c = desk.counters;
	const counter = (n, label, warn) =>
		`<div class="desk-counter${
			warn && n ? " warn" : ""
		}"><strong>${n}</strong><span>${label}</span></div>`;
	const chips = [
		["Not Graded", t("ui_224")],
		["Pass", t("ui_225")],
		["Fail", t("ui_226")],
		["", t("ui_227")],
	]
		.map(
			([value, label]) =>
				`<button type="button" class="chip${
					f.status === value ? " on" : ""
				}" data-action="desk-filter" data-status="${value}" aria-pressed="${
					f.status === value
				}">${label}</button>`
		)
		.join("");
	const courses = `<label class="sr-only" for="desk-course">${t(
		"ui_228"
	)}</label><select id="desk-course" data-desk-course><option value="">${t(
		"ui_228"
	)}</option>${desk.courses
		.map(
			(x) =>
				`<option value="${e(x.id)}"${
					x.id === f.course ? " selected" : ""
				}>${e(x.title)}</option>`
		)
		.join("")}</select>`;
	return `${heading(
		t("ui_219"),
		t("ui_218")
	)}<div class="desk-counters">${counter(
		c.to_review,
		t("ui_220"),
		true
	)}${counter(c.questions, t("ui_221"), true)}${counter(
		c.students,
		t("ui_222")
	)}${counter(c.reports_today, t("ui_315"))}${counter(
		c.courses,
		t("ui_223")
	)}</div><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_229"
	)}</h2><div class="desk-filters" role="group" aria-label="${t(
		"ui_229"
	)}">${chips}${courses}</div></div>${
		desk.queue.length
			? `<div class="teacher-queue">${desk.queue
					.map(queueRow)
					.join("")}</div>`
			: empty(t("ui_230"))
	}</section><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_231"
	)}</h2></div>${
		desk.questions.length
			? `<div class="teacher-queue">${desk.questions
					.map(questionRow)
					.join("")}</div>`
			: empty(t("ui_232"))
	}</section><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_233"
	)}</h2></div><div class="desk-courses">${desk.courses
		.map(
			(x) =>
				`<a class="desk-course" data-nav href="${e(
					courseHref(x.id)
				)}"><strong>${e(x.title)}</strong>${icon("arrow")}</a>`
		)
		.join(
			""
		)}<a class="desk-course" data-nav href="/school/teacher/masterminds"><strong>${t(
		"ui_353"
	)}</strong>${icon(
		"arrow"
	)}</a><a class="desk-course" data-nav href="/school/teacher/groups"><strong>${t("ui_369"
	)}</strong>${icon(
		"arrow"
	)}</a><a class="desk-course" data-nav href="/school/teacher/points"><strong>${t("ui_385"
	)}</strong>${icon("arrow")}</a></div></section>`;
}

export function teacherAssignmentView(item) {
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[null, item.assignment],
	])}${heading(
		e(item.course),
		item.assignment,
		`${e(item.lesson)} · ${e(item.member)}`
	)}<section class="teacher-review"><div class="review-content"><span class="eyebrow">${t(
		"ui_238"
	)}</span><div class="review-answer">${
		item.answer || `<p>${t("ui_159")}</p>`
	}</div></div><details class="review-prompt"><summary>${t(
		"ui_239"
	)}</summary><div>${
		item.question || ""
	}</div></details><form id="teacher-review-form"><input type="hidden" name="submission" value="${e(
		item.name
	)}"><label for="review-comment">${t(
		"ui_237"
	)}</label><textarea id="review-comment" name="comments" maxlength="10000">${richText(
		item.comments
	)}</textarea><div id="form-feedback" role="alert"></div><div class="review-actions"><button type="submit" name="status" value="Pass" class="button primary">${t(
		"ui_235"
	)}</button><button type="submit" name="status" value="Fail" class="button secondary">${t(
		"ui_236"
	)}</button>${link(
		"/school/teacher",
		t("ui_240"),
		"button quiet"
	)}</div></form></section>`;
}

const tabs = (data, tab) =>
	`<nav class="course-tabs" aria-label="${e(data.title)}">${[
		["content", t("ui_241"), ""],
		["students", t("ui_242"), data.counters.students],
		["discussions", t("ui_243"), data.counters.questions],
	]
		.map(
			([key, label, count]) =>
				`<a data-nav href="${e(
					courseHref(data.id, key === "content" ? "" : key)
				)}" class="${tab === key ? "on" : ""}"${
					tab === key ? ' aria-current="page"' : ""
				}>${label}${count ? ` <b>${count}</b>` : ""}</a>`
		)
		.join("")}</nav>`;

export function teacherCourseView(data, tab = "content") {
	let body;
	if (tab === "students")
		body = data.students.length
			? `<div class="teacher-queue">${data.students
					.map(
						(s) =>
							`<article class="assignment-row teacher-queue-row"><div><h3>${link(
								s.href,
								e(s.name),
								"student-link"
							)}</h3>${bar(s.progress)}${
								s.pending
									? `<span class="desk-status st-new">${t(
											"ui_244",
											s.pending
									  )}</span>`
									: ""
							}</div>${link(
								s.href,
								`${t("ui_234")}${icon("arrow")}`,
								"button secondary"
							)}</article>`
					)
					.join("")}</div>`
			: empty(t("ui_248"));
	else if (tab === "discussions")
		body = data.questions.length
			? `<div class="teacher-queue">${data.questions
					.map(questionRow)
					.join("")}</div>`
			: empty(t("ui_232"));
	else
		body = data.modules
			.map(
				(m, i) =>
					`<section class="module-block"><h2><span>${i + 1}</span>${e(
						m.title
					)}</h2><ol class="lesson-rows">${m.lessons
						.map(
							(l) =>
								`<li>${link(
									l.href,
									`<span class="lesson-name">${e(
										l.title
									)}</span><span class="lesson-badges">${
										l.pending
											? `<b class="warn">${t(
													"ui_244",
													l.pending
											  )}</b>`
											: ""
									}${
										l.questions
											? `<b class="warn">${t(
													"ui_245",
													l.questions
											  )}</b>`
											: ""
									}${
										l.comments
											? `<b>${t(
													"ui_246",
													l.comments
											  )}</b>`
											: ""
									}</span>`,
									"lesson-row"
								)}</li>`
						)
						.join("")}</ol></section>`
			)
			.join("");
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[null, data.title],
	])}${heading(t("ui_233"), data.title)}${tabs(data, tab)}${body}`;
}

export function teacherLessonView(data, drafts) {
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[courseHref(data.course, "discussions"), data.course_title],
		[null, data.title],
	])}${heading(t("ui_259", data.module), data.title)}${discussionView(
		data.discussion,
		drafts
	)}`;
}

const PROFILE_LABEL = {
	about: () => t("ui_358"),
	offer: () => t("ui_359"),
	strengths: () => t("ui_360"),
	help_needed: () => t("ui_361"),
	help_how: () => t("ui_362"),
	expertise: () => t("ui_363"),
};

function profileBlock(profile) {
	const rows = Object.values(profile || {})
		.flatMap((block) =>
			Object.keys(PROFILE_LABEL)
				.filter((f) => block[f])
				.map(
					(f) =>
						`<li><strong>${PROFILE_LABEL[f]()}</strong><p class="desk-quote">${plain(
							block[f]
						)}</p></li>`
				)
		)
		.join("");
	return rows
		? `<section class="desk-block"><div class="desk-head"><h2>${t("ui_356"
		  )}</h2></div><ul class="card-list">${rows}</ul></section>`
		: "";
}

export function teacherStudentView(card) {
	const rows = (items, render) =>
		items.length
			? `<ul class="card-list">${items.map(render).join("")}</ul>`
			: empty(t("ui_254"));
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[null, card.name],
	])}${heading(
		t("ui_260"),
		card.name
	)}<div class="desk-counters"><div class="desk-counter"><strong>${
		card.points
	}</strong><span>${t(
		"ui_249"
	)}</span></div><div class="desk-counter"><strong>${
		card.groups.length
	}</strong><span>${t(
		"ui_250"
	)}</span></div></div><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_253"
	)}</h2></div>${rows(
		card.courses,
		(c) => `<li><strong>${e(c.title)}</strong>${bar(c.progress)}</li>`
	)}</section><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_313"
	)}</h2></div>${rows(
		card.goals,
		(g) =>
			`<li><strong>${e(g.title)}</strong> <span class="help">${e(
				g.kind
			)}</span><div class="goal-bar"><progress max="100" value="${
				g.percent
			}">${g.percent}%</progress><strong>${
				g.percent
			}%</strong></div></li>`
	)}</section><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_314"
	)}</h2></div>${rows(
		card.reports,
		(r) =>
			`<li><span class="help">${day(r.date)}</span>${[
				r.goals_done,
				r.insights,
				r.tasks_done,
				r.suggestions,
			]
				.filter(Boolean)
				.map((x) => `<p class="desk-quote">${plain(x)}</p>`)
				.join("")}</li>`
	)}</section>${profileBlock(card.profile)}${
		card.groups.length
			? `<section class="desk-block"><div class="desk-head"><h2>${t(
					"ui_250"
			  )}</h2></div>${rows(
					card.groups,
					(g) =>
						`<li>${e(g.title)} <span class="help">${e(
							g.kind
						)}</span></li>`
			  )}</section>`
			: ""
	}<section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_251"
	)}</h2></div>${rows(
		card.submissions,
		(s) =>
			`<li>${link(
				s.href,
				e(s.assignment),
				"student-link"
			)} <span class="help">${e(s.course)} · ${when(
				s.created
			)}</span> <span class="desk-status st-${
				s.status === "Not Graded"
					? "new"
					: s.status === "Pass"
					? "ok"
					: "bad"
			}">${status(s.status)}</span></li>`
	)}</section><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_252"
	)}</h2></div>${rows(
		card.comments,
		(c) =>
			`<li>${link(
				c.href,
				e(c.lesson),
				"student-link"
			)} <span class="help">${e(c.course)} · ${when(c.when)}</span>${
				c.private
					? ` <span class="feed-tag priv">${t("ui_216")}</span>`
					: ""
			}${
				c.hidden
					? ` <span class="feed-tag off">${t("ui_176")}</span>`
					: ""
			}<p class="desk-quote">${plain(c.text)}</p></li>`
	)}</section>`;
}

const local = (v) => (v || "").replace(" ", "T").slice(0, 16);

function meetingForm(data, m) {
	const courses = data.courses
		.map(
			(c) =>
				`<option value="${e(c.id)}"${
					m && m.course === c.id ? " selected" : ""
				}>${e(c.title)}</option>`
		)
		.join("");
	return `<form class="goal-form" data-mm-form data-id="${e(
		m ? m.id : ""
	)}"><label>${t("ui_340")}<select name="course"${
		m ? " disabled" : ""
	}>${courses}</select></label><label>${t(
		"ui_341"
	)}<input type="text" name="title" maxlength="140" required value="${e(
		m ? m.title : ""
	)}"></label><label>${t(
		"ui_342"
	)}<input type="datetime-local" name="starts_at" required value="${e(
		m ? local(m.starts_at) : ""
	)}"></label><p class="help">${t("ui_331", e(data.tz))}</p><label>${t(
		"ui_343"
	)}<input type="text" name="link" maxlength="300" value="${e(
		m ? m.link : ""
	)}" placeholder="https://"></label><label>${t(
		"ui_344"
	)}<textarea name="topics" rows="4">${e(
		m ? m.topics.join("\n") : ""
	)}</textarea></label><label>${t(
		"ui_345"
	)}<textarea name="outcome" rows="3" maxlength="5000">${e(
		m ? m.outcome : ""
	)}</textarea></label><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_346"
	)}</button></form>`;
}

function attendance(data, m) {
	const people = data.participants[m.course] || [];
	const marked = new Set(
		m.people.filter((p) => p.attended).map((p) => p.member)
	);
	const going = new Set(m.people.filter((p) => p.going).map((p) => p.member));
	return people.length
		? `<form class="goal-form" data-attend-form data-id="${e(
				m.id
		  )}"><fieldset class="goal-steps"><legend>${t(
				"ui_347"
		  )}</legend>${people
				.map(
					(p) =>
						`<label class="feed-private"><input type="checkbox" name="member" value="${e(
							p.member
						)}"${marked.has(p.member) ? " checked" : ""}> ${e(
							p.name
						)}${
							going.has(p.member)
								? ` <span class="feed-tag priv">${t(
										"ui_336"
								  )}</span>`
								: ""
						}</label>`
				)
				.join(
					""
				)}</fieldset><div class="feed-error" role="alert"></div><button type="submit" class="button secondary">${t(
				"ui_348"
		  )}</button></form>`
		: `<p class="help">${t("ui_349")}</p>`;
}

function meetingRow(data, m) {
	return `<article class="goal-card meeting"><header><span class="feed-tag pin">${when(
		m.starts_at
	)}</span><span class="feed-tag priv">${t("ui_337", m.going_count)}</span>${
		m.past
			? `<span class="feed-tag staff">${t(
					"ui_352",
					m.people.filter((p) => p.attended).length
			  )}</span>`
			: ""
	}</header><h3>${e(m.title)}</h3><details class="goal-edit"><summary>${t(
		"ui_276"
	)}</summary>${meetingForm(data, m)}${attendance(
		data,
		m
	)}<button type="button" class="link-button danger" data-action="mm-delete" data-id="${e(
		m.id
	)}">${t("ui_350")}</button></details></article>`;
}

export function teacherMastermindsView(data) {
	const list = (items) => items.map((m) => meetingRow(data, m)).join("");
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[null, t("ui_326")],
	])}${heading(
		t("ui_354"),
		t("ui_326")
	)}<div class="desk-courses">${data.courses
		.map(
			(c) =>
				`<a class="desk-course" data-nav href="/school/teacher/super/${encodeURIComponent(
					c.id
				)}"><strong>${t("ui_319")} · ${e(c.title)}</strong>${icon(
					"arrow"
				)}</a>`
		)
		.join(
			""
		)}</div><section class="desk-block"><div class="desk-head"><h2>${t(
		"ui_339"
	)}</h2></div>${meetingForm(data, null)}</section>${
		data.upcoming.length
			? `<section class="desk-block"><div class="desk-head"><h2>${t(
					"ui_328"
			  )}</h2></div><div class="goal-list">${list(
					data.upcoming
			  )}</div></section>`
			: ""
	}${
		data.past.length
			? `<section class="desk-block"><div class="desk-head"><h2>${t(
					"ui_329"
			  )}</h2></div><div class="goal-list">${list(
					data.past
			  )}</div></section>`
			: ""
	}${
		data.upcoming.length || data.past.length
			? ""
			: `<p class="help">${t("ui_330")}</p>`
	}`;
}

export function teacherSuperView(data) {
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		["/school/teacher/masterminds", t("ui_326")],
		[null, t("ui_319")],
	])}${heading(t("ui_354"), t("ui_319"))}${superPosts(data)}`;
}
