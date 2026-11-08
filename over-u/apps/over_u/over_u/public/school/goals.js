import { t } from "./i18n.js";
import { escape as e, icon, link } from "./components.js";
import { plain, day, when } from "./community.js";

const pct = (n) => t("ui_316", n);
const bar = (n, label) =>
	`<div class="goal-bar"><progress max="100" value="${n}" aria-label="${e(
		label
	)} ${pct(n)}">${pct(n)}</progress><strong>${pct(n)}</strong></div>`;
const tabs = (tab) =>
	`<nav class="course-tabs" aria-label="${t("ui_262")}">${[
		["", t("ui_264"), "goals"],
		["report", t("ui_265"), "report"],
		["buddy", t("ui_266"), "buddy"],
		["profile", t("ui_355"), "profile"],
		["masterminds", t("ui_317"), "masterminds"],
		["super", t("ui_318"), "super"],
	]
		.map(
			([path, label, key]) =>
				`<a data-nav href="/school/goals${
					path ? "/" + path : ""
				}" class="${tab === key ? "on" : ""}"${
					tab === key ? ' aria-current="page"' : ""
				}>${label}</a>`
		)
		.join("")}</nav>`;
const heading = (title, lead) =>
	`<div class="page-heading"><span class="eyebrow">${t(
		"ui_262"
	)}</span><h1>${title}</h1><p>${lead}</p></div>`;

function stepRow(step = {}) {
	return `<div class="step-row"><input type="text" name="step_title" maxlength="140" value="${e(
		step.title || ""
	)}" placeholder="${t("ui_287")}" aria-label="${t(
		"ui_287"
	)}"><input type="date" name="step_due" value="${e(
		step.due || ""
	)}" aria-label="${t(
		"ui_288"
	)}"><label class="step-done"><input type="checkbox" name="step_done"${
		step.done ? " checked" : ""
	}> <span class="sr-only">${t("ui_289")}</span></label></div>`;
}

function goalForm(goal, kinds) {
	const kind = goal
		? `<input type="hidden" name="kind" value="${e(goal.kind)}">`
		: `<label for="goal-kind">${t(
				"ui_281"
		  )}</label><select id="goal-kind" name="kind">${kinds
				.map(
					(k) =>
						`<option value="${e(k)}">${
							k === "Основная" ? t("ui_269") : t("ui_270")
						}</option>`
				)
				.join("")}</select>`;
	const steps = goal && goal.steps.length ? goal.steps : [{}, {}];
	return `<form class="goal-form" data-goal-form data-goal="${e(
		goal ? goal.id : ""
	)}">${kind}<label>${t(
		"ui_282"
	)}<input type="text" name="title" maxlength="140" required value="${e(
		goal ? goal.title : ""
	)}"></label><label>${t(
		"ui_283"
	)}<textarea name="details" rows="2" maxlength="3000">${e(
		goal ? goal.details : ""
	)}</textarea></label><label>${t(
		"ui_284"
	)}<input type="date" name="target_date" value="${e(
		goal ? goal.target_date : ""
	)}"></label><fieldset class="goal-steps"><legend>${t(
		"ui_274"
	)}</legend><div class="step-rows">${steps
		.map(stepRow)
		.join(
			""
		)}</div><button type="button" class="link-button" data-action="goal-add-step">${t(
		"ui_290"
	)}</button></fieldset><label class="feed-private"><input type="checkbox" name="shared"${
		goal && goal.shared ? " checked" : ""
	}> ${t("ui_285")}</label><p class="help">${t(
		"ui_286"
	)}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_291"
	)}</button></form>`;
}
export const newStepRow = () => stepRow();

