// Operates only on the restored Desk test site; never bypasses Framework setup.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import {chromium} from 'playwright'
const base = 'http://over-u-desk.localhost:8000'
const env = Object.fromEntries(fs.readFileSync(process.env.OVER_U_ENV_FILE || '/workspace/over-u-runtime/dev.env','utf8').trim().split('\n').map(s=>{const i=s.indexOf('=');return[s.slice(0,i),s.slice(i+1)]}))
const b = await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--host-resolver-rules=MAP *.localhost 127.0.0.1']})
try {
 const p=await b.newPage({viewport:{width:1440,height:1000},locale:'ru-RU'})
 await p.goto(base+'/login');await p.locator('#login_email').fill('Administrator');await p.locator('#login_password').fill(env.OVER_U_ADMIN_PASSWORD)
 await p.getByRole('button',{name:'Продолжить',exact:true}).click();await p.waitForURL(u=>!u.pathname.startsWith('/login'));await p.goto(base+'/desk')
 await p.getByRole('button',{name:'Начать настройку',exact:true}).click()
 console.log('Runtime site:',await p.evaluate(()=>({site:frappe.boot.sitename,completed:frappe.boot.setup_wizard_completed_apps})))
 assert.equal(await p.evaluate(()=>frappe.boot.sitename),'over-u-desk.localhost')
 assert.ok(await p.evaluate(()=>frappe.boot.setup_wizard_completed_apps.includes('lms')),'Native setup must skip the upstream demo seeder')
 const language=p.locator('[data-fieldname="language"] input');const russianName=await p.evaluate(()=>frappe.setup.data.lang.codes_to_names.ru);assert.ok(russianName);await language.fill(russianName);await language.press('ArrowDown');await language.press('Enter');await language.press('Tab');await p.waitForTimeout(1200)
 const country=p.locator('[data-fieldname="country"] input');await country.fill('Russia');await country.press('ArrowDown');await country.press('Enter');await country.press('Tab');await p.waitForTimeout(700)
 await p.locator('[data-fieldname="timezone"] select').selectOption('Etc/UTC');await p.locator('[data-fieldname="currency"] select').selectOption('RUB')
 // Display formatting only, not payment integration. Do not enable telemetry.
 for(const name of ['enable_telemetry','allow_recording_first_session']){
  const control=p.locator(`input[data-fieldname="${name}"][type="checkbox"]`);if(await control.count()&&await control.isVisible())await control.uncheck()
 }
 console.log('Selected region:',await p.evaluate(()=>{return Object.fromEntries(['language','country','timezone','currency'].map(key=>[key,document.querySelector(`[data-fieldname="${key}"] input, [data-fieldname="${key}"] select`)?.value]))}))
 p.on('response',async r=>{if(r.url().includes('setup_complete')){let j=await r.json().catch(()=>({}));console.log('Setup response:',r.status(),j.message?.status,j.exc_type)}})
 assert.ok((await country.inputValue()).length,'Choose a country from the native autocomplete')
 const button=p.locator('.complete-btn:visible');console.log('Complete button:',await button.innerText())
 await p.evaluate(()=>{delete frappe.wizard.values.full_name;delete frappe.wizard.values.email;delete frappe.wizard.values.password})
 const completed=p.waitForResponse(r=>r.url().includes('setup_wizard.setup_complete') && r.request().method()==='POST',{timeout:120000})
 await button.click()
 const response=await completed
 assert.equal(response.status(),200)
 assert.equal((await response.json()).message.status,'ok')
 await p.goto(base+'/desk');await p.waitForFunction(()=>window.frappe?.boot?.setup_complete)
 assert.ok(new URL(p.url()).pathname.startsWith('/desk'))
 console.log('Desk setup completed via native wizard:',p.url());console.log(await p.locator('body').innerText())
 await p.screenshot({path:'/workspace/over-u-stage22-private/desk-after-wizard.png',fullPage:true})
}finally{await b.close()}
