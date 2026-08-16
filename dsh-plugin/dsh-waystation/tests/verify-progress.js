// verify-progress.js — dsh-waystation v1.5 T12/T16：进度块解析 + 正文容错 + 渲染契约校验
// 用法: node tests/verify-progress.js（在插件根目录）
// 验证：1) parseProgress 变体解析 2) normalizeBody 容错（字面 \n + BOM） 3) host/package 均带 progress 字段 4) client/package 均含进度渲染
const fs = require('fs')
const host = fs.readFileSync('host.js', 'utf8')
const pkg = fs.readFileSync('package/lib/index.js', 'utf8')
const cli = fs.readFileSync('client.js', 'utf8')
const pcli = fs.readFileSync('package/lib/client.js', 'utf8')
let failed = false
const check = (ok, msg) => { console.log((ok ? '  PASS ' : '  FAIL ') + msg); if (!ok) failed = true }

// 1) parseProgress 单元测试（从 host 提取函数）
const fm = host.match(/function parseProgress\(body\) \{[\s\S]*?\n    \}/)
check(!!fm, 'host 含 parseProgress 定义')
const parseProgress = fm ? eval('(' + fm[0] + ')') : function () { return null }
const cases = [
  ['## 进度：90%\n下一步：x', 90],
  ['## 进度: 100%', 100],
  ['正文\n进度：5%', 5],
  ['## 进度：120%', 100],
  ['## 进度：abc%', null],
  ['无进度内容', null],
  ['## 进度：0%', 0],
  ['## 进度：95%', 95],
  // B4 回归：三级锚定 —— 正文示例/规则文本不劫持标题行进度区（#459/#460 实证）
  ['## 已对齐决定\n3. 每张新票写 ## 进度：0% 基准。\n## 进度：90%', 90],
  ['## 待 grill 点\n- 宽容：## 进度：90% 主格式\n## 进度：95%', 95],
  ['Progress: 40%', 40],
]
cases.forEach(function (c) {
  const got = parseProgress(c[0])
  check(got === c[1], 'parseProgress(' + JSON.stringify(c[0]) + ') = ' + got + '（期望 ' + c[1] + '）')
})

// T16: normalizeBody 容错测试（从 host 提取；字面 \\n 还原 + 剥 BOM）
const nfm = host.match(/function normalizeBody\(raw\) \{[\s\S]*?\n    \}/)
check(!!nfm, 'host 含 normalizeBody 定义（T16）')
const normalizeBody = nfm ? eval('(' + nfm[0] + ')') : function (s) { return String(s || '') }
// 坏格式：BOM + 整篇字面 \\n（无真实换行）
const badBody = String.fromCharCode(0xfeff) + '## Destination\\n\\nDSH-Waystation **v1.5**\\n\\n## Notes\\n\\nnote here'
const normBad = normalizeBody(badBody)
check(!normBad.startsWith(String.fromCharCode(0xfeff)), 'normalizeBody 剥 BOM')
check(normBad.indexOf('\n') >= 0, 'normalizeBody 字面 \\n 还原为真实换行')
check(normBad.indexOf('\\n') < 0, 'normalizeBody 不再含字面 \\\\n')
check(normalizeBody('正常\n正文\n带真实换行') === '正常\n正文\n带真实换行', 'normalizeBody 不误伤正常正文')
check(normalizeBody('') === '', 'normalizeBody 空串安全')
// T16 端到端回归（#463/#445）：parseMapBody 必须经 normalizeBody 接线 —— 坏格式 body（BOM + 字面 \n）恢复 Destination
const pfm = host.match(/function parseMapBody\(body\) \{[\s\S]*?\n    \}/)
check(!!pfm, 'host 含 parseMapBody 定义（T16 端到端）')
const parseMapBody = pfm ? eval('(' + pfm[0] + ')') : function () { return { destination: '', notes: '' } }
const e2eOut = parseMapBody(badBody)
check(e2eOut.destination === 'DSH-Waystation **v1.5**', 'parseMapBody 端到端恢复 Destination（BOM+字面 \\n · #445 场景）')
check(e2eOut.notes === 'note here', 'parseMapBody 端到端恢复 Notes（#445 场景）')