function goalCard(goal, kinds) {
	const steps = goal.steps.length
		? `<ul class="step-list">${goal.steps
				.map(
					(s, i) =>
						`<li class="${
							s.done ? "done" : ""
						}"><button type="button" class="step-check" data-action="step-toggle" data-goal="${e(
							goal.id
						)}" data-idx="${i}" data-done="${
							s.done ? 0 : 1
						}" aria-pressed="${s.done}">${
							s.done ? icon("check") : ""
						}</button><span>${e(s.title)}${
							s.due ? ` <small>${day(s.due)}</small>` : ""
						}</span></li>`
				)
				.join("")}</ul>`
		: `<p class="help">${t("ui_275")}</p>`;
	return `<article class="goal-card"><header><span class="feed-tag ${
		goal.kind === "Основная" ? "staff" : "pin"
	}">${
		goal.kind === "Основная" ? t("ui_269") : t("ui_270")
	}</span><span class="feed-tag ${goal.shared ? "priv" : "off"}">${
		goal.shared ? t("ui_272") : t("ui_273")
	}</span></header><h3>${e(goal.title)}</h3>${
		goal.details ? `<p>${plain(goal.details)}</p>` : ""
	}${
		goal.target_date
			? `<p class="help">${t("ui_271", day(goal.target_date))}</p>`
			: ""
	}${bar(
		goal.percent,
		goal.title
	)}${steps}<details class="goal-edit"><summary>${t(
		"ui_276"
	)}</summary>${goalForm(
		goal,
		kinds
	)}<button type="button" class="link-button danger" data-action="goal-delete" data-goal="${e(
		goal.id
	)}">${t(
		"ui_277"
	)}</button></details><button type="button" class="link-button" data-action="goal-history" data-goal="${e(
		goal.id
	)}">${t(
		"ui_444"
	)}</button><ul class="goal-history card-list" aria-live="polite"></ul></article>`;
}

export function historyList(items) {
	return items.length
		? items
				.map(
					(h) =>
						`<li><span class="help">${when(
							h.when
						)}</span> ${h.changes.map(e).join(", ")}</li>`
				)
				.join("")
		: `<li class="help">${t("ui_445")}</li>`;
}

export function goalsView(data) {
	const used = { Основная: 0, Дополнительная: 0 };
	data.goals.forEach((g) => (used[g.kind] += 1));
	const free = Object.keys(data.limits).filter(
		(k) => used[k] < data.limits[k]
	);
	return `${heading(t("ui_262"), t("ui_263"))}${tabs(
		"goals"
	)}<section class="goal-summary"><div><span class="eyebrow">${t(
		"ui_267"
	)}</span>${bar(data.percent, t("ui_267"))}<p class="help">${t(
		"ui_268"
	)}</p></div></section><div class="goal-list">${data.goals
		.map((g) => goalCard(g, free.concat([g.kind])))
		.join("")}</div>${
		free.length
			? `<section class="goal-new"><h2>${t("ui_279")}</h2>${goalForm(
					null,
					free
			  )}</section>`
			: `<p class="help">${t("ui_280")}</p>`
	}`;
}

export function reportView(data, drafts = {}) {
	const r = data.report || {};
	const field = (name, label) =>
		`<label>${label}<textarea name="${name}" rows="3" maxlength="3000">${e(
			r[name] || ""
		)}</textarea></label>`;
	const rule =
		data.rule && data.rule.enabled && data.rule.points
			? t("ui_302", data.rule.points)
			: t("ui_303");
	const history = data.history.length
		? `<div class="report-history">${data.history
				.map(
					(h) =>
						`<article class="goal-card"><h3>${day(h.date)}</h3>${[
							h.goals_done,
							h.insights,
							h.tasks_done,
							h.suggestions,
						]
							.filter(Boolean)
							.map((x) => `<p>${plain(x)}</p>`)
							.join("")}</article>`
				)
				.join("")}</div>`
		: `<p class="help">${t("ui_305")}</p>`;
	return `${heading(t("ui_293"), t("ui_294"))}${tabs(
		"report"
	)}<form class="goal-form report-form" data-report-form>${
		data.report ? `<p class="help ok">${t("ui_301")}</p>` : ""
	}${field("goals_done", t("ui_295"))}${field(
		"insights",
		t("ui_296")
	)}${field("tasks_done", t("ui_297"))}${field(
		"suggestions",
		t("ui_298")
	)}<p class="help">${t(
		"ui_306"
	)} ${rule}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${
		data.report ? t("ui_300") : t("ui_299")
	}</button></form><section class="goal-new"><h2>${t(
		"ui_304"
	)}</h2>${history}</section>`;
}

