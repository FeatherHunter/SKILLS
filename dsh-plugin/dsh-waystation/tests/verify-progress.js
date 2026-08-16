// verify-progress.js — dsh-waystation v1.5 T12：进度块解析 + 渲染契约校验
// 用法: node tests/verify-progress.js（在插件根目录）
// 验证：1) parseProgress 变体解析 2) host/package 均带 progress 字段 3) client/package 均含进度渲染
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
]
cases.forEach(function (c) {
  const got = parseProgress(c[0])
  check(got === c[1], 'parseProgress(' + JSON.stringify(c[0]) + ') = ' + got + '（期望 ' + c[1] + '）')
})

// 2) host/package 均带 progress 字段
check(host.includes('progress: parseProgress'), 'host mapTicket 带 progress')
check(pkg.includes('progress: parseProgress'), 'package index mapTicket 带 progress')
check(pkg.includes('function parseProgress'), 'package index 含 parseProgress')

// 3) client/package 均含进度渲染
check(cli.includes('const tProgressBar'), 'client 含 tProgressBar')
check(cli.includes('const tStatusBadge'), 'client 含 tStatusBadge')
check(pcli.includes('const tProgressBar'), 'package client 含 tProgressBar')
check(pcli.includes('const tStatusBadge'), 'package client 含 tStatusBadge')
check(cli.includes("'progress.done'") && cli.includes("'progress.accept'"), 'client 含进度 locale 键')
check(pcli.includes("'progress.done'") && pcli.includes("'progress.accept'"), 'package client 含进度 locale 键')
check(cli.includes('tProgressBar(t)') && cli.includes('tStatusBadge(t)'), 'client 渲染点存在')
check(pcli.includes('tProgressBar(t)') && pcli.includes('tStatusBadge(t)'), 'package client 渲染点存在')

if (failed) { console.log('\n存在失败'); process.exit(1) }
console.log('\n全部通过')
