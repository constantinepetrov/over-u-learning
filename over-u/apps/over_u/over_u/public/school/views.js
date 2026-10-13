import { boot, t } from "./i18n.js";
import { welcomeCard } from "./guide.js";
import {
	escape as e,
	icon,
	link,
	button,
	progress,
	outline,
	allLessons,
	kinds,
	richText,
} from "./components.js";
export function shell(content, home, section = "home") {
	// The real Frappe data/lesson screens stay unchanged; only the approved branded shell is new.
	const tabs = [
		["home", "/school", t("ui_001"), "home"],
		["book", "/school/learning", t("ui_002"), "learning"],
		["task", "/school/assignments", t("ui_003"), "assignments"],
		...(boot.teacher_tools
			? [["task", "/school/teacher", t("ui_151"), "teacher"]]
			: []),
		["results", "/school/results", t("ui_004"), "results"],
		["user", "/school/profile", t("ui_005"), "profile"],
	];
	const name = home?.user?.name || t("ui_006");
	const navLinks = tabs
		.map(([iconName, href, label, key]) => {
			const active = section === key;
			return link(
				href,
				`${icon(iconName)}<span>${label}</span>`,
				`ou-nav-item${active ? " active" : ""}`,
				active ? 'aria-current="page"' : ""
			);
		})
		.join("");
	// True course authoring is performed by Frappe Learning, never by mocked /school forms.
	const authorLink = boot.author_tools
		? '<a class="ou-nav-item" href="/lms" title="Открыть редактор Frappe Learning">Студия курсов</a>'
		: "";
	const mobileNav = tabs
		.filter(([, , , key]) => key !== "teacher")
		.map(([iconName, href, label, key]) => {
			const active = section === key;
			return link(
				href,
				`${icon(iconName)}<span>${label}</span>`,
				active ? "active" : "",
				active ? 'aria-current="page"' : ""
			);
		})
		.join("");
	const mobileAuthorLink = boot.author_tools
		? '<a href="/lms" class="ou-author-mobile" aria-label="Студия курсов">Студия</a>'
		: "";
	return `<div class="ou-shell">
    <header class="ou-header"><div class="ou-header-inner">
      <a class="ou-brand" href="/school" data-nav aria-label="OVER U — ${t(
			"ui_007"
		)}">
        <img src="/assets/over_u/school/assets/logo-orange.png" alt="" width="55" height="75">
        <span class="ou-brand-word"><strong>OVER U</strong><small>LIFELONG ENERGY</small></span>
      </a>
      <nav class="ou-header-nav" aria-label="${t(
			"ui_009"
		)}">${navLinks}${authorLink}</nav>
      <div class="ou-header-account"><button type="button" class="ou-help" data-action="guide" aria-label="Как это работает" title="Как это работает">?</button><span class="ou-profile-name">${e(
			name
		)}<small>${
		boot.author_tools ? "Автор / преподаватель" : t("ui_011")
	}</small></span>
        ${link(
			"/school/profile",
			e(name.slice(0, 1).toUpperCase()),
			"ou-account-avatar",
			'aria-label="Профиль"'
		)}
      </div>
    </div></header>
    <div class="ou-workspace">
      <main id="main" tabindex="-1">${content}</main>
      <footer class="ou-footer"><span>OVER U · Энерголетие / LIFELONG ENERGY</span><span>${t(
			"ui_014"
		)}</span></footer>
    </div>
    <nav class="ou-mobile-nav" aria-label="Мобильная навигация">${mobileNav}${mobileAuthorLink}</nav>
  </div>`;
}
function courseFeature(course) {
	const current = course.current;
	const pending =
		course.pending?.[0] ||
		(current?.assignment?.status === "Not Graded" ? current : null);
	const waiting = Boolean(pending);
	const actionHref = waiting ? pending.href || course.href : course.next_href;
	const actionLabel = waiting ? "Посмотреть статус задания" : t("ui_020");
	return `<article class="course-feature"><div class="course-feature-image"><img src="${e(
		course.image || "/assets/over_u/school/assets/course-cover.jpg"
	)}" alt="" loading="lazy"></div><div class="course-feature-content"><span class="eyebrow">${t(
		"ui_023"
	)}${course.chapters.length} ${t("ui_024")}</span><h2>${e(
		course.title
	)}</h2><p>${e(
		course.introduction
	)}</p><div class="next-step"><span class="tiny-label">${
		waiting ? t("ui_015") : current ? t("ui_016") : t("ui_017")
	}</span><strong>${
		waiting ? t("ui_018") : current ? e(current.title) : t("ui_019")
	}</strong></div>${link(
		actionHref,
		`${actionLabel}${icon("arrow")}`,
		"button primary"
	)}${
		waiting ? t("ui_021") : ""
	}</div><div class="course-feature-progress"><div class="progress-ring" role="img" aria-label="${t(
		"ui_025"
	)}${
		course.progress
	}%"><svg viewBox="0 0 160 160" aria-hidden="true"><circle class="ring-track" cx="80" cy="80" r="68"/><circle class="ring-value" cx="80" cy="80" r="68" pathLength="100" stroke-dasharray="${
		course.progress
	} 100"/></svg><span><strong>${
		course.progress
	}<small>%</small></strong><small>${t(
		"ui_026"
	)}</small></span></div>${progress(course)}${link(
		course.href,
		t("ui_022"),
		"text-link"
	)}</div></article>`;
}
function summaryCard(title, value, detail, href, iconName, tone = "") {
	return `<a class="summary-card ${tone}" href="${e(
		href
	)}" data-nav><span class="summary-icon">${icon(
		iconName
	)}</span><span class="summary-label">${title}</span><strong>${value}</strong><span class="summary-detail">${detail}</span></a>`;
}
function brandHero(course = null) {
	// Keep the progress badge attached to real enrollment data, never mock values.
	const value = course
		? Math.max(0, Math.min(100, Number(course.progress) || 0))
		: null;
	const progressBadge = course
		? `<div class="ou-hero-progress" role="progressbar" aria-label="Прогресс курса" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}">
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle class="ou-hero-ring-track" cx="50" cy="50" r="43" />
          <circle class="ou-hero-ring-fill" cx="50" cy="50" r="43" pathLength="100" stroke-dasharray="${value} 100" />
        </svg>
        <span><strong>${value}<small>%</small></strong><small>курса пройдено</small></span>
      </div>`
		: '<div class="ou-hero-note"><strong>Учитесь в своём ритме</strong></div>';
	return `<section class="ou-brand-hero" aria-labelledby="ou-hero-title">
    <div class="ou-brand-hero-copy">
      <span class="ou-eyebrow">Онлайн-школа OVER U</span>
      <h1 id="ou-hero-title">Энерголетие</h1>
      <span class="ou-tagline">LIFELONG ENERGY · BUSINESS HAPPINESS</span>
      <p>Пространство для развития, энергии и обучения на протяжении всей жизни.</p>
      ${link(
			"/school/learning",
			`Перейти к обучению ${icon("arrow")}`,
			"ou-brand-cta"
		)}
    </div>
    <div class="ou-brand-hero-image">
      <img src="/assets/over_u/school/assets/brand-hero.jpg" alt="Горный пейзаж на закате" width="720" height="480">
      ${progressBadge}
    </div>
  </section>`;
}

