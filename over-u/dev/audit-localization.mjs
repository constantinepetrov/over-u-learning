import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const requireFrontend = createRequire(new URL('../../frontend/package.json', import.meta.url))
const babel = requireFrontend('@babel/parser')
const vue = requireFrontend('@vue/compiler-sfc')
const dom = requireFrontend('@vue/compiler-dom')
const strings = new Set(), failures = []
function walk(node) {
  if (!node || typeof node !== 'object') return
  if (node.type === 'CallExpression' && node.callee?.name === '__' && node.arguments[0]?.type === 'StringLiteral') strings.add(node.arguments[0].value)
  for (const [key,value] of Object.entries(node)) {
    if (['loc','extra'].includes(key)) continue
    if (Array.isArray(value)) value.forEach(walk)
    else if (value && typeof value === 'object') walk(value)
  }
}
function script(code) {walk(babel.parse(code, {sourceType:'module', plugins:['typescript']}))}
function template(node) {
  if (!node || typeof node !== 'object') return
  if (node.type === 4 && node.content?.includes('__')) {
    try {walk(babel.parseExpression(node.content, {plugins:['typescript']}))} catch { /* directive statement, not a static translation call */ }
  }
  if (Array.isArray(node.children)) node.children.forEach(template)
  if (Array.isArray(node.props)) node.props.forEach(template)
  for (const key of ['content','exp','arg']) if (typeof node[key] === 'object') template(node[key])
}
function directory(folder) {
  for (const name of fs.readdirSync(folder)) {
    const file = path.join(folder,name)
    if (fs.statSync(file).isDirectory()) {if (!['tests','__tests__'].includes(name)) directory(file);continue}
    if (!/\.(vue|js|ts)$/.test(file) || /\.test\./.test(file)) continue
    const code = fs.readFileSync(file,'utf8')
    try {
      if (file.endsWith('.vue')) {
        const {descriptor} = vue.parse(code)
        for (const tag of [descriptor.script,descriptor.scriptSetup]) if (tag) script(tag.content)
        if (descriptor.template) template(dom.baseParse(descriptor.template.content))
      } else script(code)
    } catch(error) {failures.push({file,error:error.message})}
  }
}
directory(new URL('../../frontend/src/', import.meta.url).pathname)
const baseline = JSON.parse(fs.readFileSync(process.argv[2],'utf8'))
const current = JSON.parse(fs.readFileSync(process.argv[3],'utf8'))
const exempt = new Set([' ','Classplus','LearnDash','Teachmint','Open edX','Frappe Cloud Marketplace','johndoe@example.com','esc'])
const keys=[...strings].filter(k=>!exempt.has(k)).sort()
function coverage(dictionary) {
  const missing=keys.filter(k=>!dictionary[k])
  return {total:keys.length,translated:keys.length-missing.length,percent:Math.round((keys.length-missing.length)/keys.length*10000)/100,missing}
}
const result={scope:'Static __() calls in actual LMS frontend source; excludes tests and documented brands/technical tokens. Not a count of every possible rendered screen.',baseline:coverage(baseline),current:coverage(current),excluded:[...exempt],parseFailures:failures}
fs.writeFileSync(new URL('../evidence/russian-localization/coverage.json',import.meta.url),JSON.stringify(result,null,2)+'\n')
console.log(JSON.stringify({baseline:result.baseline.percent,current:result.current.percent,total:keys.length,missing:result.current.missing,parseFailures:failures},null,2))

if (failures.length || result.current.missing.length) process.exitCode = 1