export function buddyView(data) {
	const b = data.buddy;
	const body = !b
		? `<p class="help">${t("ui_308")}</p>`
		: `<section class="goal-summary"><div><span class="eyebrow">${e(
				b.title
		  )}</span><h2>${e(b.name)}</h2>${bar(b.percent, b.name)}${
				b.points === null || data.points === null
					? ""
					: `<p class="help">${t(
							"ui_310",
							data.points,
							b.points
					  )}</p>`
		  }</div></section>${
				b.goals.length
					? `<div class="goal-list">${b.goals
							.map(
								(g) =>
									`<article class="goal-card"><header><span class="feed-tag ${
										g.kind === "Основная" ? "staff" : "pin"
									}">${
										g.kind === "Основная"
											? t("ui_269")
											: t("ui_270")
									}</span></header><h3>${e(g.title)}</h3>${
										g.target_date
											? `<p class="help">${t(
													"ui_271",
													day(g.target_date)
											  )}</p>`
											: ""
									}${bar(g.percent, g.title)}${
										g.steps.length
											? `<ul class="step-list readonly">${g.steps
													.map(
														(s) =>
															`<li class="${
																s.done
																	? "done"
																	: ""
															}"><span class="step-check static">${
																s.done
																	? icon(
																			"check"
																	  )
																	: ""
															}</span><span>${e(
																s.title
															)}</span></li>`
													)
													.join("")}</ul>`
											: ""
									}</article>`
							)
							.join("")}</div>`
					: `<p class="help">${t("ui_312")}</p>`
		  }${b.hidden ? `<p class="help">${t("ui_311", b.hidden)}</p>` : ""}`;
	return `${heading(t("ui_307"), t("ui_263"))}${tabs("buddy")}${body}${
		b ? buddyProfile(b.profile) : ""
	}`;
}

