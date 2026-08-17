/**
 * dsh-feishu-link · Client 半（npm 安装版 browser bundle）
 *
 * 格式：DSH client-modules 的惰性 CJS bundle —— 经典脚本执行时只注册 factory，
 * 由浏览器内核（vendored Cordis Loader）在挂载该插件条目时物化执行。
 *
 * 与动态版 client.js 差异：
 *   1. React 来自 require('react')（动态版 runner 注入全局）
 *   2. styles.insert（动态版 runner 专属）→ 手动 <style data-plugin> 注入，
 *      并返回清理器卸载（ctx.effect 返回的清理器）
 *   3. host.call('im.xxx', ...)（动态版）→ ctx.connection.rpc.call('/dsfl', endpoint, args)
 *   4. timer 服务不可用兜底（动态版 runner 必注入 timer）
 *
 * 功能同动态版 v0.1.0：5 组件 + 4 slot 注册 + ADRG-RILLING-UX.md 6 条决策实现。
 */
window.__ModuleLoader__.load({
  id: 'dsh-feishu-link',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })

    let React = require('react')

    // ── 样式注入（动态版 styles.insert 的等价物） ──
    var STYLE_TEXT = [
      // 同一套 CSS（与 client.js 内 styles.insert 一致）
      '.dsfl-panel { position:fixed; left:24px; top:80px; width:480px; height:600px; display:flex; flex-direction:column; background:var(--dsw-alias-bg-layer-2,#16181d); border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,.45); z-index:9999; font-family:var(--dsw-font-family, sans-serif); font-size:13px; color:var(--dsw-alias-label-primary,#e6edf3); line-height:1.5; overflow:hidden; }',
      '.dsfl-head { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--dsw-alias-border-l1,#2a2d35); user-select:none; }',
      '.dsfl-head .ttl { font-weight:600; font-size:13px; }',
      '.dsfl-head .counter { font-size:11px; color:var(--dsw-alias-label-caption,#8b8b95); margin-left:auto; }',
      '.dsfl-head button { padding:3px 8px; background:transparent; border:1px solid var(--dsw-alias-border-l1,#2a2d35); color:inherit; border-radius:6px; cursor:pointer; font-size:11px; }',
      '.dsfl-head button:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-body { flex:1; overflow-y:auto; padding:10px 14px; }',
      '.dsfl-actions { padding:8px 14px; border-top:1px solid var(--dsw-alias-border-l1,#2a2d35); display:flex; gap:6px; }',
      '.dsfl-cell { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:8px; margin-bottom:6px; background:var(--dsw-alias-bg-layer-1,#10131a); }',
      '.dsfl-cell:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-cell.dashed { border-style:dashed; opacity:0.95; }',
      '.dsfl-name { font-weight:600; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }',
      '.dsfl-meta { font-size:11px; color:var(--dsw-alias-label-caption,#8b8b95); }',
      '.dsfl-badge { display:inline-flex; align-items:center; gap:3px; padding:2px 9px; border-radius:99px; font-size:11px; line-height:1.7; white-space:nowrap; flex:none; font-variant-numeric:tabular-nums; }',
      '.dsfl-badge.bound { background:rgba(63,185,80,.18); color:#3fb950; }',
      '.dsfl-badge.failed { background:rgba(248,81,73,.18); color:#f85149; }',
      '.dsfl-badge.reconnecting { background:rgba(240,136,62,.18); color:#f0883e; }',
      '.dsfl-badge.scanning { background:rgba(241,196,15,.18); color:#f1c40f; }',
      '.dsfl-badge.unbound { background:rgba(139,139,149,.18); color:#8b8b95; }',
      '.dsfl-btn { padding:4px 12px; border-radius:6px; border:1px solid var(--dsw-alias-border-l1,#2a2d35); background:transparent; color:var(--dsw-alias-label-primary,#e6edf3); font-size:12px; cursor:pointer; flex:none; font-family:inherit; }',
      '.dsfl-btn:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-btn.primary { background:#c084fc; color:#140a1e; border-color:transparent; font-weight:600; }',
      '.dsfl-btn.primary:hover { filter:brightness(1.08); }',
      '.dsfl-btn.danger { color:#f85149; }',
      '.dsfl-btn:disabled { opacity:.5; cursor:not-allowed; }',
      '.dsfl-input { background:transparent; color:inherit; border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:4px; padding:4px 8px; font-size:12px; width:140px; font-family:inherit; }',
      '.dsfl-input:focus { outline:none; border-color:#c084fc; }',
      '.dsfl-modal { position:fixed; inset:0; background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center; z-index:10000; }',
      '.dsfl-modal-box { width:480px; max-width:94vw; background:var(--dsw-alias-bg-layer-2,#16181d); border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; padding:18px 22px; }',
      '.dsfl-modal .ttl { font-size:16px; font-weight:650; margin-bottom:8px; }',
      '.dsfl-modal .actions { margin-top:14px; display:flex; gap:8px; justify-content:flex-end; }',
      '.dsfl-qr { display:block; margin:14px auto; width:240px; height:240px; background:white; padding:10px; border-radius:8px; }',
      '.dsfl-qr-img { width:100%; height:100%; display:block; }',
      '.dsfl-spinner { width:14px; height:14px; border-radius:50%; border:2px solid rgba(255,255,255,.18); border-top-color:#c084fc; animation:dsfl-spin .8s linear infinite; display:inline-block; flex:none; }',
      '@keyframes dsfl-spin { to { transform:rotate(360deg); } }',
      '.dsfl-link { color:#bc8cff; cursor:pointer; text-decoration:underline; word-break:break-all; }',
      '.dsfl-sidebtn { display:flex; align-items:center; gap:8px; padding:6px 10px; cursor:pointer; color:inherit; border-radius:6px; font-size:12.5px; flex:1; }',
      '.dsfl-sidebtn:hover { background:var(--dsw-alias-interactive-bg-hover, rgba(255,255,255,.06)); }',
      '.dsfl-sidebtn .badge { background:#f85149; color:white; font-size:10px; padding:1px 6px; border-radius:99px; font-variant-numeric:tabular-nums; }',
      '.dsfl-hint { display:flex; align-items:center; gap:8px; padding:6px 10px; background:rgba(240,136,62,.12); border:1px solid rgba(240,136,62,.35); color:#fbbf24; border-radius:6px; font-size:12px; margin:4px 0; }',
      '.dsfl-hint a { color:#fbbf24; cursor:pointer; text-decoration:underline; }',
      '.dsfl-hint .dismiss { margin-left:auto; cursor:pointer; padding:0 6px; opacity:0.7; }',
      '.dsfl-hint .dismiss:hover { opacity:1; }',
      '.dsfl-settings { max-width:720px; padding:8px; display:flex; flex-direction:column; gap:16px; }',
      '.dsfl-settings-group { border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; background:var(--dsw-alias-bg-layer-1,#10131a); padding:14px 16px; }',
      '.dsfl-settings-title { font-size:13px; font-weight:650; margin-bottom:8px; }',
      '.dsfl-note { font-size:11.5px; color:var(--dsw-alias-label-caption,#8b8b95); line-height:1.6; }',
      '.dsfl-error { padding:10px 12px; background:rgba(248,81,73,.12); border:1px solid rgba(248,81,73,.4); color:#f87171; border-radius:8px; font-size:12px; margin-bottom:10px; }',
      '.dsfl-divider { height:1px; background:var(--dsw-alias-border-l1,#2a2d35); margin:8px 0; }',
    ].join('\n')

    function injectStyles() {
      if (typeof document === 'undefined') return null
      var el = document.createElement('style')
      el.setAttribute('data-plugin', 'dsh-feishu-link')
      el.textContent = STYLE_TEXT
      document.head.appendChild(el)
      return el
    }
    function removeStyles(el) {
      if (el && el.parentNode) el.parentNode.removeChild(el)
    }

    var h = React.createElement

    // ============ RPC 客户端（npm 安装版用 ctx.connection.rpc.call）============
    function rpcCall(endpoint, payload) {
      if (!ctx || !ctx.connection || !ctx.connection.rpc || typeof ctx.connection.rpc.call !== 'function') {
        return Promise.resolve({ ok: false, error: { kind: 'no_rpc', message: 'npm 安装版 connection 服务不可用' } })
      }
      return ctx.connection.rpc.call('/dsfl', endpoint, payload || {})
    }
    function listAgentsRpc() { return rpcCall('listAgents').then(function (r) { return (r && r.ok) ? r : { ok: false, agents: [] } }) }
    function beginBind(agentId) { return rpcCall('beginBind', { agentId: agentId }) }
    function pollBind(bindId) { return rpcCall('pollBind', { bindId: bindId }) }
    function cancelBind(bindId) { return rpcCall('cancelBind', { bindId: bindId }) }
    function unbindRpc(agentId) { return rpcCall('unbind', { agentId: agentId }) }
    function getHealth() { return rpcCall('health') }
    function getRecent(agentId) { return rpcCall('recentMessages', { agentId: agentId, limit: 20 }) }

    function openIMCenter() {
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('dsfl:open'))
      }
    }

    // ============ 组件 1: SidebarButton ============
    function SidebarButton(props) {
      var _s = React.useState(0), tick = _s[0], setTick = _s[1]
      React.useEffect(function () {
        var alive = true
        function refresh() {
          listAgentsRpc().then(function (r) {
            if (!alive) return
            if (r && r.ok) {
              var list = r.agents || []
              var unbound = 0
              for (var i = 0; i < list.length; i++) if (!list[i].bound) unbound++
              setTick(unbound)  // 直接用 unbound
            }
          })
        }
        refresh()
        var t = setInterval(refresh, 60_000)
        return function () { alive = false; clearInterval(t) }
      }, [])
      return h('div', { className: 'dsfl-sidebtn', onClick: openIMCenter, title: '打开 dsh-feishu-link IM 中心' }, [
        h('span', null, '⛓'),
        h('span', null, '飞书 IM'),
        tick > 0 ? h('span', { className: 'badge' }, tick > 9 ? '9+' : String(tick)) : null,
      ])
    }

    // ============ 组件 2: IMStationOverlay ============
    function IMStationOverlay(props) {
      var _open = React.useState(false), open = _open[0], setOpen = _open[1]
      var _agents = React.useState([]), agents = _agents[0], setAgents = _agents[1]
      var _busy = React.useState(false), busy = _busy[0], setBusy = _busy[1]
      var _error = React.useState(''), error = _error[0], setError = _error[1]
      var _wizard = React.useState(null), wizard = _wizard[0], setWizard = _wizard[1]
      var _confirmUnbind = React.useState(null), confirmUnbind = _confirmUnbind[0], setConfirmUnbind = _confirmUnbind[1]

      function refresh() {
        setBusy(true); setError('')
        listAgentsRpc().then(function (r) {
          if (r && r.ok) setAgents(r.agents || [])
          else setError((r && r.error && r.error.message) || 'listAgents 失败')
          setBusy(false)
        })
      }
      React.useEffect(function () {
        var h1 = function () { setOpen(true) }
        if (typeof window !== 'undefined') window.addEventListener('dsfl:open', h1)
        return function () { if (typeof window !== 'undefined') window.removeEventListener('dsfl:open', h1) }
      }, [])
      React.useEffect(function () {
        if (!open) return
        refresh()
        var t = setInterval(refresh, 30_000)
        return function () { clearInterval(t) }
      }, [open])

      function startBind(agentId) {
        if (!agentId) return
        setError('')
        beginBind(agentId).then(function (r) {
          if (!r || !r.ok) { setError((r && r.error && r.error.message) || 'beginBind 失败'); return }
          setWizard({
            agentId: agentId, bindId: r.bindId, qrContent: r.qrContent,
            expiresAt: r.expiresAt, status: 'scan', startedAt: Date.now(),
          })
        })
      }
      function onWizardRetry() {
        if (!wizard) return
        var aid = wizard.agentId
        setWizard(null)
        startBind(aid)
      }

      React.useEffect(function () {
        if (!wizard || !wizard.bindId) return
        function poll() {
          pollBind(wizard.bindId).then(function (r) {
            if (!r || !r.ok) return
            var s = r.bind
            if (!s) return
            if (s.status === 'success') {
              setWizard(Object.assign({}, wizard, { status: 'success', appId: s.appId }))
              setTimeout(function () { setWizard(null); refresh() }, 1500)
              return
            }
            if (s.status === 'failed' || s.status === 'timeout' || s.status === 'cancelled') {
              setWizard(Object.assign({}, wizard, { status: s.status, lastError: s.lastError }))
            }
          })
        }
        var t = setInterval(poll, 4000)
        return function () { clearInterval(t) }
      }, [wizard && wizard.bindId])

      if (!open) return null
      return h('div', { className: 'dsfl-panel' }, [
        h('div', { className: 'dsfl-head' }, [
          h('span', { className: 'ttl' }, '⛓ dsh-feishu-link'),
          h('span', { className: 'counter' }, busy ? '加载中…' : (agents.length + ' 个 Agent')),
          h('button', { onClick: refresh, title: '刷新' }, '↻'),
          h('button', { onClick: function () { setOpen(false) }, title: '关闭' }, '×'),
        ]),
        h('div', { className: 'dsfl-body' }, [
          error ? h('div', { className: 'dsfl-error' }, error) : null,
          agents.length === 0 ? h('div', { className: 'dsfl-note' }, '尚未绑定任何 Agent。') : null,
          agents.map(function (b) {
            return h('div', { key: b.agentId, className: 'dsfl-cell' }, [
              h('span', { className: 'dsfl-name' }, b.agentId),
              h('span', { className: 'dsfl-meta' }, b.appId ? 'app=' + b.appId.slice(0, 14) : ''),
              h('span', { className: 'dsfl-badge ' + (b.status === 'bound' ? 'bound' : 'unbound') }, b.status === 'bound' ? '● 已绑' : '○ 未绑'),
              b.status === 'bound'
                ? h('button', { className: 'dsfl-btn', onClick: function () { setConfirmUnbind({ agentId: b.agentId, name: b.agentId }) } }, '解绑')
                : h('button', { className: 'dsfl-btn primary', onClick: function () { startBind(b.agentId) } }, '扫码绑定'),
            ])
          }),
          h(ManualBindRow, { onSubmit: function (id) { startBind(id) } }),
          h('div', { className: 'dsfl-divider' }),
          h('div', { className: 'dsfl-note' }, 'P0 = 飞书扫码绑 + 双向消息'),
        ]),
        h('div', { className: 'dsfl-actions' }, [
          h('button', { className: 'dsfl-btn', onClick: refresh }, '刷新'),
          h('button', { className: 'dsfl-btn primary', onClick: function () { startBind('') } }, '+ 新绑定'),
        ]),
        wizard ? h(BindWizardModal, { wizard: wizard, onCancel: function () { cancelBind(wizard.bindId).then(function () { setWizard(null); refresh() }) }, onClose: function () { setWizard(null); refresh() }, onRetry: onWizardRetry }) : null,
        confirmUnbind ? h(ConfirmUnbindModal, { data: confirmUnbind, onCancel: function () { setConfirmUnbind(null) }, onConfirm: function () { unbindRpc(confirmUnbind.agentId).then(function () { setConfirmUnbind(null); refresh() }) } }) : null,
      ])
    }

    function ManualBindRow(props) {
      var _v = React.useState(''), val = _v[0], setVal = _v[1]
      function submit() {
        var id = (val || '').trim()
        if (!id) return
        props.onSubmit(id)
        setVal('')
      }
      return h('div', { className: 'dsfl-cell dashed' }, [
        h('span', { className: 'dsfl-name' }, '+ 手动输入 Agent ID'),
        h('input', { className: 'dsfl-input', value: val, onChange: function (e) { setVal(e.target.value) }, onKeyDown: function (e) { if (e.key === 'Enter') submit() }, placeholder: 'agent-id', spellCheck: false }),
        h('button', { className: 'dsfl-btn primary', disabled: !val.trim(), onClick: submit }, '绑定'),
      ])
    }

    function BindWizardModal(props) {
      var w = props.wizard
      if (!w) return null
      var remaining = Math.max(0, Math.floor((w.expiresAt - Date.now()) / 1000))
      var mm = Math.floor(remaining / 60), ss = String(remaining % 60).padStart(2, '0')
      function renderBody() {
        if (w.status === 'scan' || w.status === 'waiting') {
          return h(React.Fragment, null, [
            h('div', { className: 'dsfl-note', style: { marginBottom: 8 } }, '请用飞书 App 扫描以下二维码，或用浏览器打开下方链接：'),
            h('div', { className: 'dsfl-qr' }, h('img', { className: 'dsfl-qr-img', src: 'https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=' + encodeURIComponent(w.qrContent || ''), alt: 'QR' })),
            h('div', { className: 'dsfl-note', style: { textAlign: 'center', fontVariantNumeric: 'tabular-nums' } }, '有效期 ' + mm + ':' + ss),
            h('div', { className: 'dsfl-note', style: { textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis' } }, [h('a', { className: 'dsfl-link', href: w.qrContent, target: '_blank', rel: 'noreferrer' }, w.qrContent)]),
            h('div', { className: 'dsfl-note', style: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 } }, [h('span', { className: 'dsfl-spinner' }), h('span', null, '轮询飞书侧状态…')]),
          ])
        }
        if (w.status === 'success') {
          return h('div', { className: 'dsfl-badge bound', style: { display: 'inline-flex', margin: '12px 0' } }, '✓ 绑定成功！App ID: ' + (w.appId || ''))
        }
        if (w.status === 'failed') return h('div', { className: 'dsfl-error' }, '绑定失败：' + (w.lastError || '未知错误'))
        if (w.status === 'timeout') return h('div', { className: 'dsfl-error', style: { background: 'rgba(240,136,62,.12)', borderColor: 'rgba(240,136,62,.4)', color: '#fbbf24' } }, '二维码已过期')
        if (w.status === 'cancelled') return h('div', { className: 'dsfl-note' }, '已取消')
        return h('div', { className: 'dsfl-note' }, '状态: ' + w.status)
      }
      return h('div', { className: 'dsfl-modal' }, h('div', { className: 'dsfl-modal-box' }, [
        h('div', { className: 'ttl' }, '绑定飞书机器人'),
        h('div', { className: 'dsfl-note' }, 'Agent: ' + (w.agentId || '?')),
        renderBody(),
        h('div', { className: 'actions' }, [
          (w.status === 'failed' || w.status === 'timeout' || w.status === 'cancelled') ? h('button', { className: 'dsfl-btn primary', onClick: props.onRetry }, '重试') : null,
          (w.status === 'scan' || w.status === 'waiting') ? h('button', { className: 'dsfl-btn', onClick: props.onCancel }, '取消') : null,
          h('button', { className: 'dsfl-btn', onClick: props.onClose }, '关闭'),
        ]),
      ]))
    }

    function ConfirmUnbindModal(props) {
      return h('div', { className: 'dsfl-modal' }, h('div', { className: 'dsfl-modal-box' }, [
        h('div', { className: 'ttl' }, '解绑飞书机器人？'),
        h('div', { className: 'dsfl-note' }, 'Agent: ' + (props.data && props.data.name)),
        h('div', { className: 'dsfl-note' }, '解绑后该 Agent 的飞书消息将不再自动转入 DSH 会话。需要重新扫码绑定才能继续接收飞书消息。'),
        h('div', { className: 'actions' }, [
          h('button', { className: 'dsfl-btn', onClick: props.onCancel }, '取消'),
          h('button', { className: 'dsfl-btn danger', onClick: props.onConfirm }, '解绑'),
        ]),
      ]))
    }

    function SettingsPage(props) {
      var _a = React.useState([]), agents = _a[0], setAgents = _a[1]
      var _h = React.useState(null), health = _h[0], setHealth = _h[1]
      function refresh() {
        listAgentsRpc().then(function (r) { if (r && r.ok) setAgents(r.agents || []) })
        getHealth().then(function (r) { if (r && r.ok) setHealth(r) })
      }
      React.useEffect(function () {
        refresh()
        var t = setInterval(refresh, 30_000)
        return function () { clearInterval(t) }
      }, [])
      return h('div', { className: 'dsfl-settings' }, [
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, '⛓ dsh-feishu-link'),
          h('div', { className: 'dsfl-note' }, '飞书扫码绑 + Agent 中继。已绑 ' + agents.length + ' 个 Agent。'),
          h('button', { className: 'dsfl-btn primary', onClick: openIMCenter, style: { marginTop: 10 } }, '打开 IM 中心'),
        ]),
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, 'WSS 长连接'),
          h('div', { className: 'dsfl-note' }, 'helper 状态：' + (health && health.helperReady ? '✓ 已就绪（pid ' + (health.helperPid || '?') + '）' : '✗ 未就绪（30s 后自动重启）')),
          h('div', { className: 'dsfl-note' }, '未绑会话：' + (health ? health.bindsActive : '?') + ' · 最近消息缓存：' + (health ? health.recentMessagesCount : '?')),
          h('button', { className: 'dsfl-btn', onClick: refresh, style: { marginTop: 8 } }, '手动刷新'),
        ]),
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, '已绑 Agent'),
          agents.length === 0
            ? h('div', { className: 'dsfl-note' }, '尚未绑定任何 Agent。')
            : h('div', null, agents.map(function (b) {
                return h('div', { key: b.agentId, className: 'dsfl-cell' }, [
                  h('span', { className: 'dsfl-name' }, b.agentId),
                  h('span', { className: 'dsfl-meta' }, b.appId ? 'app=' + b.appId.slice(0, 14) : ''),
                  h('span', { className: 'dsfl-badge bound' }, '● 已绑'),
                ])
              })),
        ]),
      ])
    }

    function BindHint(props) {
      var _a = React.useState([]), agents = _a[0], setAgents = _a[1]
      var _s = React.useState(false), showHint = _s[0], setShowHint = _s[1]
      React.useEffect(function () {
        listAgentsRpc().then(function (r) { if (r && r.ok) setAgents(r.agents || []) })
        if (typeof localStorage !== 'undefined') if (!localStorage.getItem('dsfl-hint-dismissed')) setShowHint(true)
      }, [])
      if (agents.length > 0) return null
      function dismiss() {
        if (typeof localStorage !== 'undefined') localStorage.setItem('dsfl-hint-dismissed', '1')
        setShowHint(false)
      }
      return h('div', { className: 'dsfl-hint' }, [
        h('span', null, '尚未绑定任何飞书 IM。'),
        h('a', { onClick: openIMCenter }, '打开 IM 中心 · 绑一个'),
        showHint ? h('a', { className: 'dismiss', onClick: dismiss, title: '不再提醒' }, '×') : null,
      ])
    }

    // ============ Slot 注册 ============
    var slots = ctx && ctx.get ? ctx.get('slots') : undefined
    var disposers = []
    if (slots && typeof slots.inject === 'function') {
      try {
        disposers.push(slots.inject('sidebar.footer.action', function () {
          return slots.register({ name: 'sidebar.footer.action', id: 'dsh-feishu-link', label: function () { return '飞书 IM' }, order: 6 }, SidebarButton)
        }))
        disposers.push(slots.inject('shell.overlay', function () {
          return slots.register({ name: 'shell.overlay', id: 'dsfl-overlay', order: 12 }, IMStationOverlay)
        }))
        disposers.push(slots.inject('settings.plugins.tab', function () {
          return slots.register({ name: 'settings.plugins.tab', id: 'dsfl-settings', order: 50, label: function () { return '飞书 IM' } }, SettingsPage)
        }))
        disposers.push(slots.inject('conversation.input.dock', function () {
          return slots.register({ name: 'conversation.input.dock', id: 'dsfl-dock', order: 41 }, BindHint)
        }))
      } catch (e) {
        // swallow
      }
    }

    // 样式注入（用 ctx.effect 卸载）
    var styleEl = injectStyles()
    if (styleEl && ctx && typeof ctx.effect === 'function') {
      ctx.effect(function () {
        return function () { removeStyles(styleEl) }
      }, 'dsh-feishu-link: styles')
    }

    if (ctx && typeof ctx.effect === 'function') {
      ctx.effect(function () {
        return function () {
          for (var i = 0; i < disposers.length; i++) {
            try { if (disposers[i]) disposers[i]() } catch (_) {}
          }
        }
      }, 'dsh-feishu-link: slots')
    }

    return module.exports
  },
})
