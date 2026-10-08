import {escape as e, icon, link, button, progress, outline, allLessons, kinds, richText} from './components.js'
export function shell(content, home, section = 'home') {
  const nav = [['home', '/school', 'Главная'], ['book', '/school/learning', 'Обучение'], ['task', '/school/assignments', 'Задания'], ['results', '/school/results', 'Результаты'], ['user', '/school/profile', 'Профиль']]
  const keys = ['home', 'learning', 'assignments', 'results', 'profile']
  const name = home?.user.name || 'Ваша школа'
  return `<aside class="navigation"><a class="wordmark" href="/school" data-nav aria-label="OVER U — главная">OVER U<span>школа вашего развития</span></a><nav aria-label="Основная навигация">${nav.map(([key, href, label], i) => link(href, `${icon(key)}<span>${label}</span>`, section === keys[i] ? 'nav-item active' : 'nav-item', section === keys[i] ? 'aria-current="page"' : '')).join('')}</nav><div class="nav-bottom"><span class="tiny-label">Учиться в своём ритме.</span><div class="account"><span class="avatar">${e(name.slice(0, 1).toUpperCase())}</span><span><strong>${e(name)}</strong><small>Личный кабинет</small></span></div></div></aside><div class="workspace"><header class="topbar"><span>Моя школа</span><span class="topbar-note">Знания, которые становятся действиями</span></header><main id="main" tabindex="-1">${content}</main><footer class="site-footer"><span>OVER U</span><span>Шаг за шагом — к вашему результату.</span></footer></div>`
}
function courseFeature(course) {
  const current = course.current
  const waiting = current?.assignment?.status === 'Not Graded'
  return `<article class="course-feature"><div class="course-feature-content"><span class="eyebrow">Ваш курс · ${course.chapters.length} модуля</span><h2>${e(course.title.replace(/^OVER U\s*[—–-]\s*/, ''))}</h2><p>${e(course.introduction)}</p><div class="next-step"><span class="tiny-label">${waiting ? 'Сейчас' : current ? 'Следующий шаг' : 'Ваш результат'}</span><strong>${waiting ? 'Домашнее задание на проверке' : current ? e(current.title) : 'Все уроки выполнены'}</strong></div>${link(course.next_href, `Продолжить обучение ${icon('arrow')}`, 'button primary')}${waiting ? '<p class="help">Следующий урок откроется после зачёта преподавателя.</p>' : ''}</div><div class="course-feature-progress"><div class="progress-ring" role="img" aria-label="Прогресс ${course.progress}%"><svg viewBox="0 0 160 160" aria-hidden="true"><circle class="ring-track" cx="80" cy="80" r="68"/><circle class="ring-value" cx="80" cy="80" r="68" pathLength="100" stroke-dasharray="${course.progress} 100"/></svg><span><strong>${course.progress}<small>%</small></strong><small>курса пройдено</small></span></div>${progress(course)}${link(course.href, 'Посмотреть программу', 'text-link')}</div></article>`
}
export function homeView(home) {
  const courses = home.courses
  if (!courses.length) return `<div class="page-heading"><span class="eyebrow">Ваша школа</span><h1>Рады вас видеть</h1></div><section class="empty"><h2>Здесь появится ваше обучение</h2><p>Пока у вас нет доступных курсов. Если обучение уже началось, обратитесь к преподавателю.</p></section>`
  const course = courses.find(c => c.current) || courses[0]
  const pending = courses.flatMap(c => c.pending)
  const completed = courses.flatMap(allLessons).filter(l => l.complete)
  return `<div class="page-heading"><span class="eyebrow">Хороший день, чтобы сделать ещё один шаг</span><h1>Ваше обучение, ${e(home.user.first_name)}.</h1><p>Продолжайте с того места, где остановились.</p></div>${courseFeature(course)}<div class="home-details"><section><div class="section-heading"><h2>На ближайшее время</h2>${link('/school/assignments', 'Все задания', 'text-link')}</div>${pending.length ? pending.map(l => `<article class="task-note"><span class="note-symbol">${icon('clock')}</span><div><span class="eyebrow">Отправлено на проверку</span><h3>${e(l.title)}</h3><p>Вы уже сделали свою часть. Дождитесь ответа преподавателя — мы покажем зачёт здесь.</p>${link(l.href, 'Посмотреть работу', 'text-link')}</div></article>`).join('') : `<article class="task-note"><span class="note-symbol">${icon(course.current ? 'book' : 'check')}</span><div><span class="eyebrow">${course.current ? 'Всё готово к следующему шагу' : 'Отличная работа'}</span><h3>${course.current ? e(course.current.title) : 'Обучение завершено'}</h3><p>${course.current ? 'Начните урок. Ваш прогресс сохранится, и вы сможете продолжить позже.' : 'Можно вернуться к материалам и ещё раз посмотреть свои результаты.'}</p></div></article>`}</section><section><div class="section-heading"><h2>Уже выполнено</h2><span class="tiny-label">${completed.length} из ${courses.reduce((n, c) => n + c.total, 0)}</span></div>${completed.length ? `<ul class="completed-list">${completed.slice(-3).reverse().map(l => `<li>${icon('check')} ${link(l.href, e(l.title))}</li>`).join('')}</ul>` : '<p class="quiet-copy">Ваш первый результат уже близко. Начните с первого урока — он открыт.</p>'}</section></div>`
}
export function learningView(home) {
  return `<div class="page-heading"><span class="eyebrow">Шаг за шагом</span><h1>Моё обучение</h1><p>Ваши курсы и точка, с которой можно продолжить.</p></div>${home.courses.map(courseFeature).join('') || '<section class="empty"><h2>Курсов пока нет</h2><p>Обратитесь к преподавателю, чтобы получить доступ.</p></section>'}`
}
export function courseView(course) {
  return `<div class="breadcrumbs">${link('/school/learning', 'Обучение')} ${icon('chevron')} <span>Программа курса</span></div><div class="course-heading"><div><span class="eyebrow">${course.chapters.length} модуля · ${course.total} уроков</span><h1>${e(course.title.replace(/^OVER U\s*[—–-]\s*/, ''))}</h1><p>${e(course.introduction)}</p></div><div class="course-summary">${progress(course)}${link(course.next_href, `Продолжить обучение ${icon('arrow')}`, 'button primary')}</div></div><div class="program-layout"><div class="program">${outline(course)}</div><aside class="program-note"><span class="note-symbol">${icon('book')}</span><h2>Один шаг за другим</h2><p>Проходите уроки по порядку. В тесте нужно набрать проходной балл, а домашняя работа завершится после зачёта преподавателя.</p>${course.pending.length ? '<div class="inline-status pending">Домашняя работа на проверке. Следующий урок пока закрыт.</div>' : ''}</aside></div>`
}
function contentBlocks(blocks) {
  return blocks.map(b => {
    if (b.type === 'header') return `<h${b.level}>${b.html}</h${b.level}>`
    if (b.type === 'paragraph') return `<div class="paragraph">${b.html}</div>`
    if (b.type === 'quote') return `<blockquote>${b.html}</blockquote>`
    if (b.type === 'video') return `<div class="video-wrap"><video controls preload="metadata" playsinline src="${e(b.url)}" aria-label="Видео урока"></video></div>`
    if (b.type === 'material') return `<div class="materials"><h2>Материалы</h2><a href="${e(b.url)}" target="_blank" rel="noopener noreferrer">${icon('book')}${e(b.title)}</a></div>`
    if (b.type === 'divider') return '<hr>'
    return ''
  }).join('')
}
function fallback(data) {
  const url = `/lms/courses/${encodeURIComponent(data.course.id)}/learn/${data.lesson.number}`
  return `<div class="inline-status"><p>Этот формат материала пока открывается в основном учебном интерфейсе.</p><a href="${e(url)}" class="text-link">Открыть материал</a></div>`
}
function quizView(data, drafts) {
  const q = data.quiz
  if (q.unsupported || q.schedule_reason) return q.schedule_reason ? `<div class="inline-status">${e(q.schedule_reason)}</div>` : fallback(data)
  const key = `${data.course.id}/${data.lesson.number}`
  const result = q.result
  const taking = !result || drafts.quizTaking.has(key)
  if (!taking) return `<section class="quiz-result ${result.passed ? 'passed' : 'not-passed'}" aria-label="Результат теста"><span class="result-symbol">${icon(result.passed ? 'check' : 'quiz')}</span><span class="eyebrow">Результат теста</span><h2>${result.passed ? 'Тест пройден' : 'Пока не пройден'}</h2><div class="score">${result.percentage}%</div><p>${result.score} из ${result.score_out_of} баллов. Проходной порог — ${q.threshold}%.</p><p>${result.passed ? 'Вы справились. Следующий шаг уже доступен.' : 'Не страшно ошибиться. Повторите материал и попробуйте ещё раз.'}</p>${q.can_retry ? button('Попробовать ещё раз', 'quiz-retry', 'button secondary') : '<p class="help">Попытки закончились. Обратитесь к преподавателю.</p>'}</section>`
  if (!q.can_retry) return '<div class="inline-status">Попытки закончились. Обратитесь к преподавателю.</div>'
  const saved = drafts.quizAnswers.get(key) || []
  return `<form id="quiz-form" class="quiz-form"><div class="assessment-heading"><span class="eyebrow">Проверим, что осталось с вами</span><h2>${e(q.title.replace(/^OVER U\s*[—–-]\s*/, ''))}</h2><p>${q.questions.length} вопроса · Проходной порог ${q.threshold}%${q.max_attempts ? ` · Осталось попыток: ${q.max_attempts - q.attempts}` : ' · Можно попробовать снова'}</p></div>${q.questions.map((question, i) => `<fieldset><legend><span class="question-number">${i + 1}</span>${e(question.prompt)}</legend><div class="answers">${question.options.map((option, j) => `<label class="answer-option"><input type="radio" name="question-${i}" value="${j}" ${saved[i] === j ? 'checked' : ''} required><span>${e(richText(option))}</span></label>`).join('')}</div></fieldset>`).join('')}<div id="form-feedback" role="alert"></div><button class="button primary" type="submit">Отправить ответы ${icon('arrow')}</button></form>`
}
function homeworkView(data, drafts) {
  const a = data.assignment
  if (a.type !== 'Text') return fallback(data)
  const s = a.submission
  const key = `${data.course.id}/${data.lesson.number}`
  const passed = s?.status === 'Pass'
  const pending = s?.status === 'Not Graded'
  const failed = s?.status === 'Fail'
  const editing = !s || failed || drafts.homeworkEditing.has(key)
  const answer = drafts.homeworkAnswers.get(key) ?? richText(s?.answer)
  const banner = passed ? `<div class="homework-status passed" role="status">${icon('check')}<div><strong>Зачтено</strong><p>Преподаватель проверил работу. Можно перейти к следующему уроку.</p></div></div>` : pending ? `<div class="homework-status waiting" role="status">${icon('clock')}<div><strong>Отправлено на проверку</strong><p>Следующий обязательный урок откроется после зачёта преподавателя.</p></div></div>` : failed ? `<div class="homework-status revision" role="status">${icon('task')}<div><strong>Нужно доработать</strong><p>Учтите комментарий преподавателя и отправьте ответ снова.</p></div></div>` : ''
  return `<section class="homework"><span class="eyebrow">От знаний — к практике</span><h2>${e(a.title.replace(/^OVER U\s*[—–-]\s*/, ''))}</h2><div class="assignment-instructions">${a.instructions}</div>${banner}${s?.comments ? `<div class="teacher-comment"><span class="eyebrow">Комментарий преподавателя</span><div>${s.comments}</div></div>` : ''}${a.schedule_reason ? `<div class="inline-status">${e(a.schedule_reason)}</div>` : editing && !passed ? `<form id="homework-form"><label for="homework-answer">Ваш ответ</label><p id="answer-hint" class="help">Опишите свой план своими словами. Максимум 20 000 символов.</p><textarea id="homework-answer" name="answer" rows="6" maxlength="20000" required aria-describedby="answer-hint">${e(answer)}</textarea><div id="form-feedback" role="alert"></div><button type="submit" class="button primary">${failed || s ? 'Отправить снова' : 'Отправить на проверку'} ${icon('arrow')}</button></form>` : `<div class="submitted-answer"><span class="eyebrow">Ваш ответ</span><div>${s?.answer || ''}</div></div>${!passed ? button('Изменить ответ', 'homework-edit', 'button secondary') : ''}`}${pending ? button(`${icon('clock')} Проверить статус`, 'refresh-status', 'button quiet') : ''}</section>`
}
export function lessonView(data, drafts) {
  const c = data.course, l = data.lesson
  let article
  if (data.locked) article = `<section class="locked-state"><span class="lock-symbol">${icon('lock')}</span><span class="eyebrow">Всё в своё время</span><h2>Этот урок пока закрыт</h2><p class="lock-reason">${e(data.lock_reason)}</p><p>Мы сохранили ваш прогресс. Вернитесь к текущему шагу — следующий откроется, когда всё будет готово.</p>${link(c.next_href, `К текущему шагу ${icon('arrow')}`, 'button primary')}</section>`
  else article = `<article class="reading"><div class="lesson-content">${contentBlocks(data.blocks)}${data.unsupported_content ? fallback(data) : ''}${data.quiz ? quizView(data, drafts) : ''}${data.assignment ? homeworkView(data, drafts) : ''}</div><div class="lesson-footer">${l.complete ? `<span class="completed-mark">${icon('check')}Урок выполнен</span>` : data.assignment ? '<span class="help">Для завершения нужен зачёт преподавателя.</span>' : data.quiz ? '<span class="help">Для завершения пройдите тест.</span>' : button(`Завершить урок ${icon('check')}`, 'complete')} ${data.next ? link(data.next.href, `${data.next.locked ? icon('lock') : ''}${data.next.locked ? 'Следующий урок закрыт' : 'Следующий урок'} ${icon('arrow')}`, 'button secondary') : l.complete ? link(c.href, 'Курс завершён · к программе', 'button secondary') : ''}</div><div id="action-feedback" role="alert"></div></article>`
  return `<div class="breadcrumbs">${link('/school/learning', 'Обучение')} ${icon('chevron')} ${link(c.href, 'Программа курса')}</div><div class="learn-layout"><div class="learn-main"><div class="lesson-heading"><span class="eyebrow">${e(l.chapter_title)} · ${kinds[l.kind]}</span><h1>${e(l.title.replace(/^\d+\.\d+\s*/, ''))}</h1></div>${article}</div><aside class="learn-outline"><div class="outline-heading"><h2>${e(c.title.replace(/^OVER U\s*[—–-]\s*/, ''))}</h2>${progress(c)}</div>${outline(c, true, l.number)}</aside></div>`
}
export function assignmentsView(home) {
  const lessons = home.courses.flatMap(allLessons).filter(l => l.kind === 'assignment' && !l.locked)
  return `<div class="page-heading"><span class="eyebrow">От теории — к вашему опыту</span><h1>Мои задания</h1><p>Здесь — ваши работы и обратная связь преподавателя.</p></div>${lessons.length ? lessons.map(l => `<article class="assignment-row"><div><span class="eyebrow">${l.assignment?.status === 'Pass' ? 'Зачтено' : l.assignment?.status === 'Not Graded' ? 'Отправлено на проверку' : l.assignment?.status === 'Fail' ? 'Нужно доработать' : 'Можно приступить'}</span><h2>${e(l.title)}</h2></div>${link(l.href, `Открыть работу ${icon('arrow')}`, 'button secondary')}</article>`).join('') : '<section class="empty"><h2>К практике придём чуть позже</h2><p>Домашние задания появятся здесь, когда вы пройдёте предыдущие уроки.</p></section>'}`
}
export function resultsView(home) {
  const rows = home.courses.flatMap(allLessons).filter(l => l.quiz_result)
  return `<div class="page-heading"><span class="eyebrow">Каждый шаг имеет значение</span><h1>Мои результаты</h1><p>Ваш прогресс и последние результаты тестов.</p></div>${home.courses.map(c => `<section class="result-course"><h2>${e(c.title)}</h2>${progress(c)}</section>`).join('')}${rows.map(l => `<article class="assignment-row"><div><span class="eyebrow">${l.quiz_result.passed ? 'Тест пройден' : 'Пока не пройден'}</span><h2>${e(l.title)}</h2><p>${l.quiz_result.percentage}% · проходной порог ${l.quiz_result.threshold}%</p></div>${link(l.href, 'Посмотреть результат', 'text-link')}</article>`).join('') || '<p class="quiet-copy">Первые результаты тестов появятся после отправки ответов.</p>'}`
}
export function profileView(home) {
  return `<div class="page-heading"><span class="eyebrow">Личный кабинет</span><h1>Мой профиль</h1></div><section class="profile-panel"><span class="avatar large">${e(home.user.name.slice(0, 1))}</span><div><h2>${e(home.user.name)}</h2><p>${e(home.user.email)}</p><p class="help">Чтобы изменить данные профиля, обратитесь к администратору школы.</p></div></section>`
}
export const loadingView = () => '<section class="loading-state" role="status"><span class="loading-dot"></span><p>Открываем ваш следующий шаг…</p></section>'
export function errorView(error) {
  return `<section class="empty" role="alert"><h1>Не удалось открыть страницу</h1><p>${e(error.message)}</p>${error.status === 401 ? '<a class="button primary" href="/login?redirect-to=%2Fschool">Войти в школу</a>' : button('Попробовать ещё раз', 'retry')}</section>`
}
