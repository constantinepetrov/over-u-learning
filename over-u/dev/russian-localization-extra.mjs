// Read-only authoring checks; no authored course, quiz or assignment is saved.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import {chromium} from 'playwright'
const out = process.env.OVER_U_EVIDENCE_DIR || new URL('../evidence/russian-localization/', import.meta.url).pathname
fs.mkdirSync(out, {recursive: true})
const env = Object.fromEntries(fs.readFileSync(process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env','utf8').trim().split('\n').map(s => {const i=s.indexOf('=');return [s.slice(0,i),s.slice(i+1)]}))
const base = process.env.OVER_U_BASE_URL || 'http://over-u.localhost:8000'
const browser = await chromium.launch({executablePath:'/usr/bin/chromium', args:['--no-sandbox','--host-resolver-rules=MAP *.localhost 127.0.0.1']})
const result = {checks:[], screens:[], errors:[], expectedErrors:[], english:[]}
let invalidDraft = false
async function page() {
 const c=await browser.newContext({viewport:{width:1440,height:1000},locale:'ru-RU'});const p=await c.newPage()
 p.on('pageerror',e=>{if(invalidDraft && e.message === '/api/method/frappe.client.insert MandatoryError')result.expectedErrors.push(e.message);else result.errors.push(e.message)}); return p
}
async function shot(p,name) {
 const text=(await p.locator('body').innerText()).replace(/[\w.+-]+@[\w.-]+/g,'').replace(/over\s*u|ctrl|\besc\b|\bPDF\b|\bURL\b|YouTube|Frappe(?: Learning)?|Administrator/gi,'')
 const words=[...new Set(text.match(/[A-Za-z]{2,}/g)||[])]; if(words.length)result.english.push({name,words})
 await p.screenshot({path:out+name+'.png',fullPage:true});result.screens.push(name+'.png');console.log('SCREEN',name)
}
async function login(p,user) {
 await p.goto(base+'/login');await p.locator('#login_email').fill(user);await p.locator('#login_password').fill(env.OVER_U_DEMO_PASSWORD)
 await p.getByRole('button',{name:'Продолжить',exact:true}).click();await p.waitForURL(u=>!u.pathname.startsWith('/login'))
}
try {
 const guest=await page();await guest.goto(base+'/login');await shot(guest,'20-login')
 await guest.locator('#login_email').fill('ru-invalid@example.com');await guest.locator('#login_password').fill('invalid-localization-check')
 await guest.getByRole('button',{name:'Продолжить',exact:true}).click()
 await guest.waitForTimeout(1800);await shot(guest,'21-login-error')
 assert.match(await guest.locator('body').innerText(),/Неверн|неверн|Неправильн|неправильн/)
 await guest.goto(base+'/login#forgot');await guest.waitForTimeout(500);await shot(guest,'22-password-recovery')
 assert.match(await guest.locator('body').innerText(),/Восстанов|Сброс|Забыли/)
 result.checks.push('Russian guest login, invalid-credentials error and password recovery; no real password/email action.')
 const teacher=await page();await login(teacher,'teacher@over-u.example.com')
 for(const [route,name,wait] of [
  ['/lms/courses/over-u#dashboard','23-teacher-dashboard','Зачислить'],
  ['/lms/quizzes/edit/over-u','24-quiz-editor','Сданные работы'],
  ['/lms/quizzes/new','25-new-quiz','Создать'],
  ['/lms/assignments/new','26-assignment-form','Тип работы'],
 ]) {
  await teacher.goto(base+route);await teacher.waitForTimeout(2500);await shot(teacher,name)
 }
 const fields=teacher.locator('[data-testid="assignment-fields"]');await fields.waitFor()
 await fields.getByRole('combobox',{name:/Формат ответа/}).click()
 await teacher.getByRole('option',{name:'Текст',exact:true}).click()
 assert.equal(await fields.getByRole('combobox',{name:/Формат ответа/}).innerText(),'Текст')
 let draftType
 teacher.on('request',req=>{if(req.url().includes('/api/')&&req.method()==='POST'){try{const body=req.postDataJSON();const doc=typeof body.doc==='string'?JSON.parse(body.doc):body.doc;if(doc?.doctype==='LMS Assignment')draftType=doc.type}catch{}}})
 // An invalid draft is rejected and cannot create a new assignment.
 invalidDraft = true
 await teacher.getByTestId('assignment-save').click();await teacher.waitForTimeout(1200);await shot(teacher,'27-assignment-validation'); invalidDraft = false
 assert.match(await teacher.locator('body').innerText(),/Название|обязатель|заполн|Укажите/i)
 assert.equal(draftType,'Text','Localized option retains technical submission value')
 result.checks.push('Teacher dashboard/student list, existing and new quiz editors, assignment form/select labels and invalid-draft validation. No authoring save succeeds.')
 const student=await page();await login(student,'localization-test@over-u.example.com');await student.goto(base+'/school/courses/no-such-localization-course')
 await student.waitForTimeout(700);await shot(student,'28-access-error');assert.match(await student.locator('body').innerText(),/Ошибка|доступ|найден|загрузить/i)
 result.checks.push('Student missing/forbidden course displays a Russian safe error.')
 assert.deepEqual(result.errors,[]);assert.deepEqual(result.english,[])
 result.status='passed'
} catch(e) {result.status='failed';result.failure=e.message;console.error(e.message);process.exitCode=1}
finally {fs.writeFileSync(out+'extra-validation.json',JSON.stringify(result,null,2));await browser.close()}
