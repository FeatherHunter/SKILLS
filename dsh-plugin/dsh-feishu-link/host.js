/**
 * dsh-feishu-link · Host 半（cordis_define code.host 函数体）
 *
 * 本文件是 cordis_define code.host 的函数体直接源码；返回 {inject, apply(ctx)}。
 *
 * 实现清单（按 RESEARCH-im-binding.md §10.6 + DESIGN-concept.md §2 + ADR-GRILLING-UX）：
 *   1. 元数据持久化：~/.dsh/im-bindings/<agentId>.json（fs 服务读/写）
 *   2. 凭证：DSH credentials 服务 ref={ns:'im-lark', id:agentId}（JSON 整体存）
 *   3. bind 状态机：begin → poll timer 循环 → success/failed/timeout/cancelled
 *   4. WSS 长连接管理：subprocess.spawn helper.mjs，stdin/stdout JSON RPC
 *   5. 7 RPC（harness.handle）：listAgents / beginBind / pollBind / cancelBind / unbind / send / health / listHelpers
 *   6. 2 model tools（harness.registerTool → tools.register）：im_send / im_pull
 *   7. 1 host→client 单向推送：im.bind.changed + im.message.received（harness.handleEvent）
 *   8. timer：自动轮询 bind + helper watchdog 重启 + 最近消息 ring buffer
 *
 * sandbox 限制：本函数体不引入外部模块（一切通过 ctx.get 拿）；fs / subprocess / timer / credentials 是硬依赖。
 * web.fetch 通过 ctx.get('web') 走（im.send / token 刷新 / 设备流调用）
 *
 * 与 helper.mjs 的通讯协议：见 lib/ipc.mjs
 */

