import { t, language } from "./i18n.js";
import { escape as e, icon } from "./components.js";
const locale = language === "ru" ? "ru-RU" : "en-GB";
export const when = (value) => {
	const date = new Date(String(value).replace(" ", "T"));
	return Number.isNaN(date.getTime())
		? ""
		: date.toLocaleString(locale, {
				day: "numeric",
				month: "short",
				hour: "2-digit",
				minute: "2-digit",
		  });
};
export const day = (iso) => {
	const date = new Date(`${iso}T00:00:00`);
	return Number.isNaN(date.getTime())
		? ""
		: date.toLocaleDateString(locale, { day: "numeric", month: "long" });
};
export const plain = (text) => e(text).replace(/\n/g, "<br>");
const pts = (value) => t("ui_201", value);

function reactions(message, labels) {
	return `<div class="feed-reactions">${Object.keys(labels)
		.map((kind) => {
			const r = message.reactions[kind];
			const label = `${kind === "like" ? t("ui_183") : t("ui_184")}${
				r.count ? ` · ${r.count}` : ""
			}`;
			return message.mine
				? r.count
					? `<span class="react static">${label}</span>`
					: ""
				: `<button type="button" class="react${
						r.me ? " on" : ""
				  }" data-action="feed-react" data-id="${e(
						message.id
				  )}" data-kind="${kind}" aria-pressed="${
						r.me
				  }">${label}</button>`;
		})
		.join("")}</div>`;
}
function tools(message, can, root) {
	const buttons = [];
	if (can.moderate && root)
		buttons.push([
			"pin",
			message.pinned ? t("ui_178") : t("ui_177"),
			message.pinned ? "unpin" : "pin",
		]);
	if (can.moderate)
		buttons.push([
			"hide",
			message.hidden ? t("ui_180") : t("ui_179"),
			message.hidden ? "unhide" : "hide",
		]);
	if (message.can_delete && message.kind === "Comment")
		buttons.push(["delete", t("ui_181"), "delete"]);
	return buttons.length
		? `<span class="feed-tools">${buttons
				.map(
					([, label, action]) =>
						`<button type="button" class="link-button" data-action="feed-moderate" data-id="${e(
							message.id
						)}" data-mod="${action}">${label}</button>`
				)
				.join("")}</span>`
		: "";
}
function card(message, feed, drafts, reply = false) {
	const body =
		message.kind === "Answer"
			? `<div class="feed-answer">${message.html}</div>`
			: `<p class="feed-text">${plain(message.text)}</p>`;
	const flags = `${
		message.kind === "Answer"
			? `<span class="feed-tag">${t("ui_182")}</span>`
			: ""
	}${
		message.pinned ? `<span class="feed-tag pin">${t("ui_175")}</span>` : ""
	}${
		message.hidden ? `<span class="feed-tag off">${t("ui_176")}</span>` : ""
	}`;
	const form = reply
		? ""
		: `<form class="feed-form reply" data-feed-form data-reply="${e(
				message.id
		  )}"><input type="text" name="text" maxlength="2000" placeholder="${t(
				"ui_185"
		  )}" aria-label="${t("ui_185")}" data-draft="reply:${e(
				message.id
		  )}" value="${e(
				drafts.feedText.get("reply:" + message.id) || ""
		  )}"><button type="submit" class="button quiet">${t(
				"ui_174"
		  )}</button></form>`;
	return `<article class="feed-card${reply ? " is-reply" : ""}${
		message.mine ? " is-mine" : ""
	}${
		message.hidden ? " is-hidden" : ""
	}"><span class="feed-avatar" aria-hidden="true">${e(
		message.initial
	)}</span><div class="feed-body"><header><strong>${e(message.author)}${
		message.mine ? ` <small>${t("ui_200")}</small>` : ""
	}</strong><time>${when(
		message.when
	)}</time>${flags}</header>${body}<footer>${reactions(
		message,
		feed.reactions
	)}${tools(message, { moderate: feed.can_moderate }, !reply)}</footer>${(
		message.replies || []
	)
		.map((r) => card(r, feed, drafts, true))
		.join("")}${form}</div></article>`;
}
export function feedView(feed, drafts) {
	if (!feed || feed.enabled === false) return "";
	if (!feed.unlocked)
		return `<section class="feed feed-locked" aria-label="${t(
			"ui_168"
		)}"><h2>${t("ui_168")}</h2><p>${t("ui_170")}</p>${
			feed.others
				? `<p class="feed-count">${t("ui_208", feed.others)}</p>`
				: ""
		}</section>`;
	const list = feed.messages.length
		? feed.messages.map((m) => card(m, feed, drafts)).join("")
		: `<p class="feed-empty">${t("ui_171")}</p>`;
	return `<section class="feed" id="feed" aria-label="${t("ui_168")}"><h2>${t(
		"ui_168"
	)}</h2><p>${t(
		"ui_169"
	)}</p><div class="feed-list">${list}</div><form class="feed-form main" data-feed-form><label for="feed-text">${t(
		"ui_172"
	)}</label><textarea id="feed-text" name="text" rows="3" maxlength="2000" required data-draft="main">${e(
		drafts.feedText.get("main") || ""
	)}</textarea><div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_173"
	)} ${icon("arrow")}</button></form></section>`;
}

const rank = (n) =>
	`<span class="rank${n <= 3 ? " medal m" + n : ""}">${n}</span>`;
export function ratingView(data, period) {
	const head = `<div class="page-heading"><span class="eyebrow">${t(
		"ui_187"
	)}</span><h1>${t("ui_186")}</h1></div>`;
	if (!data || data.enabled === false) return `${head}<p>${t("ui_199")}</p>`;
	const toggle = `<div class="period" role="group" aria-label="${t(
		"ui_186"
	)}"><button type="button" class="${
		period === "all" ? "on" : ""
	}" data-action="rating-period" data-period="all" aria-pressed="${
		period === "all"
	}">${t("ui_192")}</button><button type="button" class="${
		period === "week" ? "on" : ""
	}" data-action="rating-period" data-period="week" aria-pressed="${
		period === "week"
	}">${t("ui_191")}</button></div>`;
	const stats = `<div class="rating-stats"><div><span>${t(
		"ui_188"
	)}</span><strong>${data.me.points}</strong></div><div><span>${t(
		"ui_189"
	)}</span><strong>${data.me.rank}<small> ${t("ui_190")} ${
		data.me.of
	}</small></strong></div></div>`;
	const board = `<section class="rating-block"><h2>${t("ui_193")}</h2>${
		data.top.length
			? `<ol class="board">${data.top
					.map(
						(r) =>
							`<li class="${r.me ? "me" : ""}">${rank(
								r.rank
							)}<span class="who">${e(r.name)}${
								r.me ? ` <small>${t("ui_200")}</small>` : ""
							}</span><strong>${pts(r.points)}</strong></li>`
					)
					.join("")}</ol>`
			: `<p>${t("ui_202")}</p>`
	}</section>`;
	const groupBlock = (kind, title) => {
		const rows = data.groups.filter((g) => g.kind === kind);
		return rows.length
			? `<section class="rating-block"><h2>${title}</h2><ol class="board">${rows
					.map(
						(g) =>
							`<li class="${g.mine ? "me" : ""}">${rank(
								g.rank
							)}<span class="who">${e(
								g.title
							)}<small class="members">${t(
								"ui_207",
								e(g.members.join(", "))
							)}</small></span><strong>${pts(
								g.points
							)}</strong></li>`
					)
					.join("")}</ol></section>`
			: "";
	};
	const groups =
		groupBlock("Бадди", t("ui_194")) + groupBlock("Команда", t("ui_195")) ||
		`<p class="help">${t("ui_206")}</p>`;
	const rules = data.rules.length
		? `<section class="rating-block"><h2>${t(
				"ui_196"
		  )}</h2><ul class="rules">${data.rules
				.map(
					(r) =>
						`<li><span>${e(r.label)}${
							r.daily_limit
								? `<small> · ${t(
										"ui_203",
										r.daily_limit
								  )}</small>`
								: ""
						}</span><strong>+${r.points}</strong></li>`
				)
				.join("")}</ul></section>`
		: "";
	const recent = `<section class="rating-block"><h2>${t("ui_197")}</h2>${
		data.recent.length
			? `<ul class="rules">${data.recent
					.map(
						(r) =>
							`<li><span>${e(r.reason)}<small> · ${when(
								r.when
							)}</small></span><strong>${
								r.points > 0 ? "+" : ""
							}${r.points}</strong></li>`
					)
					.join("")}</ul>`
			: `<p>${t("ui_198")}</p>`
	}</section>`;
	return `${head}${toggle}${stats}<div class="rating-grid"><div>${board}${groups}</div><div>${rules}${recent}</div></div>`;
}
