import { t } from "./i18n.js";
import { escape as e, icon } from "./components.js";
import { when, plain } from "./community.js";

function tools(message, can, root) {
	const buttons = [];
	if (can.moderate && root)
		buttons.push([
			message.pinned ? t("ui_178") : t("ui_177"),
			message.pinned ? "unpin" : "pin",
		]);
	if (can.moderate)
		buttons.push([
			message.hidden ? t("ui_180") : t("ui_179"),
			message.hidden ? "unhide" : "hide",
		]);
	if (message.can_delete) buttons.push([t("ui_181"), "delete"]);
	return buttons.length
		? `<span class="feed-tools">${buttons
				.map(
					([label, action]) =>
						`<button type="button" class="link-button" data-action="disc-moderate" data-id="${e(
							message.id
						)}" data-mod="${action}">${label}</button>`
				)
				.join("")}</span>`
		: "";
}

function card(message, disc, drafts, reply = false) {
	const flags = `${
		message.staff
			? `<span class="feed-tag staff">${t("ui_215")}</span>`
			: ""
	}${
		message.private
			? `<span class="feed-tag priv">${t("ui_216")}</span>`
			: ""
	}${
		message.pinned ? `<span class="feed-tag pin">${t("ui_175")}</span>` : ""
	}${
		message.hidden ? `<span class="feed-tag off">${t("ui_176")}</span>` : ""
	}`;
	const form = reply
		? ""
		: `<form class="feed-form reply" data-disc-form data-reply="${e(
				message.id
		  )}"><input type="text" name="text" maxlength="2000" placeholder="${t(
				"ui_185"
		  )}" aria-label="${t("ui_185")}" data-draft="d:reply:${e(
				message.id
		  )}" value="${e(
				drafts.feedText.get("d:reply:" + message.id) || ""
		  )}"><button type="submit" class="button quiet">${t(
				"ui_174"
		  )}</button></form>`;
	return `<article class="feed-card${reply ? " is-reply" : ""}${
		message.mine ? " is-mine" : ""
	}${message.staff ? " is-staff" : ""}${
		message.hidden ? " is-hidden" : ""
	}"><span class="feed-avatar" aria-hidden="true">${e(
		message.initial
	)}</span><div class="feed-body"><header><strong>${e(message.author)}${
		message.mine ? ` <small>${t("ui_200")}</small>` : ""
	}</strong><time>${when(
		message.when
	)}</time>${flags}</header><p class="feed-text">${plain(
		message.text
	)}</p><footer>${tools(
		message,
		{ moderate: disc.can_moderate },
		!reply
	)}</footer>${(message.replies || [])
		.map((r) => card(r, disc, drafts, true))
		.join("")}${form}</div></article>`;
}

export function discussionView(disc, drafts) {
	if (!disc || disc.enabled === false) return "";
	const list = disc.messages.length
		? disc.messages.map((m) => card(m, disc, drafts)).join("")
		: `<p class="feed-empty">${t("ui_211")}</p>`;
	const privateBox = disc.can_moderate
		? ""
		: `<label class="feed-private"><input type="checkbox" name="private" value="1"> ${t(
				"ui_214"
		  )}</label>`;
	return `<section class="feed discussion" id="discussion" aria-label="${t(
		"ui_209"
	)}"><h2>${t("ui_209")}</h2><p>${t(
		"ui_210"
	)}</p><div class="feed-list">${list}</div><form class="feed-form main" data-disc-form><label for="disc-text">${t(
		"ui_212"
	)}</label><textarea id="disc-text" name="text" rows="3" maxlength="2000" required data-draft="d:main">${e(
		drafts.feedText.get("d:main") || ""
	)}</textarea>${privateBox}<div class="feed-error" role="alert"></div><button type="submit" class="button primary">${t(
		"ui_213"
	)} ${icon("arrow")}</button></form></section>`;
}
