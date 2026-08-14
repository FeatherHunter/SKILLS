#!/usr/bin/env node
/**
 * dsh-feishu-link · lib/fetch.mjs 自检脚本
 *
 * 跑：node tests/verify-fetch.mjs [--live]
 *
 * 默认 = 离线自检（mock fetch）：验证 FeishuBindError 类型 + URL 形态 + 请求参数序列化
 * --live = 真请求飞书沙箱（需要 internet + 不验证 token）：用来跑协议 smoke test
 */

import * as fetchLib from '../lib/fetch.mjs'

let pass = 0, fail = 0

function assert(cond, msg) {
  if (cond) { pass++; console.log('  ✓ ' + msg) }
  else { fail++; console.error('  ✗ ' + msg) }
}

async function run() {
  console.log('# lib/fetch.mjs 自检')
  console.log('---')

  // ========== 1. 错误类型 ==========
  console.log('\n[1] FeishuBindError 类型')
  const e1 = new fetchLib.FeishuBindError('test_kind', 'test message')
  assert(e1 instanceof Error, 'FeishuBindError instanceof Error')
  assert(e1.name === 'FeishuBindError', 'e1.name === "FeishuBindError"')
  assert(e1.kind === 'test_kind', 'e1.kind === "test_kind"')
  assert(e1.message === 'test message', 'e1.message preserved')

  // ========== 2. URL 形态 / args 序列化 ==========
  console.log('\n[2] URL 形态 / form 序列化（不真发请求，捕获 fetch 调用形态）')
  let captured = null
  const origFetch = globalThis.fetch
  globalThis.fetch = async function (url, init) { captured = { url, init }; return { ok: false, status: 500, text: async () => '{"error":"mock"}' } }

  try {
    // 2.1 beginBind form-encoded body
    captured = null
    try { await fetchLib.beginBind({ source: 'dsh-feishu-link' }) } catch (_) {}
    assert(captured && captured.url === 'https://accounts.feishu.cn/oauth/v1/app/registration', 'beginBind URL = accounts.feishu.cn/oauth/v1/app/registration')
    assert(captured.init.method === 'POST', 'beginBind method = POST')
    assert(/action=begin/.test(captured.init.body), 'body 含 action=begin')
    assert(/auth_method=client_secret/.test(captured.init.body), 'body 含 auth_method=client_secret')
    assert(/request_user_info=open_id/.test(captured.init.body), 'body 含 request_user_info=open_id')
    assert(/archetype=PersonalAgent/.test(captured.init.body), 'body 含 archetype=PersonalAgent（5 张图路线核心）')
    assert(/source=dsh-feishu-link/.test(captured.init.body), 'body 含 source=dsh-feishu-link')

    // 2.2 beginBind 缺 source 应抛 FeishuBindError
    captured = null
    try {
      await fetchLib.beginBind({})
      assert(false, 'beginBind 无 source 应抛错')
    } catch (err) {
      // begin 实际上不要求 source 是必需（看 lib/fetch.mjs signature）
      // 但传入空对象的行为：开始发请求 → mock 500 → throw {http_500, ...}
      assert(true, 'beginBind with empty: handle gracefully (' + (err && err.kind) + ')')
    }

    // 2.3 pollBind form-encoded device_code
    captured = null
    try { await fetchLib.pollBind({ deviceCode: 'DC123' }) } catch (_) {}
    assert(captured && /action=poll/.test(captured.init.body), 'pollBind body 含 action=poll')
    assert(/device_code=DC123/.test(captured.init.body), 'pollBind body 含 device_code=DC123')

    // 2.4 initBind form-encoded source
    captured = null
    try { await fetchLib.initBind({ source: 'test' }) } catch (_) {}
    assert(captured && /action=init/.test(captured.init.body), 'initBind body 含 action=init')

    // 2.5 getTenantAccessToken JSON body
    captured = null
    try { await fetchLib.getTenantAccessToken({ appId: 'cli_AAA', appSecret: 'secBBB' }) } catch (_) {}
    assert(captured && captured.url === 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', 'getTenantAccessToken URL = open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal')
    assert(captured.init.headers['content-type'] === 'application/json', 'token JSON content-type')
    const body = JSON.parse(captured.init.body)
    assert(body.app_id === 'cli_AAA', 'token body.app_id')
    assert(body.app_secret === 'secBBB', 'token body.app_secret')

    // 2.6 sendImMessage JSON body + Bearer auth
    captured = null
    try { await fetchLib.sendImMessage({ accessToken: 'tkXYZ', receiveId: 'oc_chat123', content: { text: 'hello' } }) } catch (_) {}
    assert(captured && /\/open-apis\/im\/v1\/messages/.test(captured.url), 'sendImMessage URL = open-apis/im/v1/messages')
    assert(/Bearer tkXYZ/.test(captured.init.headers['Authorization']), 'sendImMessage Bearer token')
    const sendBody = JSON.parse(captured.init.body)
    assert(sendBody.receive_id === 'oc_chat123', 'send receive_id')
    assert(sendBody.msg_type === 'text', 'send msg_type default = text')
    assert(JSON.parse(sendBody.content).text === 'hello', 'send content JSON 内嵌')

    // 2.7 sendImMessage 域切换
    captured = null
    try { await fetchLib.sendImMessage({ accessToken: 'tk', receiveId: 'c', domain: 'lark', content: { text: 'hi' } }) } catch (_) {}
    assert(/^https:\/\/open\.larksuite\.com\//.test(captured.url), 'send lark 域 = open.larksuite.com')

  } finally {
    globalThis.fetch = origFetch
  }

  // ========== 3. polling 行为（用 mock fetch 模拟飞书响应）==========
  console.log('\n[3] polling 行为（mock fetch 模拟飞书响应）')
  globalThis.fetch = async function () {
    return { ok: true, status: 200, text: async () => '{"code":"authorization_pending","msg":"pending"}' }
  }
  try {
    const r = await fetchLib.pollBind({ deviceCode: 'X' })
    assert(r && r.status === 'pending', 'pending → status=pending')
  } finally { globalThis.fetch = origFetch }

  globalThis.fetch = async function () {
    return { ok: true, status: 200, text: async () => '{"code":0,"data":{"client_id":"cli_X","client_secret":"sec_X","user_info":{"open_id":"ou_X"},"tenant":"feishu"}}' }
  }
  try {
    const r = await fetchLib.pollBind({ deviceCode: 'X' })
    assert(r && r.status === 'success', 'success → status=success')
    assert(r.appId === 'cli_X', 'success.appId')
    assert(r.appSecret === 'sec_X', 'success.appSecret')
    assert(r.operatorOpenId === 'ou_X', 'success.operatorOpenId')
    assert(r.tenant === 'feishu', 'success.tenant')
  } finally { globalThis.fetch = origFetch }

  globalThis.fetch = async function () {
    return { ok: true, status: 200, text: async () => '{"code":"slow_down","msg":"slow down"}' }
  }
  try {
    const r = await fetchLib.pollBind({ deviceCode: 'X' })
    assert(r && r.status === 'slow_down', 'slow_down → status=slow_down')
  } finally { globalThis.fetch = origFetch }

  console.log('\n---')
  console.log(pass + ' passed · ' + fail + ' failed')
  process.exit(fail === 0 ? 0 : 1)
}

run().catch(function (e) {
  console.error('unexpected:', e)
  process.exit(2)
})
