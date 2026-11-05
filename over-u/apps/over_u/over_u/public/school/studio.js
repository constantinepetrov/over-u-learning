import { t } from "./i18n.js";
import { escape as e, icon, link } from "./components.js";
import { crumbs, heading } from "./teacher.js";

function lessonForm(course, module, lesson) {
	const l = lesson || {};
	return `<form class="goal-form" data-studio-lesson data-course="${e(
		course
	)}" data-chapter="${e(module)}" data-id="${e(l.id || "")}"><label>${t("ui_425"
	)}<input type="text" name="title" maxlength="140" required value="${e(
		l.title || ""
	)}"></label><label>${t("ui_426"
	)}<textarea name="text" rows="10" maxlength="30000" required>${e(
		l.text || ""
	)}</textarea></label><p class="help">${t("ui_427"
	)}</p><label>${t("ui_428"
	)}<textarea name="homework" rows="4" maxlength="5000">${e(
		l.task || ""
	)}</textarea></label><p class="help">${t("ui_429"
	)}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t("ui_430"
	)}</button></form>`;
}

const mover = (kind, id) =>
	`<span class="row-actions"><button type="button" class="link-button" data-action="studio-move" data-kind="${kind}" data-id="${e(
		id
	)}" data-dir="up">${t("ui_431"
	)}</button><button type="button" class="link-button" data-action="studio-move" data-kind="${kind}" data-id="${e(
		id
	)}" data-dir="down">${t("ui_432")}</button></span>`;

function lessonRow(course, module, l) {
	const body = l.editable
		? lessonForm(course, module.id, l)
		: `<p class="help">${t("ui_434")}</p><a class="button secondary" href="/app/course-lesson/${encodeURIComponent(
				l.id
		  )}">${t("ui_435")}</a>`;
	return `<li class="goal-card"><header><strong>${e(l.title)}</strong>${
		l.homework
			? `<span class="feed-tag pin">${t("ui_436")}</span>`
			: ""
	}</header><div class="row-actions">${mover(
		"lesson",
		l.id
	)}${link(
		`/school/teacher/courses/${encodeURIComponent(
			course
		)}/lessons/${l.number}`,
		`${t("ui_433")}${icon("arrow")}`,
		"text-link"
	)}</div><details class="goal-edit"><summary>${t(
		"ui_276"
	)}</summary>${body}</details></li>`;
}

export function studioView(data) {
	const total = data.modules.length;
	return `${crumbs([
		["/school/teacher", t("ui_151")],
		[null, t("ui_413")],
	])}${heading(
		data.title,
		t("ui_413"),
		t("ui_414")
	)}<section class="desk-block"><p><strong>${
		data.published ? t("ui_415") : t("ui_416")
	}</strong> · ${t("ui_420",
		data.ready,
		total
	)}</p><button type="button" class="button ${
		data.published ? "secondary" : "primary"
	}" data-action="studio-publish" data-course="${e(
		data.course
	)}" data-publish="${data.published ? 0 : 1}">${
		data.published ? t("ui_418") : t("ui_417")
	}</button><div class="feed-error" role="alert"></div></section>${
		total
			? data.modules
					.map(
						(m, i) =>
							`<section class="desk-block"><div class="desk-head"><h2><span>${
								i + 1
							}</span> ${e(m.title)}</h2>${mover(
								"module",
								m.id
							)}</div>${
								m.lessons.length
									? `<ol class="goal-list">${m.lessons
											.map((l) =>
												lessonRow(data.course, m, l)
											)
											.join("")}</ol>`
									: `<p class="help">${t("ui_421")}</p>`
							}<details class="goal-edit"><summary>${t("ui_424"
							)}</summary>${lessonForm(
								data.course,
								m.id,
								null
							)}</details><details class="goal-edit"><summary>${t(
								"ui_276"
							)} · ${t("ui_422"
							)}</summary><form class="goal-form" data-studio-module data-course="${e(
								data.course
							)}" data-id="${e(
								m.id
							)}"><label>${t("ui_422"
							)}<input type="text" name="title" maxlength="140" required value="${e(
								m.title
							)}"></label><div class="feed-error" role="alert"></div><button type="submit" class="button secondary">${t("ui_430"
							)}</button></form></details></section>`
					)
					.join("")
			: `<p class="help">${t("ui_437")}</p>`
	}<section class="desk-block"><div class="desk-head"><h2>${t("ui_423"
	)}</h2></div><form class="goal-form" data-studio-module data-course="${e(
		data.course
	)}" data-id=""><label>${t("ui_422"
	)}<input type="text" name="title" maxlength="140" required></label><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t("ui_423"
	)}</button></form></section>`;
}