return {
  // ====== 硬依赖 ======
  inject: ['subprocess', 'timer', 'fs', 'credentials', 'harness', 'tools', 'web'],

  apply(ctx) {
    const subprocess = ctx.get('subprocess')
    const timer = ctx.get('timer')
    const fs = ctx.get('fs')
    const credentials = ctx.get('credentials')
    const harness = ctx.get('harness')
    const toolsSvc = ctx.get('tools')
    const webSvc = ctx.get('web')

    // 缺一个硬依赖就不挂（避免挂一半崩）
    if (!subprocess || !timer || !fs || !credentials || !harness) return

    // ============ 配置 ============
    const BINDINGS_DIR = '.dsh/im-bindings'
    const HELPER_REL = 'helper/helper.mjs'
    const POLL_BIND_MS_MIN = 3000
    const POLL_BIND_TIMEOUT_MS = 600000        // 10 分钟
    const HELPER_RESTART_DELAY_MS = 3000       // 3s
    const MAX_RECEIVED_BUFFER = 200

    // ============ 状态 ============
    let pluginDirCached = null
    let helperHandle = null          // DSH subprocess handle
    let helperStdoutParseBuf = ''    // stdio 行解析缓存
    let helperReady = false
    let helperWatchdog = null
    let projectRoot = ''

    /** @type {Map<string, any>} */ const bindSessions = new Map()  // bindId -> session
    /** @type {Array<{agentId:string, message:any, receivedAt:number}>} */
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
        if (typeof __filename === 'string' && __filename) {
          pluginDirCached = path.dirname(__filename)
        } else if (typeof __dirname === 'string' && __dirname) {
          pluginDirCached = __dirname
        } else {
          pluginDirCached = projectRoot || '.'
        }
      } catch (_) {
        pluginDirCached = projectRoot || '.'
      }
      return pluginDirCached
    }

    function getNodePath() {
      try { return process && process.execPath ? process.execPath : 'node' } catch (_) { return 'node' }
    }

    // ============ metadata（fs 服务）============
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

    // ============ credentials 服务 ============
    async function storeCredentials(agentId, payload) {
      if (!payload || typeof payload !== 'object') return
      const json = JSON.stringify(payload)
      if (!json || json === '{}' || json === 'null') return
      try {
        await credentials.set(credRef(agentId), json)
      } catch (e) {
        // credentials 服务对空字符串/非字符串抛错；我们应该不会走到这里
      }
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

    // ============ web.fetch 工具（注入超时 + JSON 解析）============
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
        bindId: s.bindId,
        agentId: s.agentId,
        status: s.status,
        qrContent: s.verificationUriComplete,
        verificationUriComplete: s.verificationUriComplete,
        appId: s.appId,
        operatorOpenId: s.operatorOpenId,
        tenant: s.tenant,
        expiresAt: s.expiresAt,
        startedAt: s.startedAt,
        lastError: s.lastError,
      }
    }
    function fireBindChanged(s) {
      try {
        if (typeof harness.handleEvent === 'function') harness.handleEvent('im.bind.changed', sanitizeSession(s))
      } catch (_) { /* swallow */ }
    }

    async function startBind(args) {
      const agentId = args && args.agentId
      if (!agentId) throw { kind: 'invalid_request', message: 'agentId required' }

      // 先确保 helper 已经启动（且 ready）
      if (!helperReady) {
        // 等一会儿（短轮询）
        for (let i = 0; i < 30; i++) {
          if (helperReady) break
          await new Promise(function (r) { setTimeout(r, 200) })
        }
        if (!helperReady) {
          // helper 还没启动；先启
          ensureHelperProcess()
          // 再等最多 10s
          for (let i = 0; i < 50; i++) {
            if (helperReady) break
            await new Promise(function (r) { setTimeout(r, 200) })
          }
        }
        if (!helperReady) {
          throw { kind: 'helper_not_ready', message: 'helper 未就绪，请稍后重试' }
        }
      }

      // 设备流 begin
      const source = 'dsh-feishu-link'
      const beginForm = {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          action: 'begin',
          auth_method: 'client_secret',
          request_user_info: 'open_id',
          source,
          archetype: 'PersonalAgent',
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
        bindId,
        agentId,
        status: 'scan',
        deviceCode: beginData.device_code,
        verificationUriComplete: beginData.verification_uri_complete,
        expiresAt: Date.now() + (beginData.expires_in || 600) * 1000,
        interval: Math.max(POLL_BIND_MS_MIN, (beginData.interval || 5) * 1000),
        lastError: null,
        startedAt: Date.now(),
      }
      bindSessions.set(bindId, session)
      fireBindChanged(session)

      // 启动轮询（递归 setTimeout，不重叠）
      const poll = async function tick() {
        const s = bindSessions.get(bindId)
        if (!s) return
        if (s.status !== 'scan') return
        if (Date.now() > s.expiresAt + POLL_BIND_TIMEOUT_MS) {
          s.status = 'timeout'
          s.lastError = 'expired'
          fireBindChanged(s)
          bindSessions.delete(bindId)
          return
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
          // 网络错误：延后重试
          s.lastError = errText(e)
          if (timer && typeof timer.setTimeout === 'function') {
            timer.setTimeout(tick, s.interval)
          } else {
            setTimeout(tick, s.interval)
          }
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
          // 持久化
          try {
            await storeCredentials(s.agentId, {
              appId: s.appId,
              appSecret: s.appSecret,
              tenant: s.tenant,
              operatorOpenId: s.operatorOpenId,
              boundAt: Date.now(),
            })
            await writeBinding(s.agentId, {
              agentId: s.agentId,
              platform: 'lark',
              status: 'bound',
              appId: s.appId,
              operatorOpenId: s.operatorOpenId,
              tenant: s.tenant,
              boundAt: Date.now(),
            })
          } catch (e) {
            s.status = 'partial'
            s.lastError = 'credentials/metadata write failed: ' + errText(e)
            fireBindChanged(s)
            bindSessions.delete(bindId)
            return
          }
          // 启动 helper bot
          sendHelperCmd({ cmd: 'startBot', payload: { agentId: s.agentId, appId: s.appId, appSecret: s.appSecret, domain: (s.tenant === 'lark' ? 'lark' : 'feishu') } })
          bindSessions.delete(bindId)
          return
        }
        if (j && (j.error === 'authorization_pending' || j.code === 'authorization_pending')) {
          // 继续轮询
        } else if (j && (j.error === 'slow_down' || j.code === 'slow_down')) {
          s.interval = Math.min(s.interval * 1.5, 30000)
        } else {
          s.status = 'failed'
          s.lastError = (j && (j.message || j.msg)) || 'poll unknown error'
          fireBindChanged(s)
          bindSessions.delete(bindId)
          return
        }
        if (timer && typeof timer.setTimeout === 'function') {
          timer.setTimeout(tick, s.interval)
        } else {
          setTimeout(tick, s.interval)
        }
      }
      // 首次轮询延迟 interval（让飞书侧有时间响应 begin）
      if (timer && typeof timer.setTimeout === 'function') {
        timer.setTimeout(poll, session.interval)
      } else {
        setTimeout(poll, session.interval)
      }
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
        if (typeof harness.handleEvent === 'function') {
          harness.handleEvent('im.bind.changed', { agentId, status: 'unbound', updatedAt: Date.now() })
        }
      } catch (_) {}
      return { ok: true, agentId }
    }

    // ============ helper 进程管理 ============
    function sendHelperCmd(cmd) {
      if (!helperHandle || !helperHandle.stdin) return false
      try {
        const json = JSON.stringify(cmd)
        helperHandle.stdin.write(json + '\n')
        return true
      } catch (_) { return false }
    }

    function ensureHelperProcess() {
      if (helperHandle) {
        // 已存在；不做二次启动
        return helperHandle
      }
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

        // stdout 解析
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
            if (parseBuf) {
              try { onHelperMessage(JSON.parse(parseBuf)) } catch (_) {}
              parseBuf = ''
            }
          })
        }
        helperHandle = handle
        helperStdoutParseBuf = ''

        handle.done.then(function () {
          if (helperHandle === handle) {
            helperHandle = null
            helperReady = false
            // watchdog 重启
            if (helperWatchdog && typeof timer.clearTimeout === 'function') {
              try { timer.clearTimeout(helperWatchdog) } catch (_) {}
            }
            helperWatchdog = (timer && typeof timer.setTimeout === 'function')
              ? timer.setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
              : setTimeout(function () { ensureHelperProcess() }, HELPER_RESTART_DELAY_MS)
          }
        }).catch(function (e) {
          if (helperHandle === handle) {
            helperHandle = null
            helperReady = false
          }
        })
        return handle
      } catch (e) {
        // spawn 失败 → 退避重试
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
        // 把已绑定的 agent 喂给 helper
        broadcastListOfBots().catch(function (e) { /* swallow */ })
      } else if (t === 'botStarted') {
        try {
          if (typeof harness.handleEvent === 'function') {
            harness.handleEvent('im.bind.changed', { agentId: msg.agentId, status: 'connected', ts: msg.ts })
          }
        } catch (_) {}
      } else if (t === 'botClosed') {
        try {
          if (typeof harness.handleEvent === 'function') {
            harness.handleEvent('im.bind.changed', { agentId: msg.agentId, status: 'closed', reason: msg.reason, ts: msg.ts })
          }
        } catch (_) {}
      } else if (t === 'botFailed') {
        try {
          if (typeof harness.handleEvent === 'function') {
            harness.handleEvent('im.bind.changed', { agentId: msg.agentId, status: 'failed', error: msg.error, ts: msg.ts })
          }
        } catch (_) {}
      } else if (t === 'botStalled') {
        try {
          if (typeof harness.handleEvent === 'function') {
            harness.handleEvent('im.bind.changed', { agentId: msg.agentId, status: 'reconnecting', ageMs: msg.ageMs, ts: msg.ts })
          }
        } catch (_) {}
      } else if (t === 'message') {
        const m = (msg && msg.payload) || {}
        const item = { agentId: msg.agentId, message: m, receivedAt: Date.now() }
        recentMessages.push(item)
        while (recentMessages.length > MAX_RECEIVED_BUFFER) recentMessages.shift()
        try {
          if (typeof harness.handleEvent === 'function') {
            harness.handleEvent('im.message.received', { agentId: msg.agentId, message: m, eventType: msg.eventType, ts: msg.ts })
          }
        } catch (_) {}
      } else if (t === 'log') {
        // 静默；如需调试可在 settings 里打开 verbose
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
        payload.push({
          agentId: b.agentId,
          appId: c.appId,
          appSecret: c.appSecret,
          domain: (b.tenant === 'lark') ? 'lark' : 'feishu',
        })
      }
      if (payload.length) sendHelperCmd({ cmd: 'broadcastList', payload })
    }

    // ============ 发消息（封装 + token 自动换发）============
    async function ensureFreshToken(c) {
      if (!c) return null
      if (c.accessToken && c.expiresAt && Date.now() < c.expiresAt - 60 * 1000) {
        return c.accessToken
      }
      // 重新拿
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
      if (!token) {
        return { ok: false, error: { kind: 'token_error', message: 'token 获取失败' } }
      }
      // 缓存新 token
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

    // ============ RPC ============
    if (typeof harness.handle === 'function') {
      harness.handle('im.listAgents', async function (args) {
        const bindings = await listBindings()
        return {
          ok: true,
          agents: bindings.map(function (b) { return {
            id: b.agentId,
            agentId: b.agentId,
            name: b.agentId,
            bound: b.status === 'bound',
            platform: b.platform || 'lark',
            appId: b.appId,
            tenant: b.tenant || 'feishu',
            status: b.status,
            operatorOpenId: b.operatorOpenId,
            boundAt: b.boundAt,
          } }),
        }
      })

      harness.handle('im.beginBind', async function (args) {
        try {
          const s = await startBind({ agentId: args && args.agentId })
          return {
            ok: true,
            bindId: s.bindId,
            agentId: s.agentId,
            qrContent: s.verificationUriComplete,
            verificationUriComplete: s.verificationUriComplete,
            expiresAt: s.expiresAt,
            intervalMs: s.interval,
            status: s.status,
          }
        } catch (e) {
          return { ok: false, error: (e && e.kind) ? e : { kind: 'unknown', message: errText(e) } }
        }
      })

      harness.handle('im.pollBind', async function (args) {
        const s = bindSessions.get(args && args.bindId)
        if (!s) return { ok: false, error: { kind: 'not_found', message: 'bindId 失效（已 success/timeout/cancelled）' } }
        return { ok: true, bind: sanitizeSession(s) }
      })

      harness.handle('im.cancelBind', async function (args) {
        return await cancelBind({ bindId: args && args.bindId })
      })

      harness.handle('im.unbind', async function (args) {
        try { return { ok: true, ...(await unbind({ agentId: args && args.agentId })) } }
        catch (e) {
          return { ok: false, error: (e && e.kind) ? e : { kind: 'unknown', message: errText(e) } }
        }
      })

      harness.handle('im.send', async function (args) {
        return await sendIm(args || {})
      })

      harness.handle('im.health', async function () {
        const bindings = await listBindings()
        return {
          ok: true,
          helperReady: helperReady,
          helperPid: helperHandle && helperHandle.pid ? helperHandle.pid : null,
          bindsActive: bindSessions.size,
          recentMessagesCount: recentMessages.length,
          agents: bindings.map(function (b) { return { agentId: b.agentId, status: b.status, appId: b.appId } }),
        }
      })

      harness.handle('im.listHelpers', async function () {
        return {
          ok: true,
          helperReady: helperReady,
          recentMessages: recentMessages.slice(-50),
          bindsActive: bindSessions.size,
        }
      })

      harness.handle('im.recentMessages', async function (args) {
        const agentId = args && args.agentId
        const limit = Math.min(100, Math.max(1, (args && args.limit) || 20))
        const out = agentId
          ? recentMessages.filter(function (m) { return m.agentId === agentId }).slice(-limit)
          : recentMessages.slice(-limit)
        return { ok: true, count: out.length, items: out }
      })
    }

    // ============ Model Tools（harness.registerTool → tools.register）============
    if (toolsSvc && typeof toolsSvc.register === 'function') {
      const defImSend = {
        name: 'im_send',
        description: '用指定 DSH Agent 的飞书 IM 通道向 chatId 发一条消息。',
        parameters: {
          agentId: { type: 'string', required: true, description: '已绑飞书的 DSH Agent ID' },
          chatId: { type: 'string', required: true, description: '飞书 chat_id（群）或 open_id（用户）' },
          msgType: { type: 'string', enum: ['text', 'post', 'interactive', 'image'], required: false },
          content: { type: 'string', required: true, description: 'JSON 字符串；按 msgType 对应格式（text: {"text":"..."}）' },
          receiveIdType: { type: 'string', enum: ['chat_id', 'open_id', 'email'], required: false },
        },
        output: { schema: { type: 'object' }, render: function (_a, v) { return [{ type: 'text', text: JSON.stringify(v) }] } },
        async execute: function (args) {
          let contentParsed
          try { contentParsed = JSON.parse(args.content || '{}') } catch (_) { contentParsed = { text: args.content || '' } }
          return await sendIm({
            agentId: args.agentId,
            chatId: args.chatId,
            msgType: args.msgType || 'text',
            content: contentParsed,
            receiveIdType: args.receiveIdType || 'chat_id',
          })
        },
      }
      toolsSvc.register(defImSend)

      const defImPull = {
        name: 'im_pull',
        description: '读最近收到的飞书 IM 消息（已在 DSH 内缓存，最多 200 条）。',
        parameters: {
          agentId: { type: 'string', required: false, description: '留空 = 全部' },
          limit: { type: 'number', required: false, description: '默认 20，上限 100' },
        },
        output: { schema: { type: 'object' }, render: function (_a, v) { return [{ type: 'text', text: JSON.stringify(v) }] } },
        async execute: function (args) {
          const lim = Math.min(100, Math.max(1, args.limit || 20))
          const items = args.agentId
            ? recentMessages.filter(function (m) { return m.agentId === args.agentId }).slice(-lim)
            : recentMessages.slice(-lim)
          return { ok: true, count: items.length, items: items }
        },
      }
      toolsSvc.register(defImPull)
    }

    // ============ 启动 helper ============
    if (typeof projectRoot !== 'string' || !projectRoot) {
      // 尝试从环境/hook 拿 cwd（DSH 通常注入 process.cwd）
      try { projectRoot = process.cwd() } catch (_) { projectRoot = '' }
    }
    ensureHelperProcess()
  },
}
