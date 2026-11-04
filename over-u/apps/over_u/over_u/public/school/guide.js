// Student guide: an inline welcome card on the home page and a help dialog.
// Self-contained on purpose: it never blocks the page on first load.
import { escape as e } from "./components.js";
import { boot } from "./i18n.js";

const STORAGE_KEY = "ou_guide_dismissed_v1";

export const GUIDE_STEPS = [
	{
		title: "Начните с главной",
		text: "Здесь виден ваш следующий шаг и общий прогресс. Нажмите «Продолжить обучение», чтобы открыть нужный урок.",
	},
	{
		title: "Идите по порядку",
		text: "В разделе «Обучение» вся программа: модули и уроки. Урок со значком замка откроется, когда вы завершите предыдущий.",
	},
	{
		title: "Завершайте уроки",
		text: "Прочитали или посмотрели материал? Нажмите «Завершить урок», тогда откроется следующий.",
	},
	{
		title: "Тесты",
		text: "Ответьте на вопросы и нажмите «Отправить ответы». Чтобы идти дальше, нужно набрать проходной балл, он указан в тесте. Если не получилось, можно попробовать снова.",
	},
	{
		title: "Домашние работы",
		text: "Напишите ответ и нажмите «Отправить на проверку». Преподаватель проверит работу и поставит зачёт. Статус виден в разделе «Задания».",
	},
	{
		title: "Результаты и профиль",
		text: "В «Результатах» ваши баллы и прогресс. В «Профиле» можно сменить пароль и выйти из школы. Если что-то непонятно, напишите организатору курса.",
	},
];

export function welcomeDismissed() {
	try {
		return localStorage.getItem(STORAGE_KEY) === "1";
	} catch (error) {
		return false;
	}
}

export function dismissWelcome() {
	try {
		localStorage.setItem(STORAGE_KEY, "1");
	} catch (error) {
		/* Private mode: the card simply shows again next time. */
	}
}

function stepsList() {
	return `<ol class="ou-guide-steps">${GUIDE_STEPS.map(
		(step, index) =>
			`<li><span class="ou-guide-num" aria-hidden="true">${
				index + 1
			}</span><div><strong>${e(step.title)}</strong><p>${e(
				step.text
			)}</p></div></li>`
	).join("")}</ol>`;
}

export function welcomeCard() {
	if (welcomeDismissed()) return "";
	return `<section class="ou-welcome" aria-labelledby="ou-welcome-title">
    <div class="ou-welcome-head"><div><span class="eyebrow">Первый раз здесь?</span>
    <h2 id="ou-welcome-title">Как учиться в OVER U</h2></div>
    <button type="button" class="button secondary" data-action="welcome-dismiss">Всё понятно, скрыть</button></div>
    ${stepsList()}</section>`;
}

export function openGuide() {
	if (document.getElementById("ou-guide-dialog")) return;
	const previous = document.activeElement;
	const overlay = document.createElement("div");
	overlay.className = "ou-guide-overlay";
	overlay.id = "ou-guide-dialog";
	overlay.innerHTML = `<div class="ou-guide-dialog" role="dialog" aria-modal="true" aria-labelledby="ou-guide-title">
    <div class="ou-guide-top"><h2 id="ou-guide-title">Как это работает</h2>
    <button type="button" class="ou-guide-close" aria-label="Закрыть">×</button></div>
    ${stepsList()}
    <div class="ou-guide-actions"><button type="button" class="button primary" data-guide-close>Понятно</button></div></div>`;
	const close = () => {
		document.removeEventListener("keydown", onKey);
		overlay.remove();
		dismissWelcome();
		if (previous && previous.focus) previous.focus();
	};
	const onKey = (event) => {
		if (event.key === "Escape") close();
	};
	overlay.addEventListener("click", (event) => {
		if (
			event.target === overlay ||
			event.target.closest(".ou-guide-close, [data-guide-close]")
		)
			close();
	});
	document.addEventListener("keydown", onKey);
	document.body.appendChild(overlay);
	overlay.querySelector("[data-guide-close]").focus();
}

export function chatBanner() {
	const url = (boot.chat_url || "").trim();
	if (!/^https:\/\/(chat\.whatsapp\.com|wa\.me|t\.me)\//.test(url)) return "";
	return `<section class="ou-chat" aria-label="Общий чат группы"><div><h2>Общий чат группы</h2><p>Здесь можно задать вопрос, поделиться успехами и пообщаться с другими участниками курса.</p></div><a class="button primary" href="${e(
		url
	)}" target="_blank" rel="noopener noreferrer">Открыть чат в WhatsApp</a></section>`;
}
