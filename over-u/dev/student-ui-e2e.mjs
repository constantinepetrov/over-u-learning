// Real demo-user workflow. No cookie/password is written to evidence or stdout.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import {chromium} from 'playwright'
const out = new URL('../evidence/student-ui-v1/', import.meta.url).pathname
const env = Object.fromEntries(fs.readFileSync(process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env', 'utf8').trim().split('\n').map(line => {const i = line.indexOf('='); return [line.slice(0, i), line.slice(i + 1)]}))
const base = process.env.OVER_U_BASE_URL || 'http://over-u.localhost:8000'
const evidence = {screens: [], checks: [], errors: []}
const browser = await chromium.launch({executablePath: process.env.OVER_U_CHROMIUM || '/usr/bin/chromium', args: ['--no-sandbox', '--host-resolver-rules=MAP over-u.localhost 127.0.0.1']})
const students = ['student1@over-u.example.com', 'student2@over-u.example.com']
let student
async function login(user, password, destination = '/school') {
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'})
  const page = await context.newPage()
  page.on('pageerror', error => evidence.errors.push({user, message: error.message}))
  await page.goto(`${base}/login?redirect-to=${encodeURIComponent(destination)}`)
  await page.locator('#login_email').fill(user)
  await page.locator('#login_password').fill(password)
  await page.getByRole('button', {name: /^(Continue|Продолжить)$/, exact: true}).click()
  await page.waitForURL(url => !url.pathname.startsWith('/login'))
  await page.goto(base + destination)
  return page
}
async function call(page, method, args = {}) {
  return page.evaluate(async ({method, args}) => {
    const boot = document.getElementById('school-boot')
    const token = boot ? JSON.parse(boot.textContent).csrf_token : window.csrf_token
    const r = await fetch(`/api/method/${method}`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': token}, body: JSON.stringify(args)})
    const body = await r.json()
    if (!r.ok) throw new Error(`${method}: ${r.status} ${body.exc_type || 'request failed'}`)
    return body.message
  }, {method, args})
}
const api = (page, method, args = {}) => call(page, `over_u.student_api.${method}`, args)
async function shot(page, file, description) {
  await page.screenshot({path: `${out}${file}.png`, fullPage: true})
  evidence.screens = evidence.screens.filter(s => s.file !== `${file}.png`)
  evidence.screens.push({file: `${file}.png`, description, url: page.url()})
  console.log('SCREEN', file)
}
async function lesson(number) {
  await student.goto(`${base}/school/courses/over-u/lessons/${number}`)
  await student.locator('.lesson-heading h1').waitFor()
}
async function finish() {
  await student.getByRole('button', {name: /Завершить урок/}).click()
  await student.getByText('Урок выполнен', {exact: true}).waitFor()
}
async function snapshot() {return api(student, 'course', {course: 'over-u'})}
function flat(course) {return course.chapters.flatMap(c => c.lessons)}
try {
  const guest = await browser.newPage()
  await guest.goto(base + '/school')
  assert.ok(new URL(guest.url()).pathname.startsWith('/login'))
  evidence.checks.push('Guest is redirected to stock login.')
  student = await login(students[1], env.OVER_U_DEMO_PASSWORD)
  await student.locator('.course-feature').waitFor()
  let course = await snapshot()
  const resume = process.env.OVER_U_RESUME === 'teacher'
  const verify = process.env.OVER_U_RESUME === 'verify'
  if (verify) {
    const previous = JSON.parse(fs.readFileSync(`${out}validation.json`, 'utf8'))
    evidence.screens = previous.screens; evidence.checks = previous.checks
    assert.equal(course.completed, 6)
  } else {
  if (resume) {
    const previous = JSON.parse(fs.readFileSync(`${out}validation.json`, 'utf8'))
    evidence.screens = previous.screens; evidence.checks = previous.checks
    assert.equal(course.completed, 4)
  } else {
    assert.equal(course.completed, 0, 'Use untouched student 2 for first run; resume with OVER_U_RESUME=teacher after homework.')
    assert.equal(flat(course).filter(l => l.locked).length, 5)
    await shot(student, '01-home', 'Главная: реальный курс, прогресс 0%, текущий шаг')
    await student.getByRole('link', {name: 'Посмотреть программу', exact: true}).click()
    await student.locator('.program').waitFor()
    await shot(student, '02-course', 'Программа: три модуля, шесть уроков, последовательность')
    await lesson('3-2')
    await student.getByRole('heading', {name: 'Этот урок пока закрыт'}).waitFor()
    assert.equal(await student.locator('.lesson-content').count(), 0)
    await lesson('1-1')
    await shot(student, '03-text-lesson', 'Текстовый урок и программа рядом')
    await finish()
    await lesson('1-2')
    const video = student.locator('video')
    await video.evaluate(async v => {v.muted = true; await v.play()})
    assert.ok(await video.evaluate(v => v.duration > 0 && v.readyState >= 2))
    await shot(student, '04-video-lesson', 'Видео воспроизводится в собственном интерфейсе')
    await video.evaluate(v => v.pause())
    await finish()
    await lesson('2-1'); await finish()
    await lesson('2-2')
    await student.locator('#quiz-form').waitFor()
    assert.equal(await student.locator('fieldset').count(), 4)
    await shot(student, '05-quiz', 'Тест: четыре вопроса, порог 75%')
    for (let i = 0; i < 4; i++) await student.locator(`input[name="question-${i}"]`).nth(i < 2 ? 0 : 1).check()
    await student.getByRole('button', {name: /Отправить ответы/}).click()
    await student.getByRole('heading', {name: 'Пока не пройден'}).waitFor()
    assert.equal((await snapshot()).completed, 3)
    assert.ok(flat(await snapshot())[4].locked)
    await shot(student, '06-quiz-failed', '50%: тест не пройден, задание остаётся закрытым')
    await student.getByRole('button', {name: 'Попробовать ещё раз', exact: true}).click()
    for (let i = 0; i < 4; i++) await student.locator(`input[name="question-${i}"]`).nth(i < 3 ? 0 : 1).check()
    await student.getByRole('button', {name: /Отправить ответы/}).click()
    await student.getByRole('heading', {name: 'Тест пройден'}).waitFor()
    assert.equal((await snapshot()).completed, 4)
    assert.equal(await student.locator('.score').textContent(), '75%')
    await shot(student, '07-quiz-passed', '75%: тест пройден, открыт следующий шаг')
    evidence.checks.push('Browser-only lesson completion, playable video, quiz 50% stays locked, retry 75% unlocks homework.')
    await lesson('3-1')
    const answer = 'Моя цель — закончить обучение OVER U до пятницы. Каждый день выделяю 20 минут. Первый шаг — записать план и отметить выполненный урок.'
    await student.getByLabel('Ваш ответ', {exact: true}).fill(answer)
    // A network failure must preserve the draft and expose an actionable error.
    await student.route('**/api/method/over_u.student_api.submit_assignment', r => r.abort('failed'))
    await student.getByRole('button', {name: /Отправить на проверку/}).click()
    await student.locator('#form-feedback').filter({hasText: /.+/}).waitFor()
    assert.equal(await student.getByLabel('Ваш ответ', {exact: true}).inputValue(), answer)
    await student.unroute('**/api/method/over_u.student_api.submit_assignment')
    await student.getByRole('link', {name: 'Профиль', exact: true}).click()
    await student.getByRole('heading', {name: 'Мой профиль'}).waitFor()
    await student.goBack()
    await student.getByLabel('Ваш ответ', {exact: true}).waitFor()
    assert.equal(await student.getByLabel('Ваш ответ', {exact: true}).inputValue(), answer)
    evidence.checks.push('Failed homework request and browser back retain in-memory draft; error is visible.')
    await student.getByRole('button', {name: /Отправить на проверку/}).click()
    await student.getByText('Отправлено на проверку', {exact: true}).waitFor()
    assert.equal((await snapshot()).completed, 4)
    await shot(student, '08-homework-pending', 'Работа отправлена, ожидает проверки, следующий урок закрыт')
    await lesson('3-2')
    await student.getByRole('heading', {name: 'Этот урок пока закрыт'}).waitFor()
    await student.getByText('Сначала дождитесь проверки домашнего задания.', {exact: true}).waitFor()
    await shot(student, '09-next-locked', 'Следующий урок закрыт до зачёта, причина показана ученику')
    await student.goto(base + '/school')
    await student.getByText('Домашнее задание на проверке', {exact: true}).waitFor()
    await shot(student, '10-home-pending', 'Главная показывает ожидающую проверки работу и 66.7%')
    evidence.checks.push('Not Graded homework retains 4/6 progress; direct next URL remains locked.')
  }
  await lesson('3-1')
  const submission = await call(student, 'lms.lms.api.get_own_assignment_submission', {assignment: 'ASG-00005'})
  assert.ok(submission)
  const teacher = await login('teacher@over-u.example.com', env.OVER_U_DEMO_PASSWORD, '/lms/courses')
  await teacher.getByText('OVER U — Основы осознанного обучения', {exact: true}).first().waitFor()
  await shot(teacher, '11-stock-lms', 'Штатный LMS преподавателя сохранён')
  await teacher.goto(`${base}/lms/courses/over-u#editor`)
  await teacher.getByText('1.1 Добро пожаловать', {exact: true}).first().click()
  await teacher.locator('.ce-block:visible').first().waitFor()
  await shot(teacher, '12-stock-editor', 'Штатный редактор курса сохранён')
  await teacher.goto(`${base}/lms/assignment-submission/ASG-00005/${submission}`)
  await teacher.getByLabel(/^(Grade|Оценка)$/).click()
  await teacher.getByRole('option', {name: /^(Pass|Зачтено)$/, exact: true}).click()
  await teacher.locator('[contenteditable="true"]').last().fill('Зачёт. Цель измерима, срок и первый шаг указаны. Можно переходить к итогам.')
  await shot(teacher, '13-teacher-grading', 'Преподаватель проверяет существующую работу в штатном LMS')
  await teacher.getByRole('button', {name: /^(Save|Сохранить)$/, exact: true}).click()
  await teacher.getByText(/^(Pass|Зачтено)$/, {exact: true}).first().waitFor()
  // The waiting student page must notice stock grading without resubmitting work.
  await student.getByText('Зачтено', {exact: true}).waitFor({timeout: 35000})
  assert.equal((await snapshot()).completed, 5)
  await shot(student, '14-homework-pass', 'Ученик видит зачёт и комментарий преподавателя без повторной отправки')
  assert.equal(await student.locator('#homework-form').count(), 0)
  await lesson('3-2')
  await student.locator('.reading').waitFor()
  assert.equal(await student.locator('.locked-state').count(), 0)
  await shot(student, '15-next-unlocked', 'Следующий урок открыт после Pass')
  await finish()
  assert.equal((await snapshot()).progress, 100)
  evidence.checks.push('Stock teacher Pass is observed by student polling, advances progress to 5/6, unlocks final lesson; final completion reaches 100%.')
  }
  await student.getByRole('link', {name: 'Результаты', exact: true}).click()
  await student.getByRole('heading', {name: 'Мои результаты'}).waitFor()
  await shot(student, '16-results', '100% прогресса и собственный результат теста 75%')
  await student.getByRole('link', {name: 'Задания', exact: true}).click()
  await student.getByText('Зачтено', {exact: true}).waitFor()
  await student.getByRole('link', {name: 'Профиль', exact: true}).click()
  await student.getByText(students[1], {exact: true}).waitFor()
  const first = await login(students[0], env.OVER_U_DEMO_PASSWORD)
  const firstHome = await api(first, 'home')
  assert.equal(firstHome.user.email, students[0]); assert.equal(firstHome.courses[0].progress, 100)
  assert.ok(!JSON.stringify(firstHome).includes('Моя цель — закончить обучение OVER U до пятницы.'))
  evidence.checks.push('Student 1 retains existing 100% and never sees student 2 answer; minimal assignments/results/profile work.')
  await student.goto(`${base}/school/courses/over-u`)
  await student.locator('.program').waitFor()
  for (const width of [320, 390, 768]) {
    await student.setViewportSize({width, height: 844})
    assert.ok(await student.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `No horizontal overflow at ${width}`)
    await shot(student, `17-responsive-${width}`, `Программа курса при ширине ${width}px`)
  }
  // Equivalent layout viewport for desktop at 200% zoom (1440 / 2).
  await student.setViewportSize({width: 720, height: 500})
  await lesson('2-2')
  assert.ok(await student.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await shot(student, '18-zoom-200-layout', 'Компоновка при эквиваленте 200% desktop zoom')
  await student.setViewportSize({width: 1440, height: 1000})
  await student.goto(base + '/school')
  await student.locator('.course-feature').waitFor()
  await student.getByRole('link', {name: 'Результаты', exact: true}).focus()
  await student.keyboard.press('Tab')
  assert.equal(await student.evaluate(() => document.activeElement.textContent.trim()), 'Профиль')
  await student.keyboard.press('Enter')
  await student.getByRole('heading', {name: 'Мой профиль'}).waitFor()
  assert.equal(await student.evaluate(() => document.activeElement.id), 'main')
  evidence.checks.push('320/390/768 widths and 720 CSS-pixel zoom-equivalent have no overflow; navigation is keyboard operable; reduced motion is enabled.')
  const admin = await login('Administrator', env.OVER_U_ADMIN_PASSWORD, '/desk')
  // The POC site has not completed the stock Desk setup wizard. Do not change
  // site configuration just to bypass it; validate the real existing entry.
  await admin.getByRole('button', {name: /^(Get Started|Начать настройку)$/, exact: true}).waitFor()
  assert.ok(new URL(admin.url()).pathname.startsWith('/desk/'))
  await shot(admin, '19-stock-desk', 'Штатный Desk сохранён; POC открывает исходный setup wizard')
  evidence.checks.push('Stock /desk renders its existing setup wizard; full administration requires completing that wizard.')
  assert.deepEqual(evidence.errors, [], 'No uncaught browser JS errors')
  evidence.status = 'passed'
} catch (error) {
  evidence.status = 'failed'; evidence.failure = error.message; console.error('FAILED', error.message)
  if (student) await student.screenshot({path: `${out}failure.png`, fullPage: true}).catch(() => {})
  process.exitCode = 1
} finally {
  evidence.checks = [...new Set(evidence.checks)]
  fs.writeFileSync(`${out}validation.json`, JSON.stringify(evidence, null, 2))
  await browser.close()
}