export function homeView(home) {
	const courses = home.courses;
	if (!courses.length)
		return `${brandHero()}${welcomeCard()}<div class="page-heading"><span class="eyebrow">${t(
			"ui_006"
		)}</span><h1>${t("ui_027")}</h1></div><section class="empty"><h2>${t(
			"ui_028"
		)}</h2><p>${t("ui_029")}</p></section>`;
	const course = courses.find((c) => c.current) || courses[0];
	const pending = courses.flatMap((c) => c.pending);
	const lessons = courses.flatMap(allLessons);
	const completed = lessons.filter((l) => l.complete);
	const activeCourses = courses.filter(
		(c) => c.total > 0 && c.completed < c.total
	);
	const openAssignments = lessons.filter(
		(l) =>
			l.kind === "assignment" &&
			!l.locked &&
			!l.complete &&
			l.assignment?.status !== "Not Graded"
	);
	const cards = `<section class="learning-summary" aria-label="${t(
		"ui_142"
	)}">${summaryCard(
		t("ui_143"),
		activeCourses.length,
		t("ui_144"),
		"/school/learning",
		"book",
		"summary-active"
	)}${summaryCard(
		t("ui_145"),
		openAssignments.length,
		t("ui_146"),
		openAssignments[0]?.href || "/school/assignments",
		"clock",
		"summary-upcoming"
	)}${summaryCard(
		t("ui_147"),
		completed.length,
		t("ui_148"),
		"/school/results",
		"check",
		"summary-complete"
	)}</section>`;
	return `${brandHero(
		course
	)}${welcomeCard()}<div class="page-heading"><div class="program-identity"><strong>${t(
		"ui_150"
	)}</strong><span>LIFELONG ENERGY · BUSINESS HAPPINESS</span></div><span class="eyebrow">${t(
		"ui_040"
	)}</span><h1>${t("ui_041")}${e(home.user.first_name)}.</h1><p>${t(
		"ui_042"
	)}</p></div>${courseFeature(
		course
	)}${cards}<div class="home-details"><section><div class="section-heading"><h2>${t(
		"ui_043"
	)}</h2>${link("/school/assignments", t("ui_030"), "text-link")}</div>${
		pending.length
			? pending
					.map(
						(l) =>
							`<article class="task-note"><span class="note-symbol">${icon(
								"clock"
							)}</span><div><span class="eyebrow">${t(
								"ui_032"
							)}</span><h3>${e(l.title)}</h3><p>${t(
								"ui_033"
							)}</p>${link(
								l.href,
								t("ui_031"),
								"text-link"
							)}</div></article>`
					)
					.join("")
			: openAssignments.length
			? openAssignments
					.slice(0, 2)
					.map(
						(l) =>
							`<article class="task-note task-open"><span class="note-symbol">${icon(
								"task"
							)}</span><div><span class="eyebrow">${t(
								"ui_145"
							)}</span><h3>${e(l.title)}</h3><p>${t(
								"ui_146"
							)}</p>${link(
								l.href,
								t("ui_031"),
								"text-link"
							)}</div></article>`
					)
					.join("")
			: `<article class="task-note"><span class="note-symbol">${icon(
					course.current ? "book" : "check"
			  )}</span><div><span class="eyebrow">${
					course.current ? t("ui_034") : t("ui_035")
			  }</span><h3>${
					course.current ? e(course.current.title) : t("ui_036")
			  }</h3><p>${
					course.current ? t("ui_037") : t("ui_038")
			  }</p></div></article>`
	}</section><section><div class="section-heading"><h2>${t(
		"ui_044"
	)}</h2><span class="tiny-label">${completed.length} ${t(
		"ui_045"
	)}${courses.reduce((n, c) => n + c.total, 0)}</span></div>${
		completed.length
			? `<ul class="completed-list">${completed
					.slice(-3)
					.reverse()
					.map(
						(l) =>
							`<li>${icon("check")} ${link(
								l.href,
								e(l.title)
							)}</li>`
					)
					.join("")}</ul>`
			: t("ui_039")
	}</section></div>`;
}
export function learningView(home) {
	return `<div class="page-heading"><span class="eyebrow">${t(
		"ui_047"
	)}</span><h1>${t("ui_048")}</h1><p>${t("ui_049")}</p></div>${
		home.courses.map(courseFeature).join("") || t("ui_046")
	}`;
}
export function courseView(course) {
	return `<div class="breadcrumbs">${link(
		"/school/learning",
		t("ui_002")
	)} ${icon("chevron")} <span>${t(
		"ui_051"
	)}</span></div><div class="course-heading"><div><span class="eyebrow">${
		course.chapters.length
	} ${t("ui_052")}${course.total} ${t("ui_053")}</span><h1>${e(
		course.title.replace(/^OVER U\s*[—–-]\s*/, "")
	)}</h1><p>${e(
		course.introduction
	)}</p></div><div class="course-summary">${progress(course)}${link(
		course.next_href,
		`${t("ui_020")}${icon("arrow")}`,
		"button primary"
	)}</div></div><div class="program-layout"><div class="program">${outline(
		course
	)}</div><aside class="program-note"><span class="note-symbol">${icon(
		"book"
	)}</span><h2>${t("ui_054")}</h2><p>${t("ui_055")}</p>${
		course.pending.length ? t("ui_050") : ""
	}</aside></div>`;
}
function contentBlocks(blocks) {
	return blocks
		.map((b) => {
			if (b.type === "header")
				return `<h${b.level}>${b.html}</h${b.level}>`;
			if (b.type === "paragraph")
				return `<div class="paragraph">${b.html}</div>`;
			if (b.type === "quote") return `<blockquote>${b.html}</blockquote>`;
			if (b.type === "video")
				return `<div class="video-wrap"><video controls preload="metadata" playsinline src="${e(
					b.url
				)}" aria-label="${t("ui_056")}"></video></div>`;
			if (b.type === "material")
				return `<div class="materials"><h2>${t(
					"ui_057"
				)}</h2><a href="${e(
					b.url
				)}" target="_blank" rel="noopener noreferrer">${icon(
					"book"
				)}${e(b.title)}</a></div>`;
			if (b.type === "divider") return "<hr>";
			return "";
		})
		.join("");
}
function fallback(data) {
	const url = `/lms/courses/${encodeURIComponent(data.course.id)}/learn/${
		data.lesson.number
	}`;
	return `<div class="inline-status"><p>${t("ui_058")}</p><a href="${e(
		url
	)}" class="text-link">${t("ui_059")}</a></div>`;
}
function quizView(data, drafts) {
	const q = data.quiz;
	if (q.unsupported || q.schedule_reason)
		return q.schedule_reason
			? `<div class="inline-status">${e(q.schedule_reason)}</div>`
			: fallback(data);
	const key = `${data.course.id}/${data.lesson.number}`;
	const result = q.result;
	const taking = !result || drafts.quizTaking.has(key);
	if (!taking)
		return `<section class="quiz-result ${
			result.passed ? "passed" : "not-passed"
		}" aria-label="${t("ui_066")}"><span class="result-symbol">${icon(
			result.passed ? "check" : "quiz"
		)}</span><span class="eyebrow">${t("ui_066")}</span><h2>${
			result.passed ? t("ui_060") : t("ui_061")
		}</h2><div class="score">${result.percentage}%</div><p>${
			result.score
		} ${t("ui_045")}${result.score_out_of} ${t("ui_067")}${
			q.threshold
		}%.</p><p>${result.passed ? t("ui_062") : t("ui_063")}</p>${
			q.can_retry
				? button(t("ui_064"), "quiz-retry", "button secondary")
				: t("ui_065")
		}</section>`;
	if (!q.can_retry) return t("ui_068");
	const saved = drafts.quizAnswers.get(key) || [];
	return `<form id="quiz-form" class="quiz-form"><div class="assessment-heading"><span class="eyebrow">${t(
		"ui_071"
	)}</span><h2>${e(q.title.replace(/^OVER U\s*[—–-]\s*/, ""))}</h2><p>${
		q.questions.length
	} ${t("ui_072")}${q.threshold}%${
		q.max_attempts
			? ` · ${t("ui_069")}${q.max_attempts - q.attempts}`
			: t("ui_070")
	}</p></div>${q.questions
		.map(
			(question, i) =>
				`<fieldset><legend><span class="question-number">${
					i + 1
				}</span>${e(
					question.prompt
				)}</legend><div class="answers">${question.options
					.map(
						(option, j) =>
							`<label class="answer-option"><input type="radio" name="question-${i}" value="${j}" ${
								saved[i] === j ? "checked" : ""
							} required><span>${e(
								richText(option)
							)}</span></label>`
					)
					.join("")}</div></fieldset>`
		)
		.join(
			""
		)}<div id="form-feedback" role="alert"></div><button class="button primary" type="submit">${t(
		"ui_073"
	)}${icon("arrow")}</button></form>`;
}
function homeworkView(data, drafts) {
	const a = data.assignment;
	if (a.type !== "Text") return fallback(data);
	const s = a.submission;
	const key = `${data.course.id}/${data.lesson.number}`;
	const passed = s?.status === "Pass";
	const pending = s?.status === "Not Graded";
	const failed = s?.status === "Fail";
	const editing = !s || failed || drafts.homeworkEditing.has(key);
	const answer = drafts.homeworkAnswers.get(key) ?? richText(s?.answer);
	const banner = passed
		? `<div class="homework-status passed" role="status">${icon(
				"check"
		  )}<div><strong>${t("ui_074")}</strong><p>${t(
				"ui_075"
		  )}</p></div></div>`
		: pending
		? `<div class="homework-status waiting" role="status">${icon(
				"clock"
		  )}<div><strong>${t("ui_032")}</strong><p>${t(
				"ui_076"
		  )}</p></div></div>`
		: failed
		? `<div class="homework-status revision" role="status">${icon(
				"task"
		  )}<div><strong>${t("ui_077")}</strong><p>${t(
				"ui_078"
		  )}</p></div></div>`
		: "";
	return `<section class="homework"><span class="eyebrow">${t(
		"ui_086"
	)}</span><h2>${e(
		a.title.replace(/^OVER U\s*[—–-]\s*/, "")
	)}</h2><div class="assignment-instructions">${
		a.instructions
	}</div>${banner}${
		s?.comments
			? `<div class="teacher-comment"><span class="eyebrow">${t(
					"ui_079"
			  )}</span><div>${s.comments}</div></div>`
			: ""
	}${
		a.schedule_reason
			? `<div class="inline-status">${e(a.schedule_reason)}</div>`
			: editing && !passed
			? `<form id="homework-form"><label for="homework-answer">${t(
					"ui_082"
			  )}</label><p id="answer-hint" class="help">${t(
					"ui_083"
			  )}</p><textarea id="homework-answer" name="answer" rows="6" maxlength="20000" required aria-describedby="answer-hint">${e(
					answer
			  )}</textarea><div id="form-feedback" role="alert"></div><button type="submit" class="button primary">${
					failed || s ? t("ui_080") : t("ui_081")
			  } ${icon("arrow")}</button></form>`
			: `<div class="submitted-answer"><span class="eyebrow">${t(
					"ui_082"
			  )}</span><div>${s?.answer || ""}</div></div>${
					!passed
						? button(
								t("ui_084"),
								"homework-edit",
								"button secondary"
						  )
						: ""
			  }`
	}${
		pending
			? button(
					`${icon("clock")} ${t("ui_085")}`,
					"refresh-status",
					"button quiet"
			  )
			: ""
	}</section>`;
}
export function lessonView(data, drafts) {
	const c = data.course,
		l = data.lesson;
	let article;
	if (data.locked)
		article = `<section class="locked-state"><span class="lock-symbol">${icon(
			"lock"
		)}</span><span class="eyebrow">${t("ui_088")}</span><h2>${t(
			"ui_089"
		)}</h2><p class="lock-reason">${e(data.lock_reason)}</p><p>${t(
			"ui_090"
		)}</p>${link(
			c.next_href,
			`${t("ui_087")}${icon("arrow")}`,
			"button primary"
		)}</section>`;
	else
		article = `<article class="reading"><div class="lesson-content">${contentBlocks(
			data.blocks
		)}${data.unsupported_content ? fallback(data) : ""}${
			data.quiz ? quizView(data, drafts) : ""
		}${
			data.assignment ? homeworkView(data, drafts) : ""
		}</div><div class="lesson-footer">${
			l.complete
				? `<span class="completed-mark">${icon("check")}${t(
						"ui_091"
				  )}</span>`
				: data.assignment
				? t("ui_092")
				: data.quiz
				? t("ui_093")
				: button(`${t("ui_094")}${icon("check")}`, "complete")
		} ${
			data.next
				? link(
						data.next.href,
						`${data.next.locked ? icon("lock") : ""}${
							data.next.locked ? t("ui_095") : t("ui_096")
						} ${icon("arrow")}`,
						"button secondary"
				  )
				: l.complete
				? link(c.href, t("ui_097"), "button secondary")
				: ""
		}</div><div id="action-feedback" role="alert"></div></article>`;
	return `<div class="breadcrumbs">${link(
		"/school/learning",
		t("ui_002")
	)} ${icon("chevron")} ${link(
		c.href,
		t("ui_051")
	)}</div><div class="learn-layout"><div class="learn-main"><div class="lesson-heading"><span class="eyebrow">${e(
		l.chapter_title
	)} · ${kinds[l.kind]}</span><h1>${e(
		l.title.replace(/^\d+\.\d+\s*/, "")
	)}</h1></div>${article}</div><aside class="learn-outline"><div class="outline-heading"><h2>${e(
		c.title.replace(/^OVER U\s*[—–-]\s*/, "")
	)}</h2>${progress(c)}</div>${outline(c, true, l.number)}</aside></div>`;
}
export function assignmentsView(home) {
	const lessons = home.courses
		.flatMap(allLessons)
		.filter((l) => l.kind === "assignment" && !l.locked);
	return `<div class="page-heading"><span class="eyebrow">${t(
		"ui_101"
	)}</span><h1>${t("ui_102")}</h1><p>${t("ui_103")}</p></div>${
		lessons.length
			? lessons
					.map(
						(l) =>
							`<article class="assignment-row"><div><span class="eyebrow">${
								l.assignment?.status === "Pass"
									? t("ui_074")
									: l.assignment?.status === "Not Graded"
									? t("ui_032")
									: l.assignment?.status === "Fail"
									? t("ui_077")
									: t("ui_098")
							}</span><h2>${e(l.title)}</h2></div>${link(
								l.href,
								`${t("ui_099")}${icon("arrow")}`,
								"button secondary"
							)}</article>`
					)
					.join("")
			: t("ui_100")
	}`;
}
export function resultsView(home) {
	const rows = home.courses.flatMap(allLessons).filter((l) => l.quiz_result);
	return `<div class="page-heading"><span class="eyebrow">${t(
		"ui_107"
	)}</span><h1>${t("ui_108")}</h1><p>${t("ui_109")}</p></div>${home.courses
		.map(
			(c) =>
				`<section class="result-course"><h2>${e(
					c.title
				)}</h2>${progress(c)}</section>`
		)
		.join("")}${
		rows
			.map(
				(l) =>
					`<article class="assignment-row"><div><span class="eyebrow">${
						l.quiz_result.passed ? t("ui_060") : t("ui_061")
					}</span><h2>${e(l.title)}</h2><p>${
						l.quiz_result.percentage
					}% · ${t("ui_105")}${
						l.quiz_result.threshold
					}%</p></div>${link(
						l.href,
						t("ui_104"),
						"text-link"
					)}</article>`
			)
			.join("") || t("ui_106")
	}`;
}
export function profileView(home) {
	return `<div class="page-heading"><span class="eyebrow">${t(
		"ui_011"
	)}</span><h1>${t(
		"ui_110"
	)}</h1></div><section class="profile-panel"><span class="avatar large">${e(
		home.user.name.slice(0, 1)
	)}</span><div><h2>${e(home.user.name)}</h2><p>${e(
		home.user.email
	)}</p><p class="help">${t(
		"ui_111"
	)}</p><button class="button secondary" data-action="logout">${t(
		"ui_149"
	)}</button><div id="logout-feedback" role="alert"></div></div></section><section class="profile-panel"><div><h2>Пароль и подсказки</h2><p class="help">Забыли пароль или хотите его сменить? Это можно сделать самостоятельно.</p><div class="profile-actions"><a class="button secondary" href="/update-password">Сменить пароль</a><button class="button secondary" type="button" data-action="guide">Как это работает</button></div></div></section>`;
}
export function teacherAssignmentsView(rows) {
	return `<div class="page-heading"><span class="eyebrow">${t(
		"ui_151"
	)}</span><h1>${t("ui_152")}</h1><p>${t("ui_153")}</p></div>${
		rows.length
			? `<div class="teacher-queue">${rows
					.map(
						(row) =>
							`<article class="assignment-row teacher-queue-row"><div><span class="eyebrow">${
								row.status === "Not Graded"
									? t("ui_032")
									: e(row.status)
							}</span><h2>${e(row.assignment)}</h2><p>${e(
								row.member
							)} · ${e(row.course)}</p><span class="help">${e(
								row.lesson
							)}</span></div>${link(
								row.href,
								`${t("ui_154")}${icon("arrow")}`,
								"button secondary"
							)}</article>`
					)
					.join("")}</div>`
			: `<section class="empty"><h2>${t("ui_155")}</h2><p>${t(
					"ui_156"
			  )}</p></section>`
	}`;
}
export function teacherAssignmentView(item) {
	return `<div class="breadcrumbs">${link(
		"/school/teacher",
		t("ui_151")
	)} ${icon("chevron")} <span>${t(
		"ui_157"
	)}</span></div><div class="page-heading"><span class="eyebrow">${e(
		item.course
	)}</span><h1>${e(item.assignment)}</h1><p>${e(item.lesson)} · ${e(
		item.member
	)}</p></div><section class="teacher-review"><div class="review-content"><span class="eyebrow">${t(
		"ui_158"
	)}</span><div class="review-answer">${
		item.answer || `<p>${t("ui_159")}</p>`
	}</div></div><details class="review-prompt"><summary>${t(
		"ui_160"
	)}</summary><div>${
		item.question || ""
	}</div></details><form id="teacher-review-form"><input type="hidden" name="submission" value="${e(
		item.name
	)}"><label for="review-status">${t(
		"ui_161"
	)}</label><select id="review-status" name="status" required><option value="">${t(
		"ui_162"
	)}</option><option value="Pass">${t(
		"ui_163"
	)}</option><option value="Fail">${t(
		"ui_164"
	)}</option></select><label for="review-comment">${t(
		"ui_165"
	)}</label><textarea id="review-comment" name="comments" maxlength="10000">${richText(
		item.comments
	)}</textarea><div id="form-feedback" role="alert"></div><div class="review-actions"><button type="submit" class="button primary">${t(
		"ui_166"
	)}</button>${link(
		"/school/teacher",
		t("ui_167"),
		"button secondary"
	)}</div></form></section>`;
}
export const loadingView = () => t("ui_112");
export function errorView(error) {
	return `<section class="empty" role="alert"><h1>${t("ui_114")}</h1><p>${e(
		error.message
	)}</p>${
		error.status === 401 ? t("ui_113") : button(t("ui_064"), "retry")
	}</section>`;
}
