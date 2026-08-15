#!/usr/bin/env node
/**
 * dsh-feishu-link · cordis sandbox 限制探测（ROADMAP A3）
 *
 * 跑：node tests/probe-sandbox.mjs
 *
 * 目的：在带 cordis 工具的 DSH 会话里跑这个脚本，
 *   实际回答"cordis code.host 函数体能用什么，不能用什么"
 * 之前我写代码时凭假设（`require('path')` / `__filename` / `process.cwd` 是否可用），
 * 现在真实测一次。
 *
 * 用法：用户/agent 在 DSH 环境加载此脚本，print 报告表，按需修改 host.js 兜底顺序。
 */

const report = []

function tryOp(name, op) {
  try {
    const result = op()
    report.push({ op: name, ok: true, sample: String(result).slice(0, 80) })
    return result
  } catch (e) {
    report.push({ op: name, ok: false, error: String((e && e.message) || e).slice(0, 120) })
    return undefined
  }
}

console.log('# cordis sandbox 能力探测')
console.log('# (in code.host function body context, run in DSH harness with cordis)')
console.log('---')

// ============ Globals ============
console.log('\n## Globals')

tryOp('typeof process', function () { return typeof process })
tryOp('typeof globalThis', function () { return typeof globalThis })
tryOp('typeof self', function () { return typeof self })
tryOp('typeof window', function () { return typeof window })

// ============ Module-scoped variables ============
console.log('\n## Module-scoped variables')

tryOp('typeof __filename', function () { return typeof __filename })
tryOp('typeof __dirname', function () { return typeof __dirname })
tryOp('typeof module', function () { return typeof module })
tryOp('typeof exports', function () { return typeof exports })
tryOp('typeof require', function () { return typeof require })

// ============ Node built-ins (common require attempts) ============
console.log('\n## Node built-ins via require')

tryOp('require("path")', function () {
  const p = require('path')
  return p && p.basename ? 'path module loaded' : 'no path module'
})
tryOp('require("url")', function () {
  const u = require('url')
  return u && u.parse ? 'url module loaded' : 'no url module'
})
tryOp('require("crypto")', function () {
  const c = require('crypto')
  return c && c.randomBytes ? 'crypto module loaded' : 'no crypto module'
})
tryOp('require("os")', function () { return 'os module loaded' })

// ============ process methods ============
console.log('\n## process methods')

tryOp('process.cwd()', function () { return process.cwd() })
tryOp('process.execPath', function () { return process.execPath })
tryOp('process.env.PWD', function () { return process.env.PWD || '(empty)' })
tryOp('process.env.USERPROFILE', function () { return process.env.USERPROFILE || '(empty)' })
tryOp('process.env.DSH_HOME', function () { return process.env.DSH_HOME || '(empty)' })
tryOp('process.versions.node', function () { return process.versions.node })

// ============ URL & URLSearchParams (native) ============
console.log('\n## Native URL/URLSearchParams')

tryOp('typeof URLSearchParams', function () { return typeof URLSearchParams })
tryOp('typeof fetch', function () { return typeof fetch })

// ============ Async / Await / Promise ============
console.log('\n## ES2023 async features')

tryOp('typeof async', function () {
  // 不能'直接 typeof async'，验证 async fn 可用
  return (async function () { return 1 }).constructor.name
})

// ============ DSH ctx services (assumed available) ============
console.log('\n## DSH ctx services (these are passed in by cordis; we can probe but cannot call without ctx arg)')

tryOp('typeof ctx', function () { return typeof ctx })
tryOp('typeof host', function () { return typeof host })
tryOp('typeof harness', function () { return typeof harness })
tryOp('typeof timer', function () { return typeof timer })
tryOp('typeof fs', function () { return typeof fs })
tryOp('typeof subprocess', function () { return typeof subprocess })
tryOp('typeof credentials', function () { return typeof credentials })
tryOp('typeof web', function () { return typeof web })
tryOp('typeof tools', function () { return typeof tools })

// ============ Report ============
console.log('\n---')
console.log('# Report Summary')
console.log('| operation | ok | sample/error |')
console.log('|-----------|----|----|')
for (let i = 0; i < report.length; i++) {
  const r = report[i]
  const v = r.ok ? (r.sample || '(empty)') : (r.error || 'unknown')
  console.log('| ' + r.op + ' | ' + (r.ok ? '✓' : '✗') + ' | `' + v + '` |')
}

console.log('')
console.log('# Quick decision matrix')
console.log('| Symbol | Can code.host use? | Fallback strategy |')
console.log('|--------|-----|-----|')
for (let i = 0; i < report.length; i++) {
  const r = report[i]
  let fallback = '(none needed)'
  if (r.op === 'typeof process' || r.op === 'typeof __filename' || r.op === 'typeof __dirname') {
    fallback = r.ok ? 'use directly' : 'use pluginRoot passed from outer scope; fallback to NPM_PLUGIN_DIR / process.env.DSH_HOME / "."'
  }
  if (r.op.indexOf('require(') === 0) {
    fallback = r.ok ? 'use directly' : 'inline path manipulation (no require)'
  }
  if (r.op === 'typeof fetch') {
    fallback = r.ok ? 'use for HTTP' : 'use ctx.web.fetch via ctx.get("web")'
  }
  if (r.op === 'typeof URLSearchParams') {
    fallback = r.ok ? 'use for form encoding' : 'hand-roll url encoding'
  }
  if (r.op.indexOf('ctx services') >= 0 || r.op.indexOf('typeof ctx') === 0 || r.op.indexOf('typeof host') === 0) {
    fallback = 'via ctx.get(name) — safe in cordis sandbox'
  }
  console.log('| `' + r.op + '` | ' + (r.ok ? 'YES' : 'NO') + ' | ' + fallback + ' |')
}

console.log('')
console.log('# Instructions for agent:')
console.log('# 1. Run this in a DSH session that has cordis tools loaded')
console.log('# 2. Read the report above')
console.log('# 3. For each "NO", update host.js fallback order to prefer the YES alternatives')
console.log('# 4. If "typeof harness" is YES, prefer harness.handle over connection.rpc.handle for host RPCs in dynamic version')
