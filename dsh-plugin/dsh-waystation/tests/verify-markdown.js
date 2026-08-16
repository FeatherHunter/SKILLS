// verify-markdown.js — dsh-waystation v1.5 T17：markdown 白名单渲染契约校验
// 用法: node tests/verify-markdown.js（在插件根目录）
const fs = require('fs')
const cli = fs.readFileSync('client.js', 'utf8')
const pcli = fs.readFileSync('package/lib/client.js', 'utf8')
let failed = false
const check = (ok, msg) => { console.log((ok ? '  PASS ' : '  FAIL ') + msg); if (!ok) failed = true }

// 提取整段渲染器（mdInline 起 → mdToHtml 结束）
const extract = function (src) {
  const i = src.indexOf('const MD_LINK_RE')
  if (i < 0) return ''
  const end = src.indexOf('// ============================================================', i + 10)
  return end > i ? src.slice(i, end) : src.slice(i, i + 9000)
}
const mdCli = extract(cli)
const mdPkg = extract(pcli)

check(mdCli.length > 0, 'client 含渲染器（MD_LINK_RE 起）')
check(mdPkg.length > 0, 'package client 含渲染器')
check(cli.includes('const mdToHtml = function'), 'client 含 mdToHtml 定义')
check(pcli.includes('const mdToHtml = function'), 'package 含 mdToHtml 定义')

// 渲染点接入
check(cli.includes('mdToHtml(m.notes)'), 'client Notes 渲染接入')
check(cli.includes("mdToHtml('· ' + f)"), 'client Fog 渲染接入')
check(cli.includes("mdToHtml('· ' + o)"), 'client OutOfScope 渲染接入')
check(pcli.includes('mdToHtml(m.notes)'), 'package Notes 渲染接入')
check(pcli.includes("mdToHtml('· ' + f)"), 'package Fog 渲染接入')
check(pcli.includes("mdToHtml('· ' + o)"), 'package OutOfScope 渲染接入')

// 白名单标签
const tags = ['strong', 'em', 'code', 'ul', 'li', 'blockquote', 'input', 'a', 'hr', 'div']
tags.forEach(function (t) {
  check(mdCli.includes("h('" + t + "',") || mdCli.includes("h('" + t + "')"), '渲染器构造 ' + t)
})

// 语法正则
check(mdCli.includes('MD_LINK_RE'), '链接正则定义')
check(mdCli.includes('MD_TASK_RE'), '任务项正则定义')

// 防注入
check(!mdCli.includes('dangerouslySetInnerHTML'), '渲染器不使用 dangerouslySetInnerHTML')
check(!mdCli.includes('innerHTML'), '渲染器不直接操作 innerHTML')
check(!mdPkg.includes('dangerouslySetInnerHTML'), 'package 渲染器不使用 dangerouslySetInnerHTML')

// 双源一致
check(Math.abs(mdCli.length - mdPkg.length) < 50, '双源渲染器体量一致 (' + mdCli.length + ' vs ' + mdPkg.length + ')')

if (failed) { console.log('\n存在失败'); process.exit(1) }
console.log('\n全部通过')
