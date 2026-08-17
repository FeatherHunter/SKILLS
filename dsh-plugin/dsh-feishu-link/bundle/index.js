/**
 * dsh-feishu-link · Host 半（npm 安装版 ESM 插件协议）
 *
 * 与动态版 host.js 同源（cordis_define code.host 函数体），仅 export 形态不同：
 *   1. 静态版：`export const name + export const inject + export function apply(ctx)`
 *   2. 动态版：`return { inject: [...], apply(ctx) { ... } }`
 *
 * 内部逻辑（与 host.js 1:1 对齐）：
 *   - 元数据持久化 ~/.dsh/im-bindings/<agentId>.json
 *   - 凭证 DSH credentials ref={ns:'im-lark', id:agentId}
 *   - bind 状态机（begin / 轮询 / success / failed / timeout / cancelled）
 *   - helper 子进程管理（spawn + watchdog 重启 + IPC）
 *   - 7 RPC + 2 model tools
 *
 * sandbox 限制：本模块被 Cordis loader 加载；一切副作用必须走 ctx.get 服务。
 * 与动态版的代码冗余是刻意保留（避免 sandbox 内部的 import 不可靠问题）。
 */

export const name = 'dsh-feishu-link'

// 服务依赖声明（loader 等待就绪后再 apply；npm 安装版必须用 connection.rpc 不能用 harness）
export const inject = ['subprocess', 'timer', 'fs', 'credentials', 'connection', 'tools', 'web']

