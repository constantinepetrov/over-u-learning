import fs from 'node:fs'
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const out = new URL('../evidence/', import.meta.url).pathname
const env = Object.fromEntries(fs.readFileSync(process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env', 'utf8').trim().split('\n').map(line => {
  const i = line.indexOf('=')
  return [line.slice(0, i), line.slice(i + 1)]
}))
const school = JSON.parse(fs.readFileSync(`${out}demo-manifest.json`, 'utf8'))
const base = process.env.OVER_U_BASE_URL || 'http://over-u.localhost:8000'
const browser = await chromium.launch({executablePath: process.env.OVER_U_CHROMIUM || '/usr/bin/chromium', args: ['--no-sandbox', '--host-resolver-rules=MAP over-u.localhost 127.0.0.1']})
const evidence = {screens: [], checks: [], errors: []}

async function login(user, password) {
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}})
  const page = await context.newPage()
  page.on('pageerror', error => evidence.errors.push({user, message: error.message}))
  await page.goto(`${base}/login`)
  const status = await page.evaluate(async ({user, password}) => (await fetch('/api/method/login', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({usr: user, pwd: password})
  })).status, {user, password})
  assert.equal(status, 200, `Login ${user}`)
  await page.goto(`${base}/lms/courses`)
  await page.getByText('OVER U — Основы осознанного обучения', {exact: true}).first().waitFor()
  return page
}

async function call(page, method, args = {}) {
  const result = await page.evaluate(async ({method, args}) => {
    const response = await fetch(`/api/method/${method}`, {method: 'POST', headers: {
      'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': window.csrf_token
    }, body: JSON.stringify(args)})
    return {status: response.status, body: await response.json()}
  }, {method, args})
  if (result.status !== 200) throw new Error(`${method}: HTTP ${result.status}: ${result.body.exc_type || result.body.exception}`)
  return result.body.message
}

async function shot(page, file, description) {
  await page.waitForTimeout(1000)
  if (!['01-student-catalog', '02-student-lesson'].includes(file) || !fs.existsSync(`${out}${file}.png`)) {
    await page.screenshot({path: `${out}${file}.png`, fullPage: true})
  }
  evidence.screens = evidence.screens.filter(screen => screen.file !== `${file}.png`)
  evidence.screens.push({file: `${file}.png`, description, url: page.url()})
  console.log('SCREEN', file)
}

async function outline(page) {
  return (await call(page, 'lms.lms.utils.get_course_outline', {course: school.course, progress: true})).flatMap(chapter => chapter.lessons)
}

