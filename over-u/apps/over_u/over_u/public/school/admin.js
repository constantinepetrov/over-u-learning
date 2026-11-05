import { t } from "./i18n.js";
import { escape as e } from "./components.js";
import { when } from "./community.js";
import { crumbs, heading } from "./teacher.js";

const nav = (items) =>
	crumbs([["/school/teacher", t("ui_151")], [null, items]]);

function groupForm(course, g) {
	const picked = new Set((g ? g.members : []).map((m) => m.member));
	return `<form class="goal-form" data-group-form data-course="${e(
		course.id
	)}" data-id="${e(g ? g.id : "")}"><label>${t("ui_372"
	)}<select name="kind"><option value="Бадди"${
		g && g.kind === "Бадди" ? " selected" : ""
	}>${t("ui_373")}</option><option value="Команда"${
		g && g.kind === "Команда" ? " selected" : ""
	}>${t("ui_374")}</option></select></label><label>${t("ui_375"
	)}<input type="text" name="title" maxlength="100" required value="${e(
		g ? g.title : ""
	)}"></label>${
		course.participants.length
			? `<fieldset class="goal-steps"><legend>${t("ui_376"
			  )}</legend>${course.participants
					.map(
						(p) =>
							`<label class="feed-private"><input type="checkbox" name="member" value="${e(
								p.member
							)}"${picked.has(p.member) ? " checked" : ""}> ${e(
								p.name
							)}</label>`
					)
					.join("")}</fieldset>`
			: `<p class="help">${t("ui_382")}</p>`
	}<p class="help">${t("ui_377"
	)}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t("ui_378"
	)}</button></form>`;
}

export function teacherGroupsView(data) {
	return `${nav(t("ui_367"))}${heading(
		t("ui_367"),
		t("ui_367"),
		t("ui_368")
	)}${data.courses
		.map((c) => {
			const own = data.groups.filter((g) => g.course === c.id);
			return `<section class="desk-block"><div class="desk-head"><h2>${e(
				c.title
			)}</h2></div>${
				own.length
					? `<div class="goal-list">${own
							.map(
								(g) =>
									`<article class="goal-card"><header><span class="feed-tag ${
										g.kind === "Бадди" ? "pin" : "staff"
									}">${
										g.kind === "Бадди"
											? t("ui_373")
											: t("ui_374")
									}</span></header><h3>${e(
										g.title
									)}</h3><p class="help">${g.members
										.map((m) => e(m.name))
										.join(
											", "
										)}</p><details class="goal-edit"><summary>${t(
										"ui_276"
									)}</summary>${groupForm(
										c,
										g
									)}<button type="button" class="link-button danger" data-action="group-delete" data-id="${e(
										g.id
									)}">${t("ui_379")}</button></details></article>`
							)
							.join("")}</div>`
					: `<p class="help">${t("ui_381")}</p>`
			}<details class="goal-edit"><summary>${t("ui_371"
			)}</summary>${groupForm(c, null)}</details></section>`;
		})
		.join("")}`;
}

function ruleRow(r) {
	return `<form class="goal-form rule-row" data-rule-form data-event="${e(
		r.event
	)}"><h3>${e(r.label)}</h3><p class="help">${t("ui_393",
		r.last30
	)}</p><label>${t("ui_388"
	)}<input type="number" name="points" min="0" max="1000" required value="${
		r.points
	}"></label><label>${t("ui_390"
	)}<input type="number" name="daily_limit" min="0" max="100" value="${
		r.daily_limit
	}"></label><label class="feed-private"><input type="checkbox" name="enabled"${
		r.enabled ? " checked" : ""
	}> ${t("ui_389"
	)}</label><p class="help preview-out" aria-live="polite"></p><div class="feed-error" role="alert"></div><div class="row-actions"><button type="button" class="button secondary" data-action="rule-preview">${t("ui_391"
	)}</button><button type="submit" class="button primary">${t("ui_392"
	)}</button></div></form>`;
}

export function teacherPointsView(data) {
	const b = data.board;
	const sel = (v) => (b.visibility === v ? " selected" : "");
	return `${nav(t("ui_383"))}${heading(
		t("ui_383"),
		t("ui_383"),
		t("ui_384")
	)}<section class="desk-block"><div class="desk-head"><h2>${t("ui_387"
	)}</h2></div><div class="goal-list">${data.rules
		.map(ruleRow)
		.join(
			""
		)}</div></section><section class="desk-block"><div class="desk-head"><h2>${t("ui_395"
	)}</h2></div><form class="goal-form" data-board-form><label class="feed-private"><input type="checkbox" name="enabled"${
		b.enabled ? " checked" : ""
	}> ${t("ui_396")}</label><label>${t("ui_397"
	)}<select name="visibility"><option value="Все ученики видят табло"${sel(
		"Все ученики видят табло"
	)}>${t("ui_398"
	)}</option><option value="Ученик видит только свой результат"${sel(
		"Ученик видит только свой результат"
	)}>${t("ui_399")}</option></select></label><label>${t("ui_400"
	)}<input type="number" name="limit" min="3" max="50" value="${
		b.limit
	}"></label><label>${t("ui_401"
	)}<textarea name="prizes" rows="4" maxlength="3000">${e(
		data.prizes
	)}</textarea></label><p class="help">${t("ui_402"
	)}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t("ui_403"
	)}</button></form></section><section class="desk-block"><div class="desk-head"><h2>${t("ui_404"
	)}</h2></div>${
		data.participants.length
			? `<form class="goal-form" data-bonus-form><label>${t("ui_405"
			  )}<select name="member">${data.participants
					.map(
						(p) =>
							`<option value="${e(p.member)}" data-course="${e(
								p.course
							)}">${e(p.name)}</option>`
					)
					.join("")}</select></label><label>${t("ui_406"
			  )}<input type="number" name="value" min="1" max="1000" required></label><label>${t("ui_407"
			  )}<input type="text" name="reason" maxlength="140" required></label><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t("ui_408"
			  )}</button></form>`
			: `<p class="help">${t("ui_382")}</p>`
	}</section><section class="desk-block"><div class="desk-head"><h2>${t("ui_409"
	)}</h2></div>${
		data.journal.length
			? `<ul class="card-list">${data.journal
					.map(
						(j) =>
							`<li><strong>${j.points > 0 ? "+" : ""}${
								j.points
							}</strong> ${e(j.name)} <span class="help">${e(
								j.reason
							)} · ${when(j.when)}</span></li>`
					)
					.join("")}</ul>`
			: `<p class="help">${t("ui_411")}</p>`
	}</section>`;
}