// 2) host/package 均带 progress 字段
check(host.includes('progress: parseProgress'), 'host mapTicket 带 progress')
check(pkg.includes('progress: parseProgress'), 'package index mapTicket 带 progress')
check(pkg.includes('function parseProgress'), 'package index 含 parseProgress')
check(host.includes('nodes{number title state body url'), 'host frag 子票查询含 body（fetchMapsDetail）')
check(pkg.includes('nodes{number title state body url'), 'package index frag 子票查询含 body')
check(host.includes('progress: parseProgress'), 'host mapTicket 带 progress（重复守卫）')
check(host.includes('function normalizeBody'), 'host 含 normalizeBody（重复守卫）')
check(pkg.includes('function normalizeBody'), 'package index 含 normalizeBody')
check(host.includes('normalizeBody(body).split'), 'host parseMapBody 经 normalizeBody 接线（双源）')
check(pkg.includes('normalizeBody(body).split'), 'package index parseMapBody 经 normalizeBody 接线（双源）')

// 3) client/package 均含进度渲染
check(cli.includes('const tProgressBar'), 'client 含 tProgressBar')
check(cli.includes('const tStatusBadge'), 'client 含 tStatusBadge')
check(pcli.includes('const tProgressBar'), 'package client 含 tProgressBar')
check(pcli.includes('const tStatusBadge'), 'package client 含 tStatusBadge')
check(cli.includes("'progress.done'") && cli.includes("'progress.accept'"), 'client 含进度 locale 键')
check(pcli.includes("'progress.done'") && pcli.includes("'progress.accept'"), 'package client 含进度 locale 键')
check(cli.includes('tProgressBar(t)') && cli.includes('tStatusBadge(t)'), 'client 渲染点存在')
check(pcli.includes('tProgressBar(t)') && pcli.includes('tStatusBadge(t)'), 'package client 渲染点存在')
// B4：0% = 未动工（契约）—— tStatus 0 分支 + parseProgress 标题行锚定守卫
check(cli.includes('t.progress <= 0'), 'client tStatus 0% → todo（B4）')
check(pcli.includes('t.progress <= 0'), 'package client tStatus 0% → todo（B4）')
check(host.includes('#{1,6}'), 'host parseProgress 标题行锚定（B4）')
check(pkg.includes('#{1,6}'), 'package parseProgress 标题行锚定（B4）')

// T16: client/package 均含 bodyFormat 契约与追加点
check(cli.includes('"bodyFormat"'), 'client 含 bodyFormat prompt')
check(pcli.includes('"bodyFormat"'), 'package client 含 bodyFormat prompt')
check(cli.includes('const BODY_FORMAT'), 'client 含 BODY_FORMAT 常量')
check(pcli.includes('const BODY_FORMAT'), 'package client 含 BODY_FORMAT 常量')
// 追加点跨行容错（completePrompt 的 + 在上一行末尾，CRLF 源码）：\+ 与 ( 之间允许空白/换行
const appendCount = (s) => (s.match(/\+[\s]*\(BODY_FORMAT \? '\\n\\n' \+ BODY_FORMAT : ''\)/g) || []).length
check(appendCount(cli) === 3, 'client BODY_FORMAT 追加点 ×3（completePrompt + mapExecute + newWayfinder）')
check(appendCount(pcli) === 3, 'package client BODY_FORMAT 追加点 ×3（completePrompt + mapExecute + newWayfinder）')
check(cli.includes('newWayfinderText') && cli.includes('BODY_FORMAT ?') && cli.includes("promptText('newWayfinder'"), 'client newWayfinder 建图入口挂 BODY_FORMAT（F2 补强）')
check(pcli.includes('newWayfinderText') && pcli.includes('BODY_FORMAT ?') && pcli.includes("promptText('newWayfinder'"), 'package client newWayfinder 建图入口挂 BODY_FORMAT（F2 补强）')

if (failed) { console.log('\n存在失败'); process.exit(1) }
console.log('\n全部通过')
