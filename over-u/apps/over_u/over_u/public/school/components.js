export const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch]))
const paths = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  book: '<path d="M12 5v16M3 4c4-1 6 0 9 1 3-1 5-2 9-1v15c-4-1-6 0-9 2-3-2-5-3-9-2Z"/>',
  task: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 10h6M9 15h6"/>',
  results: '<path d="M4 20h17M6 15v-4M12 15V5M18 15V8"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  arrow: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  video: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3Z"/>',
  quiz: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 3h.01"/>',
}
export const icon = (name, cls = '') => `<svg class="icon ${cls}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.book}</svg>`
export const link = (href, label, cls = '', extra = '') => `<a href="${escape(href)}" data-nav class="${cls}" ${extra}>${label}</a>`
export const button = (label, action, cls = 'button primary', extra = '') => `<button type="button" data-action="${action}" class="${cls}" ${extra}>${label}</button>`
export const kinds = {text: 'Урок', video: 'Видео', quiz: 'Тест', assignment: 'Домашнее задание'}
export const allLessons = course => course.chapters.flatMap(chapter => chapter.lessons)
export const richText = html => { const doc = new DOMParser().parseFromString(html || '', 'text/html'); doc.querySelectorAll('br').forEach(br => br.replaceWith('\n')); return doc.body.textContent }
export function progress(course) {
  return `<div class="progress-meta"><span>${course.completed} из ${course.total} уроков</span><strong>${course.progress}%</strong></div><progress max="100" value="${course.progress}" aria-label="Прогресс курса: ${course.progress}%">${course.progress}%</progress>`
}
export function status(lesson) {
  if (lesson.locked) return `<span class="lesson-state muted">${icon('lock')}Закрыт</span>`
  const homework = lesson.assignment
  if (homework?.status === 'Not Graded') return `<span class="lesson-state pending">${icon('clock')}На проверке</span>`
  if (homework?.status === 'Fail') return '<span class="lesson-state revision">Нужны правки</span>'
  if (lesson.complete) return `<span class="lesson-state success">${icon('check')}Выполнено</span>`
  return '<span class="lesson-state current">Можно начать</span>'
}
export function lessonRow(lesson, compact = false, active = '') {
  const symbol = lesson.locked ? 'lock' : lesson.complete ? 'check' : ({video: 'video', quiz: 'quiz', assignment: 'task'}[lesson.kind] || 'book')
  return link(lesson.href, `<span class="lesson-symbol ${lesson.complete ? 'done' : ''}">${icon(symbol)}</span><span class="lesson-info"><span class="lesson-title">${escape(lesson.title)}</span><span class="lesson-kind">${kinds[lesson.kind]}${lesson.assignment?.status === 'Not Graded' ? ' · На проверке' : ''}</span></span>${compact ? '' : status(lesson)}${icon('chevron', 'row-chevron')}`, `lesson-row ${compact ? 'compact' : ''} ${lesson.locked ? 'locked-row' : ''} ${active === lesson.number ? 'selected' : ''}`, active === lesson.number ? 'aria-current="page"' : '')
}
export function outline(course, compact = false, active = '') {
  return course.chapters.map(chapter => `<section class="module"><div class="module-heading"><span class="eyebrow">Модуль ${chapter.number}</span><h${compact ? 3 : 2}>${escape(chapter.title.replace(/^\d+\.\s*/, ''))}</h${compact ? 3 : 2}><span class="module-count">${chapter.lessons.filter(l => l.complete).length}/${chapter.lessons.length}</span></div><div class="lesson-list">${chapter.lessons.map(l => lessonRow(l, compact, active)).join('')}</div></section>`).join('')
}
