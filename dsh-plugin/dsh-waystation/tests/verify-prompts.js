// verify-prompts.js — dsh-waystation v1.5 方案 A：prompt 注册表契约校验
// 用法: node tests/verify-prompts.js [file...]（默认 client.js + package/lib/client.js）
// 验证：
//   1) 注册表条目结构（version/placeholders/use/zh/en 齐全）
//   2) 文本内 {x} 占位符 与 placeholders 声明一致（未知占位符 = 违规）
//   3) 代码中 promptText('id') 引用全部存在
//   4) 双源注册表键集合一致
const fs = require('fs')
const files = process.argv.slice(2)
const targets = files.length ? files : ['client.js', 'package/lib/client.js']
let failed = false
const unescapeStr = function (s) {
  let out = ''
  for (let i = 0; i < s.length; i++) {
    const c = s[i]
    if (c === '\\' && i + 1 < s.length) { out += s[i + 1] === 'n' ? '\n' : s[i + 1]; i++ }
    else out += c
  }
  return out
}
const parseRegistry = function (src) {
  const reg = {}
  const entryRe = /^\s*"([a-zA-Z0-9.]+)": \{ version: (\d+), placeholders: \[([^\]]*)\], use: '([^']*)', zh: '([^']*)', en: '([^']*)' \},?$/gm
  let m
  while ((m = entryRe.exec(src)) !== null) {
    const ph = m[3] ? m[3].split(',').map(function (x) { return x.trim().replace(/'/g, '') }).filter(Boolean) : []
    reg[m[1]] = { version: Number(m[2]), placeholders: ph, use: m[4], zh: unescapeStr(m[5]), en: unescapeStr(m[6]) }
  }
  return reg
}
const check = function (file) {
  const src = fs.readFileSync(file, 'utf8')
  const reg = parseRegistry(src)
  const problems = []
  if (Object.keys(reg).length < 14) problems.push('注册表条目数异常 ' + Object.keys(reg).length + '（期望 14）')
  Object.keys(reg).forEach(function (id) {
    const p = reg[id]
    if (!(p.version >= 1)) problems.push(id + ' 缺 version')
    if (!p.zh || !p.en) problems.push(id + ' 缺 zh/en')
    if (!p.use) problems.push(id + ' 缺 use')
    const found = []
    const re = /\{(\w+)\}/g
    let mm
    while ((mm = re.exec(p.zh)) !== null) if (found.indexOf(mm[1]) < 0) found.push(mm[1])
    found.forEach(function (x) { if (p.placeholders.indexOf(x) < 0) problems.push(id + ' 文本含未声明占位符 {' + x + '}') })
    p.placeholders.forEach(function (x) { if (found.indexOf(x) < 0) problems.push(id + ' 声明占位符 {' + x + '} 但文本未使用') })
  })
  const useRe = /promptText\('([a-zA-Z0-9.]+)'/g
  let mu
  while ((mu = useRe.exec(src)) !== null) { if (!reg[mu[1]]) problems.push('引用不存在的 prompt id: ' + mu[1]) }
  // 旧形式残留
  ;["tr('prompt.", "'prompt.\'" ].forEach(function (bad) { if (src.includes(bad)) problems.push('旧字典引用残留 ' + bad) })
  if (problems.length) { console.log('  FAIL', file, problems.join('；')); failed = true }
  else console.log('  PASS', file, '(' + Object.keys(reg).length + ' 条注册表，' + (src.match(/promptText\(/g) || []).length + ' 处引用)')
}
console.log('P1: prompt 注册表契约')
targets.forEach(check)
// 双源键一致性
const a = parseRegistry(fs.readFileSync(targets[0], 'utf8'))
const b = parseRegistry(fs.readFileSync(targets[1], 'utf8'))
const ka = Object.keys(a).sort().join(',')
const kb = Object.keys(b).sort().join(',')
if (ka !== kb) { console.log('  FAIL 双源注册表键不一致'); failed = true }
else console.log('  PASS 双源注册表键一致 (' + Object.keys(a).length + ' 键)')
if (failed) { console.log('\n存在失败'); process.exit(1) }
console.log('\n全部通过')