export function apply(ctx) {
  const subprocess = ctx.get('subprocess')
  const timer = ctx.get('timer')
  const fs = ctx.get('fs')
  const credentials = ctx.get('credentials')
  const connection = ctx.get('connection')
  const toolsSvc = ctx.get('tools')
  const webSvc = ctx.get('web')

  if (!subprocess || !timer || !fs || !credentials || !connection || !connection.rpc) return

  // ============ 配置 ============
  const BINDINGS_DIR = '.dsh/im-bindings'
  const HELPER_REL = '../../helper/helper.mjs'   // 相对本文件（package/lib/index.js）→ 上两级 → helper/helper.mjs
  const POLL_BIND_MS_MIN = 3000
  const POLL_BIND_TIMEOUT_MS = 600000
  const HELPER_RESTART_DELAY_MS = 3000
  const MAX_RECEIVED_BUFFER = 200

  // ============ 状态 ============
  let pluginDirCached = null
  let helperHandle = null
  let helperStdoutParseBuf = ''
  let helperReady = false
  let helperWatchdog = null
  let projectRoot = ''

  const bindSessions = new Map()
  const recentMessages = []

  // ============ 工具函数 ============
  function errText(e) {
    if (!e) return 'unknown error'
    if (typeof e === 'string') return e
    if (typeof e.message === 'string') return e.message
    if (typeof e.error === 'string') return e.error
    try { return JSON.stringify(e) } catch (_) { return String(e) }
  }
  function uid() {
    return 'bind_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
  }
  function bindPath(agentId) { return BINDINGS_DIR + '/' + agentId + '.json' }
  function credRef(agentId) { return { ns: 'im-lark', id: agentId } }

  function resolvePluginDir() {
    if (pluginDirCached) return pluginDirCached
    try {
      const path = require('path')
      // 本文件位于 dsh-feishu-link/package/lib/index.js
      // 插件根 = package 的 .. / ..
      if (typeof __filename === 'string' && __filename) {
        pluginDirCached = path.resolve(path.dirname(__filename), '../..')
      } else {
        pluginDirCached = projectRoot || '.'
      }
    } catch (_) { pluginDirCached = projectRoot || '.' }
    return pluginDirCached
  }
  function getNodePath() {
    try { return process && process.execPath ? process.execPath : 'node' } catch (_) { return 'node' }
  }

  // ============ metadata ============
  async function readBinding(agentId) {
    try {
      const t = await fs.resolve(bindPath(agentId), { cwd: projectRoot || undefined })
      const text = await fs.readText(t)
      return JSON.parse(text)
    } catch (_) { return null }
  }
  async function writeBinding(agentId, data) {
    const t = await fs.resolve(bindPath(agentId), { cwd: projectRoot || undefined })
    await fs.writeText(t, JSON.stringify(data || {}, null, 2), { cwd: projectRoot || undefined })
  }
  async function deleteBinding(agentId) {
    try {
      const t = await fs.resolve(bindPath(agentId), { cwd: projectRoot || undefined })
      await fs.writeText(t, JSON.stringify({ agentId, platform: 'lark', status: 'deleted', deletedAt: Date.now() }, null, 2), { cwd: projectRoot || undefined })
    } catch (_) { /* swallow */ }
  }
  async function listBindings() {
    const out = []
    try {
      const dirTarget = await fs.resolve(BINDINGS_DIR, { cwd: projectRoot || undefined })
      const entries = await fs.listDir(dirTarget)
      for (let i = 0; i < entries.length; i++) {
        const name = (entries[i] && (entries[i].name || entries[i].path)) || ''
        if (!/\.json$/i.test(name)) continue
        try {
          const t = await fs.resolve(BINDINGS_DIR + '/' + name, { cwd: projectRoot || undefined })
          const text = await fs.readText(t)
          const data = JSON.parse(text)
          if (!data || data.status === 'deleted') continue
          if (!data.agentId) data.agentId = name.replace(/\.json$/i, '')
          out.push(data)
        } catch (_) { /* skip */ }
      }
    } catch (_) { /* dir 不存在 = 无绑定 */ }
    return out
  }

  // ============ credentials ============
  async function storeCredentials(agentId, payload) {
    if (!payload || typeof payload !== 'object') return
    const json = JSON.stringify(payload)
    if (!json || json === '{}' || json === 'null') return
    try { await credentials.set(credRef(agentId), json) } catch (_) { /* swallow */ }
  }
  async function loadCredentials(agentId) {
    try {
      const v = await credentials.resolve(credRef(agentId))
      if (!v) return null
      const raw = typeof v.value === 'string' ? v.value : String(v.value || '')
      if (!raw) return null
      return JSON.parse(raw)
    } catch (_) { return null }
  }
  async function clearCredentials(agentId) {
    try { await credentials.unset(credRef(agentId)) } catch (_) { /* ignore */ }
  }

  // ============ web.fetch helper ============
  async function fetchJson(url, init, timeoutMs) {
    const to = (typeof timer.timeout === 'function') ? timer.timeout(timeoutMs || 15000) : new Promise(function (_r, rej) { setTimeout(function () { rej(new Error('timeout')) }, timeoutMs || 15000) })
    if (!webSvc || typeof webSvc.fetch !== 'function') throw { kind: 'no_web_service', message: 'DSH web.fetch 不可用' }
    try {
      return await Promise.race([
        (async function () {
          const o = await webSvc.fetch({ url, ...(init || {}) })
          const status = (o && typeof o.status === 'number') ? o.status : (o && o.ok ? 200 : 0)
          const body = (o && o.body !== undefined) ? o.body : ''
          if (status < 200 || status >= 300) {
            throw { kind: 'http_' + status, message: String(body || '').slice(0, 300) }
          }
          return typeof body === 'string' ? JSON.parse(body) : body
        })(),
        to.then(function () { throw { kind: 'timeout', message: 'fetch timeout: ' + url } }),
      ])
    } catch (e) {
      if (e && e.kind) throw e
      throw { kind: 'network', message: errText(e) }
    }
  }

  // ============ bind 状态机 ============
  function sanitizeSession(s) {
    return {
      bindId: s.bindId, agentId: s.agentId, status: s.status,
      qrContent: s.verificationUriComplete, verificationUriComplete: s.verificationUriComplete,
      appId: s.appId, operatorOpenId: s.operatorOpenId, tenant: s.tenant,
      expiresAt: s.expiresAt, startedAt: s.startedAt, lastError: s.lastError,
    }
  }
  function fireBindChanged(s) {
    try {
    } catch (_) { /* swallow */ }
  }

  async function startBind(args) {
    const agentId = args && args.agentId
    if (!agentId) throw { kind: 'invalid_request', message: 'agentId required' }

    if (!helperReady) {
      for (let i = 0; i < 30; i++) { if (helperReady) break; await new Promise(function (r) { setTimeout(r, 200) }) }
      if (!helperReady) {
        ensureHelperProcess()
        for (let i = 0; i < 50; i++) { if (helperReady) break; await new Promise(function (r) { setTimeout(r, 200) }) }
      }
      if (!helperReady) throw { kind: 'helper_not_ready', message: 'helper 未就绪，请稍后重试' }
    }

    const source = 'dsh-feishu-link'
    const beginForm = {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        action: 'begin', auth_method: 'client_secret',
        request_user_info: 'open_id', source, archetype: 'PersonalAgent',
      }).toString(),
    }
    const beginJ = await fetchJson('https://accounts.feishu.cn/oauth/v1/app/registration', beginForm)
    if (!beginJ || beginJ.code !== 0) {
      throw { kind: 'feishu_begin', message: (beginJ && (beginJ.message || beginJ.msg)) || 'feishu begin failed' }
    }
    const beginData = beginJ.data || {}
    if (!beginData.device_code || !beginData.verification_uri_complete) {
      throw { kind: 'feishu_begin_invalid', message: 'missing device_code / verification_uri_complete' }
    }

    const bindId = uid()
    const session = {
      bindId, agentId, status: 'scan',
      deviceCode: beginData.device_code,
      verificationUriComplete: beginData.verification_uri_complete,
      expiresAt: Date.now() + (beginData.expires_in || 600) * 1000,
      interval: Math.max(POLL_BIND_MS_MIN, (beginData.interval || 5) * 1000),
      lastError: null, startedAt: Date.now(),
    }
    bindSessions.set(bindId, session)
    fireBindChanged(session)

    const poll = async function tick() {
      const s = bindSessions.get(bindId)
      if (!s) return
      if (s.status !== 'scan') return
      if (Date.now() > s.expiresAt + POLL_BIND_TIMEOUT_MS) {
        s.status = 'timeout'; s.lastError = 'expired'
        fireBindChanged(s); bindSessions.delete(bindId); return
      }
      const pollForm = {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ action: 'poll', device_code: s.deviceCode }).toString(),
      }
      let j
      try {
        j = await fetchJson('https://accounts.feishu.cn/oauth/v1/app/registration', pollForm)
      } catch (e) {
        s.lastError = errText(e)
        if (timer && typeof timer.setTimeout === 'function') timer.setTimeout(tick, s.interval)
        else setTimeout(tick, s.interval)
        return
      }
      if (j && j.code === 0) {
        const data = j.data || {}
        s.status = 'success'
        s.appId = data.client_id
        s.appSecret = data.client_secret
        s.operatorOpenId = data.user_info && data.user_info.open_id
        s.tenant = data.tenant || 'feishu'
        fireBindChanged(s)
        try {
          await storeCredentials(s.agentId, {
            appId: s.appId, appSecret: s.appSecret, tenant: s.tenant,
            operatorOpenId: s.operatorOpenId, boundAt: Date.now(),
          })
          await writeBinding(s.agentId, {
            agentId: s.agentId, platform: 'lark', status: 'bound',
            appId: s.appId, operatorOpenId: s.operatorOpenId, tenant: s.tenant, boundAt: Date.now(),
          })
        } catch (e) {
          s.status = 'partial'
          s.lastError = 'credentials/metadata write failed: ' + errText(e)
          fireBindChanged(s); bindSessions.delete(bindId); return
        }
        sendHelperCmd({ cmd: 'startBot', payload: { agentId: s.agentId, appId: s.appId, appSecret: s.appSecret, domain: (s.tenant === 'lark' ? 'lark' : 'feishu') } })
        bindSessions.delete(bindId); return
      }
      if (j && (j.error === 'authorization_pending' || j.code === 'authorization_pending')) {
        // 继续
      } else if (j && (j.error === 'slow_down' || j.code === 'slow_down')) {
        s.interval = Math.min(s.interval * 1.5, 30000)
      } else {
        s.status = 'failed'
        s.lastError = (j && (j.message || j.msg)) || 'poll unknown error'
        fireBindChanged(s); bindSessions.delete(bindId); return
      }
      if (timer && typeof timer.setTimeout === 'function') timer.setTimeout(tick, s.interval)
      else setTimeout(tick, s.interval)
    }
    if (timer && typeof timer.setTimeout === 'function') timer.setTimeout(poll, session.interval)
    else setTimeout(poll, session.interval)
    return session
  }

  async function cancelBind(args) {
    const bindId = args && args.bindId
    const s = bindSessions.get(bindId)
    if (!s) return { ok: true, bindId, status: 'not_found' }
    bindSessions.delete(bindId)
    s.status = 'cancelled'
    fireBindChanged(s)
    return { ok: true, bindId, status: 'cancelled' }
  }

  async function unbind(args) {
    const agentId = args && args.agentId
    if (!agentId) throw { kind: 'invalid_request', message: 'agentId required' }
    sendHelperCmd({ cmd: 'stopBot', payload: { agentId } })
    await clearCredentials(agentId)
    await deleteBinding(agentId)
    try {
    return { ok: true, agentId }
  }

  // ============ helper 进程管理 ============
  function sendHelperCmd(cmd) {
    if (!helperHandle || !helperHandle.stdin) return false
    try {
      helperHandle.stdin.write(JSON.stringify(cmd) + '\n')
      return true
    } catch (_) { return false }
  }

  function ensureHelperProcess() {
    if (helperHandle) return helperHandle
    try {
      const dir = resolvePluginDir()
      const path = require('path')
      const helperPath = path.join(dir, HELPER_REL)
      const nodePath = getNodePath()
      const handle = subprocess.spawn({
        argv: [nodePath, helperPath],
        cwd: dir,
        stdio: {
          stdin: 'pipe',
          stdout: { maxBytes: 1024 * 1024 },
          stderr: { maxBytes: 256 * 1024 },
        },
        graceMs: 2000,
      })
      let parseBuf = ''
      if (handle.collected && handle.collected.stdout) {
        handle.collected.stdout.on('data', function (chunk) {
          parseBuf += chunk.toString('utf8')
          const lines = parseBuf.split('\n')
          parseBuf = lines.pop()
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim()
            if (!line) continue
            let msg = null
            try { msg = JSON.parse(line) } catch (_) { continue }
            if (msg) onHelperMessage(msg)
          }
        })
        handle.collected.stdout.on('end', function () {
          if (parseBuf) { try { onHelperMessage(JSON.parse(parseBuf)) } catch (_) {} parseBuf = '' }
        })
      }
      helperHandle = handle
      helperStdoutParseBuf = ''
      handle.done.then(function () {
        if (helperHandle === handle) {
          helperHandle = null
          helperReady = false
          if (helperWatchdog && typeof timer.clearTimeout === 'function') {
            try { timer.clearTimeout(helperWatchdog) } catch (_) {}
          }
          helperWatchdog = (timer && typeof timer.setTimeout === 'function')
            ? timer.setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
            : setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
        }
      }).catch(function (_) {
        if (helperHandle === handle) { helperHandle = null; helperReady = false }
      })
      return handle
    } catch (_) {
      if (helperWatchdog && typeof timer.clearTimeout === 'function') {
        try { timer.clearTimeout(helperWatchdog) } catch (_) {}
      }
      helperWatchdog = (timer && typeof timer.setTimeout === 'function')
        ? timer.setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
        : setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
      return null
    }
  }

  function onHelperMessage(msg) {
    const t = msg.type
    if (t === 'ready') {
      helperReady = true
      broadcastListOfBots().catch(function () {})
    } else if (t === 'botStarted') {
      try {
    } else if (t === 'botClosed') {
      try {
    } else if (t === 'botFailed') {
      try {
    } else if (t === 'botStalled') {
      try {
    } else if (t === 'message') {
      const m = (msg && msg.payload) || {}
      const item = { agentId: msg.agentId, message: m, receivedAt: Date.now() }
      recentMessages.push(item)
      while (recentMessages.length > MAX_RECEIVED_BUFFER) recentMessages.shift()
      try {
    } else if (t === 'log') {
      // 静默
    }
  }

  async function broadcastListOfBots() {
    if (!helperReady) return
    const bindings = await listBindings()
    if (!bindings.length) return
    const payload = []
    for (let i = 0; i < bindings.length; i++) {
      const b = bindings[i]
      if (!b || b.status === 'deleted') continue
      const c = await loadCredentials(b.agentId)
      if (!c || !c.appId || !c.appSecret) continue
      payload.push({ agentId: b.agentId, appId: c.appId, appSecret: c.appSecret, domain: (b.tenant === 'lark') ? 'lark' : 'feishu' })
    }
    if (payload.length) sendHelperCmd({ cmd: 'broadcastList', payload })
  }

  // ============ im.send ============
  async function ensureFreshToken(c) {
    if (!c) return null
    if (c.accessToken && c.expiresAt && Date.now() < c.expiresAt - 60 * 1000) return c.accessToken
    try {
      const tok = await fetchJson('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ app_id: c.appId, app_secret: c.appSecret }),
      }, 10000)
      if (!tok || tok.code !== 0) return null
      return tok.tenant_access_token
    } catch (_) { return null }
  }
  async function sendIm(args) {
    const agentId = args.agentId
    const c = await loadCredentials(agentId)
    if (!c) return { ok: false, error: { kind: 'not_bound', message: '该 Agent 未绑飞书' } }
    let token = await ensureFreshToken(c)
    if (!token) return { ok: false, error: { kind: 'token_error', message: 'token 获取失败' } }
    try {
      const expiresAt = Date.now() + (2 * 60 * 60 - 60) * 1000
      await storeCredentials(agentId, Object.assign({}, c, { accessToken: token, expiresAt }))
    } catch (_) {}
    const url = 'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=' + (args.receiveIdType || 'chat_id')
    const contentStr = typeof args.content === 'string' ? args.content : JSON.stringify(args.content || { text: '' })
    try {
      const j = await fetchJson(url, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'content-type': 'application/json' },
        body: JSON.stringify({ receive_id: args.chatId, msg_type: args.msgType || 'text', content: contentStr }),
      }, 15000)
      if (!j || j.code !== 0) {
        return { ok: false, error: { kind: 'feishu_send', message: (j && j.msg) || 'send failed' } }
      }
      return { ok: true, messageId: j.data && j.data.message_id, chatId: j.data && j.data.chat_id }
    } catch (e) {
      return { ok: false, error: { kind: 'send_failed', message: errText(e) } }
    }
  }

  // ============ RPC（npm 安装版用 connection.rpc 通道）============
  // 把每个 endpoint 显式映射到一个内部函数 — 避免 dynamic dispatch 的脆弱性
  async function rpcListAgents() {
    const bindings = await listBindings()
    return { ok: true, agents: bindings.map(function (b) { return {
      id: b.agentId, agentId: b.agentId, name: b.agentId,
      bound: b.status === 'bound', platform: b.platform || 'lark',
      appId: b.appId, tenant: b.tenant || 'feishu', status: b.status,
      operatorOpenId: b.operatorOpenId, boundAt: b.boundAt,
    } }) }
  }
  async function rpcBeginBind(args) {
    try {
      const s = await startBind({ agentId: args && args.agentId })
      return { ok: true, bindId: s.bindId, agentId: s.agentId, qrContent: s.verificationUriComplete, verificationUriComplete: s.verificationUriComplete, expiresAt: s.expiresAt, intervalMs: s.interval, status: s.status }
    } catch (e) { return { ok: false, error: (e && e.kind) ? e : { kind: 'unknown', message: errText(e) } } }
  }
  async function rpcPollBind(args) {
    const s = bindSessions.get(args && args.bindId)
    if (!s) return { ok: false, error: { kind: 'not_found', message: 'bindId 失效' } }
    return { ok: true, bind: sanitizeSession(s) }
  }
  async function rpcCancelBind(args) { return await cancelBind({ bindId: args && args.bindId }) }
  async function rpcUnbind(args) {
    try { return { ok: true, ...(await unbind({ agentId: args && args.agentId })) } }
    catch (e) { return { ok: false, error: (e && e.kind) ? e : { kind: 'unknown', message: errText(e) } } }
  }
  async function rpcSend(args) { return await sendIm(args || {}) }
  async function rpcHealth() {
    const bindings = await listBindings()
    return {
      ok: true, helperReady: helperReady,
      helperPid: helperHandle && helperHandle.pid ? helperHandle.pid : null,
      bindsActive: bindSessions.size, recentMessagesCount: recentMessages.length,
      agents: bindings.map(function (b) { return { agentId: b.agentId, status: b.status, appId: b.appId } }),
    }
  }
  async function rpcRecentMessages(args) {
    const agentId = args && args.agentId
    const limit = Math.min(100, Math.max(1, (args && args.limit) || 20))
    const out = agentId ? recentMessages.filter(function (m) { return m.agentId === agentId }).slice(-limit) : recentMessages.slice(-limit)
    return { ok: true, count: out.length, items: out }
  }

  // connection.rpc 通道：dispatch 把 endpoint 映射到具体函数
  const endpointMap = {
    'listAgents': rpcListAgents,
    'beginBind': rpcBeginBind,
    'pollBind': rpcPollBind,
    'cancelBind': rpcCancelBind,
    'unbind': rpcUnbind,
    'send': rpcSend,
    'health': rpcHealth,
    'recentMessages': rpcRecentMessages,
  }
  const dispatch = async function (endpoint, payload) {
    const fn = endpointMap[endpoint]
    if (!fn) throw new Error('unknown endpoint: ' + endpoint)
    return await fn(payload || {})
  }
  connection.rpc.handle('/dsfl', async function (endpoint, payload) {
    try {
      const value = await dispatch(endpoint, payload)
      return { ok: true, value: value }
    } catch (e) {
      return { ok: false, error: { code: 'internal', message: errText(e), details: {} } }
    }
  }, { authority: 'loopback' })

  // ============ Model Tools ============
  if (toolsSvc && typeof toolsSvc.register === 'function') {
    const defSend = {
      name: 'im_send',
      description: '用指定 DSH Agent 的飞书 IM 通道向 chatId 发一条消息。',
      parameters: {
        agentId: { type: 'string', required: true, description: '已绑飞书的 DSH Agent ID' },
        chatId: { type: 'string', required: true, description: '飞书 chat_id 或 open_id' },
        msgType: { type: 'string', enum: ['text', 'post', 'interactive', 'image'], required: false },
        content: { type: 'string', required: true, description: 'JSON 字符串；按 msgType 对应格式' },
        receiveIdType: { type: 'string', enum: ['chat_id', 'open_id', 'email'], required: false },
      },
      output: { schema: { type: 'object' }, render: function (_a, v) { return [{ type: 'text', text: JSON.stringify(v) }] } },
      async execute(args) {
        let contentParsed
        try { contentParsed = JSON.parse(args.content || '{}') } catch (_) { contentParsed = { text: args.content || '' } }
        return await sendIm({ agentId: args.agentId, chatId: args.chatId, msgType: args.msgType || 'text', content: contentParsed, receiveIdType: args.receiveIdType || 'chat_id' })
      },
    }
    toolsSvc.register(defSend)

    const defPull = {
      name: 'im_pull',
      description: '读最近收到的飞书 IM 消息（已在 DSH 内缓存，最多 200 条）。',
      parameters: { agentId: { type: 'string', required: false }, limit: { type: 'number', required: false } },
      output: { schema: { type: 'object' }, render: function (_a, v) { return [{ type: 'text', text: JSON.stringify(v) }] } },
      async execute(args) {
        const lim = Math.min(100, Math.max(1, args.limit || 20))
        const items = args.agentId ? recentMessages.filter(function (m) { return m.agentId === args.agentId }).slice(-lim) : recentMessages.slice(-lim)
        return { ok: true, count: items.length, items: items }
      },
    }
    toolsSvc.register(defPull)
  }

  // ============ 启动 ============
  if (typeof projectRoot !== 'string' || !projectRoot) {
    try { projectRoot = process.cwd() } catch (_) { projectRoot = '' }
  }
  ensureHelperProcess()
}