export function superPosts(data) {
	const post = (p) =>
		`<article class="feed-card${p.mine ? " is-mine" : ""}${
			p.hidden ? " is-hidden" : ""
		}"><span class="feed-avatar" aria-hidden="true">${e(
			p.initial
		)}</span><div class="feed-body"><header><strong>${e(
			p.author
		)}</strong><time>${when(p.when)}</time>${
			p.hidden ? `<span class="feed-tag off">${t("ui_176")}</span>` : ""
		}</header><p class="feed-text">${plain(p.text)}</p><footer>${
			p.cheers
				? `<span class="feed-tag priv">${t("ui_440", p.cheers)}</span>`
				: ""
		}${
			p.reports
				? `<span class="feed-tag off">${t("ui_443", p.reports)}</span>`
				: ""
		}${
			p.mine
				? ""
				: `<button type="button" class="link-button" data-action="super-mark" data-id="${e(
						p.id
				  )}" data-kind="Поддержка" data-on="${
						p.cheered ? 0 : 1
				  }" aria-pressed="${p.cheered}">${
						p.cheered ? t("ui_439") : t("ui_438")
				  }</button><button type="button" class="link-button" data-action="super-mark" data-id="${e(
						p.id
				  )}" data-kind="Жалоба" data-on="${
						p.reported ? 0 : 1
				  }" aria-pressed="${p.reported}">${
						p.reported ? t("ui_442") : t("ui_441")
				  }</button>`
		}${
			data.can_moderate
				? `<button type="button" class="link-button" data-action="super-moderate" data-id="${e(
						p.id
				  )}" data-mod="${p.hidden ? "unhide" : "hide"}">${
						p.hidden ? t("ui_180") : t("ui_179")
				  }</button>`
				: ""
		}${
			p.can_delete
				? `<button type="button" class="link-button" data-action="super-moderate" data-id="${e(
						p.id
				  )}" data-mod="delete">${t("ui_181")}</button>`
				: ""
		}</footer></div></article>`;
	return `<div class="feed-list super-list">${
		data.posts.length
			? data.posts.map(post).join("")
			: `<p class="feed-empty">${t("ui_323")}</p>`
	}</div>`;
}

export function superView(data) {
	const rule =
		data.rule && data.rule.enabled && data.rule.points
			? t("ui_324", data.rule.points)
			: t("ui_325");
	return `${heading(t("ui_319"), t("ui_320"))}${tabs(
		"super"
	)}<form class="goal-form" data-super-form><label>${t(
		"ui_321"
	)}<textarea name="text" rows="2" maxlength="300" required></textarea></label><p class="help">${rule}</p><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_322"
	)}</button></form>${superPosts(data)}`;
}

function meetingCard(m, own = true) {
	const topics = m.topics.length
		? `<h4>${t("ui_332")}</h4><ul class="topic-list">${m.topics
				.map((x) => `<li>${e(x)}</li>`)
				.join("")}</ul>`
		: "";
	const action = m.past
		? m.attended
			? `<span class="feed-tag staff">${t("ui_338")}</span>`
			: ""
		: `<button type="button" class="button ${
				m.going ? "primary" : "secondary"
		  }" data-action="mm-going" data-id="${e(m.id)}" data-going="${
				m.going ? 0 : 1
		  }" aria-pressed="${m.going}">${
				m.going ? t("ui_336") : t("ui_335")
		  }</button>`;
	return `<article class="goal-card meeting"><header><span class="feed-tag pin">${when(
		m.starts_at
	)}</span>${
		m.going_count && !m.past
			? `<span class="feed-tag priv">${t("ui_337", m.going_count)}</span>`
			: ""
	}</header><h3>${e(m.title)}</h3>${topics}${
		m.link
			? `<p><a class="button quiet" href="${e(
					m.link
			  )}" target="_blank" rel="noopener noreferrer">${t(
					"ui_333"
			  )}</a></p>`
			: ""
	}${
		m.outcome ? `<h4>${t("ui_334")}</h4><p>${plain(m.outcome)}</p>` : ""
	}<div class="meeting-actions">${action}</div></article>`;
}

export function mastermindsView(data) {
	const block = (title, items) =>
		items.length
			? `<section class="goal-new"><h2>${title}</h2><div class="goal-list">${items
					.map((m) => meetingCard(m))
					.join("")}</div></section>`
			: "";
	return `${heading(t("ui_326"), t("ui_327"))}${tabs(
		"masterminds"
	)}<p class="help">${t("ui_331", e(data.tz))}</p>${
		data.upcoming.length || data.past.length
			? block(t("ui_328"), data.upcoming) + block(t("ui_329"), data.past)
			: `<p class="help">${t("ui_330")}</p>`
	}`;
}

const PROFILE = [
	["about", ["about"]],
	["offer", ["offer"]],
	["strengths", ["strengths"]],
	["help", ["help_needed", "help_how"]],
	["expertise", ["expertise"]],
];
const FIELD_LABEL = {
	about: () => t("ui_358"),
	offer: () => t("ui_359"),
	strengths: () => t("ui_360"),
	help_needed: () => t("ui_361"),
	help_how: () => t("ui_362"),
	expertise: () => t("ui_363"),
};

function buddyProfile(profile) {
	const rows = PROFILE.filter(([block]) => profile && profile[block])
		.flatMap(([block, fields]) =>
			fields
				.filter((f) => profile[block][f])
				.map(
					(f) =>
						`<li><strong>${FIELD_LABEL[f]()}</strong><p>${e(
							profile[block][f]
						)}</p></li>`
				)
		)
		.join("");
	return rows
		? `<section class="goal-summary"><div><h2>${t(
				"ui_366"
		  )}</h2><ul class="card-list">${rows}</ul></div></section>`
		: "";
}

export function helpProfileView(data) {
	const blocks = PROFILE.map(
		([block, fields]) =>
			`<fieldset class="goal-steps">${fields
				.map(
					(f) =>
						`<label>${FIELD_LABEL[
							f
						]()}<textarea name="${block}__${f}" rows="3" maxlength="1500">${e(
							data.profile[block][f]
						)}</textarea></label>`
				)
				.join(
					""
				)}<label class="feed-private"><input type="checkbox" name="${block}__shared"${
				data.profile[block].shared ? " checked" : ""
			}> ${t("ui_364")}</label></fieldset>`
	).join("");
	return `${heading(t("ui_356"), t("ui_357"))}${tabs(
		"profile"
	)}<form class="goal-form" data-profile-form>${blocks}<div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_365"
	)}</button></form>`;
}