const student = await login(school.students[0], env.OVER_U_DEMO_PASSWORD)
try {
  let submission
  if (process.env.OVER_U_RESUME === 'teacher') {
    const previous = JSON.parse(fs.readFileSync(`${out}browser-validation.json`, 'utf8'))
    evidence.screens = previous.screens
    evidence.checks = previous.checks
    submission = previous.submission
    assert.ok(submission)
    evidence.submission = submission
    assert.ok((await outline(student))[5].locked)
  } else {
  await shot(student, '01-student-catalog', 'Интерфейс ученика: каталог OVER U')
  let lessons = await outline(student)
  assert.ok(lessons[5].locked)
  evidence.checks.push('The final lesson is locked before required work is completed.')
  await student.goto(`${base}/lms/courses/${school.course}/learn/1-1`)
  await student.getByText('Ваша школа OVER U', {exact: true}).waitFor()
  await shot(student, '02-student-lesson', 'Прохождение текстового урока и последовательность')
  // The stock save_progress API is also verified independently by backend tests.
  await call(student, 'lms.lms.doctype.course_lesson.course_lesson.save_progress', {lesson: school.lessons[0].name, course: school.course})
  await student.goto(`${base}/lms/courses/${school.course}/learn/1-2`)
  await student.locator('video').waitFor()
  await student.locator('video').evaluate(async video => {video.muted = true; await video.play()})
  assert.ok(await student.locator('video').evaluate(video => video.duration > 0 && video.readyState >= 2))
  await shot(student, '03-video-lesson', 'Штатный видеоплеер с локальным demo-видео')
  await call(student, 'lms.lms.doctype.course_lesson.course_lesson.save_progress', {lesson: school.lessons[1].name, course: school.course})
  await student.goto(`${base}/lms/courses/${school.course}/learn/2-1`)
  await student.getByText(/Хорошая цель включает/).waitFor()
  await call(student, 'lms.lms.doctype.course_lesson.course_lesson.save_progress', {lesson: school.lessons[2].name, course: school.course})
  await student.goto(`${base}/lms/courses/${school.course}/learn/2-2`)
  await student.getByRole('button', {name: 'Start Quiz', exact: true}).click()
  await student.getByRole('radio').first().waitFor()
  await shot(student, '04-quiz-question', 'Тест: 4 вопроса, проходной балл 75%')
  for (let i = 0; i < 4; i++) {
    await student.getByRole('radio').nth(i === 3 ? 1 : 0).check()
    const check = student.getByRole('button', {name: 'Check', exact: true})
    if (await check.count()) {
      await check.click()
      await student.waitForTimeout(300)
    }
    if (i < 3) {
      await student.getByRole('button', {name: 'Next', exact: true}).click()
      await student.waitForTimeout(250)
    }
  }
  await student.getByRole('button', {name: 'Submit', exact: true}).click()
  await student.waitForTimeout(700)
  const dialog = student.getByRole('dialog')
  if (await dialog.count()) {
    await dialog.getByRole('button', {name: /Submit/}).click()
  }
  await student.waitForTimeout(2000)
  const quizRows = await call(student, 'frappe.client.get_list', {doctype: 'LMS Quiz Submission', fields: ['name', 'percentage'], filters: {quiz: school.quiz, member: school.students[0]}})
  assert.equal(quizRows[0].percentage, 75)
  await shot(student, '05-quiz-result', 'Тест отправлен через интерфейс: 3 из 4, 75%')
  assert.ok(!(await outline(student))[4].locked)
  evidence.checks.push('Browser quiz submission with 3/4 correct scores 75% and unlocks assignment.')
  await student.goto(`${base}/lms/courses/${school.course}/learn/3-1`)
  const frame = student.frameLocator('iframe[src*="assignment-submission"]')
  await frame.locator('[contenteditable="true"]').first().waitFor()
  await frame.locator('[contenteditable="true"]').first().fill('Моя цель — пройти модуль OVER U до пятницы. Каждый день учусь 20 минут и записываю один выполненный шаг.')
  await shot(student, '06-assignment-send', 'Ученик пишет и отправляет домашнюю работу')
  await frame.getByRole('button', {name: 'Save', exact: true}).click()
  await frame.getByText('Not Graded', {exact: true}).waitFor()
  submission = await call(student, 'lms.lms.api.get_own_assignment_submission', {assignment: school.assignment})
  evidence.submission = submission
  await student.goto(`${base}/lms/assignment-submission/${school.assignment}/${submission}`)
  await student.getByText('Not Graded', {exact: true}).waitFor()
  await shot(student, '07-assignment-pending', 'Работа отправлена: Not Graded, ожидает преподавателя')
  assert.ok((await outline(student))[5].locked)
  evidence.checks.push('Submitting homework leaves final lesson locked until teacher Pass.')
  }
  const teacher = await login(school.teacher, env.OVER_U_DEMO_PASSWORD)
  await teacher.goto(`${base}/lms/courses/${school.course}#dashboard`)
  await teacher.getByText('Dashboard', {exact: true}).first().waitFor()
  await shot(teacher, '08-teacher-dashboard', 'Интерфейс преподавателя и прогресс учеников')
  await teacher.goto(`${base}/lms/courses/${school.course}#editor`)
  await teacher.getByText('1.1 Добро пожаловать', {exact: true}).first().click()
  await teacher.locator('.ce-block:visible').first().waitFor()
  await shot(teacher, '09-course-editor', 'Штатный редактор курса, модулей и урока')
  await teacher.goto(`${base}/lms/assignment-submissions`)
  await teacher.getByText('Assignment Submissions', {exact: true}).first().waitFor()
  await teacher.waitForTimeout(1500)
  await shot(teacher, '10-teacher-submissions', 'Преподаватель: список присланных работ')
  await teacher.goto(`${base}/lms/assignment-submission/${school.assignment}/${submission}`)
  await teacher.getByLabel('Grade').click()
  await teacher.getByRole('option', {name: 'Pass', exact: true}).click()
  await teacher.locator('[contenteditable="true"]').last().fill('Зачёт. Цель измерима, первый шаг и срок указаны. Можно переходить к итогам.')
  await shot(teacher, '11-teacher-grading', 'Преподаватель проверяет ответ и выбирает Pass')
  await teacher.getByRole('button', {name: 'Save', exact: true}).click()
  await teacher.getByText('Pass', {exact: true}).first().waitFor()
  await shot(teacher, '12-assignment-pass', 'Сохранённая проверка: Pass и комментарий')
  assert.ok(!(await outline(student))[5].locked)
  evidence.checks.push('Teacher Pass unlocks final lesson without a learner resubmission.')
  await student.goto(`${base}/lms/courses/${school.course}/learn/3-2`)
  await student.getByText(/Работа зачтена преподавателем/).waitFor()
  await shot(student, '13-final-lesson-unlocked', 'Следующий урок открыт после Pass')
  await call(student, 'lms.lms.doctype.course_lesson.course_lesson.save_progress', {lesson: school.lessons[5].name, course: school.course})
  await student.goto(`${base}/lms/courses`)
  await student.getByText('100% completed', {exact: true}).waitFor()
  await shot(student, '14-course-completed', 'Прогресс ученика 1: 100%')
  const second = await login(school.students[1], env.OVER_U_DEMO_PASSWORD)
  assert.equal((await outline(second)).filter(lesson => lesson.locked).length, 5)
  evidence.checks.push('Student 2 remains at 0% with 5 locked lessons; progress is isolated.')
  const admin = await login('Administrator', env.OVER_U_ADMIN_PASSWORD)
  evidence.checks.push('Administrator login works.')
  await shot(admin, '15-administrator', 'Администратор в штатном LMS')
  evidence.status = 'passed'
} catch (error) {
  evidence.status = 'failed'
  evidence.failure = error.message
  console.error('FAILED', error.message)
  await student.screenshot({path: `${out}browser-failure.png`, fullPage: true}).catch(() => {})
  process.exitCode = 1
} finally {
  fs.writeFileSync(`${out}browser-validation.json`, JSON.stringify(evidence, null, 2))
  await browser.close()
}
