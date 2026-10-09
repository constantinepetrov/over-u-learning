// Verify English remains selectable. Changes only the isolated browser fixture.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import {chromium} from 'playwright'
const env=Object.fromEntries(fs.readFileSync(process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env','utf8').trim().split('\n').map(s=>{const i=s.indexOf('=');return[s.slice(0,i),s.slice(i+1)]}))
const base=process.env.OVER_U_BASE_URL || 'http://over-u.localhost:8000'
const out=new URL('../evidence/russian-localization/language-validation.json',import.meta.url).pathname
const fixture='localization-test@over-u.example.com'
const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--host-resolver-rules=MAP over-u.localhost 127.0.0.1']})
let admin, changed=false
const result={checks:[]}
async function login(user,password) {
 const context=await b.newContext();const p=await context.newPage()
 await p.goto(base+'/login');await p.locator('#login_email').fill(user);await p.locator('#login_password').fill(password)
 await p.getByRole('button',{name:'Продолжить',exact:true}).click();await p.waitForURL(u=>!u.pathname.startsWith('/login'));return p
}
async function language(value) {
 return admin.evaluate(async({fixture,value})=>{
  const r=await fetch('/api/method/frappe.client.set_value',{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':JSON.parse(document.getElementById('school-boot').textContent).csrf_token},body:JSON.stringify({doctype:'User',name:fixture,fieldname:'language',value})})
  if(!r.ok)throw new Error('Fixture language change failed: '+r.status)
 },{fixture,value})
}
try {
 admin=await login('Administrator',env.OVER_U_ADMIN_PASSWORD)
 await admin.goto(base+'/school');await admin.locator('#school-boot').waitFor({state:'attached'})
 await language('en');changed=true
 const p=await login(fixture,env.OVER_U_DEMO_PASSWORD);await p.goto(base+'/school');await p.locator('.course-feature').waitFor()
 assert.equal(await p.locator('html').getAttribute('lang'),'en');await p.getByRole('link',{name:'Home',exact:true}).waitFor()
 assert.ok((await p.locator('body').innerText()).includes('Основы осознанного обучения'))
 await p.goto(base+'/lms/courses');await p.getByRole('link',{name:'Courses',exact:true}).first().waitFor()
 result.checks.push('English User.language works for /school and /lms; authored Russian course content is unchanged.')
 result.status='passed'
} catch(e) {result.status='failed';result.failure=e.message;process.exitCode=1}
finally {
 if(changed)try{await language('ru');result.restoredRussian=true}catch(e){result.status='failed';result.restoreFailure=e.message;process.exitCode=1}
 fs.writeFileSync(out,JSON.stringify(result,null,2));console.log(result.status);await b.close()
}
