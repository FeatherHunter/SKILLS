/**
 * dsh-feishu-link · Client 半（cordis_define code.client 函数体）
 *
 * 5 组件：
 *   1. SidebarButton      —— sidebar.footer.action 入口
 *   2. IMStationOverlay  —— shell.overlay IM 中心主面板（图 1/3/4 + 状态徽标）
 *   3. BindWizardModal    —— 图 4 扫码向导（QR + 状态机）
 *   4. ConfirmUnbindModal —— 解绑确认弹窗（ADR 决策 5）
 *   5. SettingsPage       —— settings.plugins.tab 配置页
 *   6. BindHint           —— conversation.input.dock 提示条（ADR 决策 1）
 *
 * 数据流：
 *   → 调用 host.call('im.xxx', args) 7 RPC（host 已实现）
 *   → 子面板用 polling（30s）刷新 agent 列表 + 健康
 *   → BindWizard 用 4s interval 轮询 bind 状态
 *
 * 主题安全：颜色 hardcoded（YIQ 自适应 fallback），不依赖 alias 变量（waystation v14-5 教训）
 */

return {
  apply(ctx) {
    const slots = ctx.get('slots')
    if (slots === undefined) return
    const timer = ctx.get('timer')
    const h = React.createElement

    // ============ 主题色（YIQ 感知亮度，主题安全）============
    const COLOR_BOUND = '#3fb950'
    const COLOR_RECONNECTING = '#f0883e'
    const COLOR_FAILED = '#f85149'
    const COLOR_SCANNING = '#f1c40f'
    const COLOR_UNBOUND = '#8b8b95'
    const ICON_LINK = '⛓'
    const DEFAULT_AGENT_ID = ''  // 留空让用户输入

    // ============ CSS ============
    styles.insert([
      // 主面板
      '.dsfl-panel { position:fixed; left:24px; top:80px; width:480px; height:600px; display:flex; flex-direction:column; background:var(--dsw-alias-bg-layer-2,#16181d); border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,.45); z-index:9999; font-family:var(--dsw-font-family, sans-serif); font-size:13px; color:var(--dsw-alias-label-primary,#e6edf3); line-height:1.5; overflow:hidden; }',
      '.dsfl-head { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--dsw-alias-border-l1,#2a2d35); user-select:none; }',
      '.dsfl-head .ttl { font-weight:600; font-size:13px; }',
      '.dsfl-head .counter { font-size:11px; color:var(--dsw-alias-label-caption,#8b8b95); margin-left:auto; }',
      '.dsfl-head button { padding:3px 8px; background:transparent; border:1px solid var(--dsw-alias-border-l1,#2a2d35); color:inherit; border-radius:6px; cursor:pointer; font-size:11px; }',
      '.dsfl-head button:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-body { flex:1; overflow-y:auto; padding:10px 14px; }',
      '.dsfl-actions { padding:8px 14px; border-top:1px solid var(--dsw-alias-border-l1,#2a2d35); display:flex; gap:6px; }',
      // agent 列表项
      '.dsfl-cell { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:8px; margin-bottom:6px; background:var(--dsw-alias-bg-layer-1,#10131a); }',
      '.dsfl-cell:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-cell.dashed { border-style:dashed; opacity:0.95; }',
      '.dsfl-name { font-weight:600; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }',
      '.dsfl-meta { font-size:11px; color:var(--dsw-alias-label-caption,#8b8b95); }',
      // 5 状态徽章（YIQ 主题安全）
      '.dsfl-badge { display:inline-flex; align-items:center; gap:3px; padding:2px 9px; border-radius:99px; font-size:11px; line-height:1.7; white-space:nowrap; flex:none; font-variant-numeric:tabular-nums; }',
      '.dsfl-badge.bound { background:rgba(63,185,80,.18); color:' + COLOR_BOUND + '; }',
      '.dsfl-badge.failed { background:rgba(248,81,73,.18); color:' + COLOR_FAILED + '; }',
      '.dsfl-badge.reconnecting { background:rgba(240,136,62,.18); color:' + COLOR_RECONNECTING + '; }',
      '.dsfl-badge.scanning { background:rgba(241,196,15,.18); color:' + COLOR_SCANNING + '; }',
      '.dsfl-badge.unbound { background:rgba(139,139,149,.18); color:' + COLOR_UNBOUND + '; }',
      // 按钮
      '.dsfl-btn { padding:4px 12px; border-radius:6px; border:1px solid var(--dsw-alias-border-l1,#2a2d35); background:transparent; color:var(--dsw-alias-label-primary,#e6edf3); font-size:12px; cursor:pointer; flex:none; font-family:inherit; }',
      '.dsfl-btn:hover { border-color:var(--dsw-alias-border-l2,#3a3f4a); }',
      '.dsfl-btn.primary { background:#c084fc; color:#140a1e; border-color:transparent; font-weight:600; }',
      '.dsfl-btn.primary:hover { filter:brightness(1.08); }',
      '.dsfl-btn.danger { color:' + COLOR_FAILED + '; }',
      '.dsfl-btn:disabled { opacity:.5; cursor:not-allowed; }',
      '.dsfl-input { background:transparent; color:inherit; border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:4px; padding:4px 8px; font-size:12px; width:140px; font-family:inherit; }',
      '.dsfl-input:focus { outline:none; border-color:#c084fc; }',
      // modal
      '.dsfl-modal { position:fixed; inset:0; background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center; z-index:10000; }',
      '.dsfl-modal-box { width:480px; max-width:94vw; background:var(--dsw-alias-bg-layer-2,#16181d); border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; padding:18px 22px; }',
      '.dsfl-modal h3 { margin:0 0 8px; font-size:15px; font-weight:650; }',
      '.dsfl-modal .ttl { font-size:16px; font-weight:650; margin-bottom:8px; }',
      '.dsfl-modal .actions { margin-top:14px; display:flex; gap:8px; justify-content:flex-end; }',
      // QR
      '.dsfl-qr { display:block; margin:14px auto; width:240px; height:240px; background:white; padding:10px; border-radius:8px; }',
      '.dsfl-qr-img { width:100%; height:100%; display:block; }',
      '.dsfl-spinner { width:14px; height:14px; border-radius:50%; border:2px solid rgba(255,255,255,.18); border-top-color:#c084fc; animation:dsfl-spin .8s linear infinite; display:inline-block; flex:none; }',
      '@keyframes dsfl-spin { to { transform:rotate(360deg); } }',
      '.dsfl-link { color:#bc8cff; cursor:pointer; text-decoration:underline; word-break:break-all; }',
      // sidebar 入口
      '.dsfl-sidebtn { display:flex; align-items:center; gap:8px; padding:6px 10px; cursor:pointer; color:inherit; border-radius:6px; font-size:12.5px; flex:1; }',
      '.dsfl-sidebtn:hover { background:var(--dsw-alias-interactive-bg-hover, rgba(255,255,255,.06)); }',
      '.dsfl-sidebtn .badge { background:' + COLOR_FAILED + '; color:white; font-size:10px; padding:1px 6px; border-radius:99px; font-variant-numeric:tabular-nums; }',
      // dock 提示条
      '.dsfl-hint { display:flex; align-items:center; gap:8px; padding:6px 10px; background:rgba(240,136,62,.12); border:1px solid rgba(240,136,62,.35); color:#fbbf24; border-radius:6px; font-size:12px; margin:4px 0; }',
      '.dsfl-hint a { color:#fbbf24; cursor:pointer; text-decoration:underline; }',
      '.dsfl-hint .dismiss { margin-left:auto; cursor:pointer; padding:0 6px; opacity:0.7; }',
      '.dsfl-hint .dismiss:hover { opacity:1; }',
      // settings page
      '.dsfl-settings { max-width:720px; padding:8px; display:flex; flex-direction:column; gap:16px; }',
      '.dsfl-settings-group { border:1px solid var(--dsw-alias-border-l1,#2a2d35); border-radius:12px; background:var(--dsw-alias-bg-layer-1,#10131a); padding:14px 16px; }',
      '.dsfl-settings-title { font-size:13px; font-weight:650; margin-bottom:8px; }',
      '.dsfl-note { font-size:11.5px; color:var(--dsw-alias-label-caption,#8b8b95); line-height:1.6; }',
      '.dsfl-error { padding:10px 12px; background:rgba(248,81,73,.12); border:1px solid rgba(248,81,73,.4); color:#f87171; border-radius:8px; font-size:12px; margin-bottom:10px; }',
      // divider
      '.dsfl-divider { height:1px; background:var(--dsw-alias-border-l1,#2a2d35); margin:8px 0; }',
    ].join('\n'))

    // ============ RPC 客户端 (host.call 包装) ============
    async function rpc(method, args) {
      try {
        const r = await host.call(method, args || {})
        return r || { ok: false, error: { kind: 'no_response', message: 'no response' } }
      } catch (e) {
        return { ok: false, error: { kind: 'rpc_failed', message: String((e && e.message) || e) } }
      }
    }
    const listAgentsRpc = () => rpc('im.listAgents')
    const beginBind = (agentId) => rpc('im.beginBind', { agentId })
    const pollBind = (bindId) => rpc('im.pollBind', { bindId })
    const cancelBind = (bindId) => rpc('im.cancelBind', { bindId })
    const unbindRpc = (agentId) => rpc('im.unbind', { agentId })
    const getHealth = () => rpc('im.health')
    const getRecent = (agentId) => rpc('im.recentMessages', { agentId, limit: 20 })

    // ============ utility: open IM 中心（用 window event 跨组件）============
    function openIMCenter() {
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('dsfl:open'))
      }
    }
    if (typeof window !== 'undefined') {
      // 暴露给 settings 页面直接调
      window.__dsfl_openIMCenter = openIMCenter
    }

    // ============ 组件 1: SidebarButton (侧栏入口) ============
    function SidebarButton(props) {
      const [count, setCount] = React.useState(0)
      React.useEffect(() => {
        let alive = true
        const refresh = async () => {
          const r = await listAgentsRpc()
          if (!alive) return
          if (r && r.ok) {
            const list = r.agents || []
            const unbound = list.filter(a => !a.bound).length
            setCount(unbound)
          }
        }
        refresh()
        const t = setInterval(refresh, 60_000)
        return () => { alive = false; clearInterval(t) }
      }, [])
      return h('div', { className: 'dsfl-sidebtn', onClick: openIMCenter, title: '打开 dsh-feishu-link IM 中心' }, [
        h('span', null, '⛓'),
        h('span', null, '飞书 IM'),
        count > 0 ? h('span', { className: 'badge' }, count > 9 ? '9+' : String(count)) : null,
      ])
    }

    // ============ 组件 2: IMStationOverlay (主面板) ============
    function IMStationOverlay(props) {
      const [open, setOpen] = React.useState(false)
      const [agents, setAgents] = React.useState([])
      const [busy, setBusy] = React.useState(false)
      const [error, setError] = React.useState('')
      const [wizard, setWizard] = React.useState(null)      // {agentId, bindId, qrContent, expiresAt, status, appId, lastError}
      const [confirmUnbind, setConfirmUnbind] = React.useState(null) // {agentId, name}

      const refresh = React.useCallback(async () => {
        setBusy(true); setError('')
        try {
          const r = await listAgentsRpc()
          if (r && r.ok) setAgents(r.agents || [])
          else setError((r && r.error && r.error.message) || 'listAgents 失败')
        } finally { setBusy(false) }
      }, [])

      // 监听全局「打开 IM 中心」事件
      React.useEffect(() => {
        const handler = () => setOpen(true)
        if (typeof window !== 'undefined') window.addEventListener('dsfl:open', handler)
        return () => { if (typeof window !== 'undefined') window.removeEventListener('dsfl:open', handler) }
      }, [])

      // 打开面板时刷新
      React.useEffect(() => {
        if (!open) return
        refresh()
        const t = setInterval(refresh, 30_000)
        return () => clearInterval(t)
      }, [open, refresh])

      const startBind = async (agentId) => {
        if (!agentId) return
        setError('')
        const r = await beginBind(agentId)
        if (!r || !r.ok) { setError((r && r.error && r.error.message) || 'beginBind 失败'); return }
        setWizard({
          agentId: agentId,
          bindId: r.bindId,
          qrContent: r.qrContent,
          expiresAt: r.expiresAt,
          status: 'scan',
          startedAt: Date.now(),
        })
      }
      const onWizardRetry = async () => {
        if (!wizard) return
        const aid = wizard.agentId
        setWizard(null)
        await startBind(aid)
      }

      // 绑定流程：4s 轮询
      React.useEffect(() => {
        if (!wizard || !wizard.bindId) return
        const poll = async () => {
          const r = await pollBind(wizard.bindId)
          if (!r || !r.ok) return
          const s = r.bind
          if (s.status === 'success') {
            setWizard(Object.assign({}, wizard, { status: 'success', appId: s.appId }))
            setTimeout(() => { setWizard(null); refresh() }, 1500)
            return
          }
          if (s.status === 'failed' || s.status === 'timeout' || s.status === 'cancelled') {
            setWizard(Object.assign({}, wizard, { status: s.status, lastError: s.lastError }))
            return
          }
        }
        const t = setInterval(poll, 4000)
        return () => clearInterval(t)
      }, [wizard && wizard.bindId])

      if (!open) return null

      return h('div', { className: 'dsfl-panel' }, [
        // 头部
        h('div', { className: 'dsfl-head' }, [
          h('span', { className: 'ttl' }, '⛓ dsh-feishu-link'),
          h('span', { className: 'counter' }, busy ? '加载中…' : (agents.length + ' 个 Agent')),
          h('button', { onClick: refresh, title: '刷新' }, '↻'),
          h('button', { onClick: () => setOpen(false), title: '关闭' }, '×'),
        ]),
        // 主体
        h('div', { className: 'dsfl-body' }, [
          error ? h('div', { className: 'dsfl-error' }, error) : null,

          agents.length === 0 ? h('div', { className: 'dsfl-note' }, '尚未绑定任何 Agent。下一步：① 创建一个 DSH Agent；② 输入 Agent ID，点「扫码绑定」。') : null,

          // agent 列表
          ...agents.map(function (b) {
            return h('div', { key: b.agentId, className: 'dsfl-cell' }, [
              h('span', { className: 'dsfl-name' }, b.agentId || b.name),
              h('span', { className: 'dsfl-meta' }, b.appId ? 'app=' + b.appId.slice(0, 14) : ''),
              h('span', { className: 'dsfl-badge ' + (b.status === 'bound' ? 'bound' : 'unbound') }, b.status === 'bound' ? '● 已绑' : '○ 未绑'),
              b.status === 'bound'
                ? h('button', { className: 'dsfl-btn', onClick: function () { setConfirmUnbind({ agentId: b.agentId, name: b.agentId }) } }, '解绑')
                : h('button', { className: 'dsfl-btn primary', onClick: function () { startBind(b.agentId) } }, '扫码绑定'),
            ])
          }),

          // 手动输入 Agent ID 绑定
          h(ManualBindRow, { onSubmit: function (id) { startBind(id) } }),

          h('div', { className: 'dsfl-divider' }),
          h('div', { className: 'dsfl-note' }, 'P0 = 飞书扫码绑 + 双向消息；P1+ = 多 Agent / 多平台 / 富文本 / 群聊路由（待 P0 验收后）'),
        ]),
        // footer actions
        h('div', { className: 'dsfl-actions' }, [
          h('button', { className: 'dsfl-btn', onClick: refresh }, '刷新'),
          h('button', { className: 'dsfl-btn primary', onClick: function () { startBind('') } }, '+ 新绑定'),
        ]),
        // modals
        wizard ? h(BindWizardModal, { wizard, onCancel: async function () { await cancelBind(wizard.bindId); setWizard(null); refresh() }, onClose: function () { setWizard(null); refresh() }, onRetry: onWizardRetry }) : null,
        confirmUnbind ? h(ConfirmUnbindModal, { data: confirmUnbind, onCancel: function () { setConfirmUnbind(null) }, onConfirm: async function () { await unbindRpc(confirmUnbind.agentId); setConfirmUnbind(null); refresh() } }) : null,
      ])
    }

    // ============ 组件 2.1: ManualBindRow (输入 Agent ID 绑定) ============
    function ManualBindRow(props) {
      const [val, setVal] = React.useState('')
      const submit = function () {
        const id = (val || '').trim()
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

    // ============ 组件 3: BindWizardModal (扫码向导) ============
    function BindWizardModal(props) {
      const w = props.wizard
      if (!w) return null
      const remaining = Math.max(0, Math.floor((w.expiresAt - Date.now()) / 1000))
      const mm = Math.floor(remaining / 60), ss = String(remaining % 60).padStart(2, '0')

      const renderBody = function () {
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
        if (w.status === 'failed') {
          return h('div', { className: 'dsfl-error' }, '绑定失败：' + (w.lastError || '未知错误'))
        }
        if (w.status === 'timeout') {
          return h('div', { className: 'dsfl-error', style: { background: 'rgba(240,136,62,.12)', borderColor: 'rgba(240,136,62,.4)', color: '#fbbf24' } }, '二维码已过期')
        }
        if (w.status === 'cancelled') {
          return h('div', { className: 'dsfl-note' }, '已取消')
        }
        return h('div', { className: 'dsfl-note' }, '状态: ' + w.status)
      }

      return h('div', { className: 'dsfl-modal' }, h('div', { className: 'dsfl-modal-box' }, [
        h('div', { className: 'ttl' }, '绑定飞书机器人'),
        h('div', { className: 'dsfl-note' }, 'Agent: ' + (w.agentId || '?')),
        renderBody(),
        h('div', { className: 'actions' }, [
          (w.status === 'failed' || w.status === 'timeout' || w.status === 'cancelled')
            ? h('button', { className: 'dsfl-btn primary', onClick: props.onRetry }, '重试')
            : null,
          (w.status === 'scan' || w.status === 'waiting')
            ? h('button', { className: 'dsfl-btn', onClick: props.onCancel }, '取消')
            : null,
          h('button', { className: 'dsfl-btn', onClick: props.onClose }, '关闭'),
        ]),
      ]))
    }

    // ============ 组件 4: ConfirmUnbindModal (解绑确认) ============
    function ConfirmUnbindModal(props) {
      return h('div', { className: 'dsfl-modal' }, h('div', { className: 'dsfl-modal-box' }, [
        h('div', { className: 'ttl' }, '解绑飞书机器人？'),
        h('div', { className: 'dsfl-note' }, 'Agent: ' + (props.data && props.data.name)),
        h('div', { className: 'dsfl-note' }, '解绑后该 Agent 的飞书消息将不再自动转入 DSH 会话。需要重新扫码绑定才能继续接收飞书消息。'),
        h('div', { className: 'dsfl-actions' }, [
          h('button', { className: 'dsfl-btn', onClick: props.onCancel }, '取消'),
          h('button', { className: 'dsfl-btn danger', onClick: props.onConfirm }, '解绑'),
        ]),
      ]))
    }

    // ============ 组件 5: SettingsPage (配置页) ============
    function SettingsPage(props) {
      const [agents, setAgents] = React.useState([])
      const [health, setHealth] = React.useState(null)

      const refresh = React.useCallback(async () => {
        const a = await listAgentsRpc()
        if (a && a.ok) setAgents(a.agents || [])
        const h2 = await getHealth()
        if (h2 && h2.ok) setHealth(h2)
      }, [])
      React.useEffect(() => {
        refresh()
        const t = setInterval(refresh, 30_000)
        return () => clearInterval(t)
      }, [refresh])

      return h('div', { className: 'dsfl-settings' }, [
        // 1. 总览
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, '⛓ dsh-feishu-link'),
          h('div', { className: 'dsfl-note' }, '飞书扫码绑 + Agent 中继（仿 MCODE IM 中心）。已绑 ' + agents.length + ' 个 Agent。'),
          h('button', { className: 'dsfl-btn primary', onClick: openIMCenter, style: { marginTop: 10 } }, '打开 IM 中心'),
        ]),
        // 2. WSS 健康
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, 'WSS 长连接'),
          h('div', { className: 'dsfl-note' }, 'helper 状态：' + (health && health.helperReady ? '✓ 已就绪（pid ' + (health.helperPid || '?') + '）' : '✗ 未就绪（30s 后自动重启）')),
          h('div', { className: 'dsfl-note' }, '未绑会话：' + (health ? health.bindsActive : '?') + ' · 最近消息缓存：' + (health ? health.recentMessagesCount : '?')),
          h('button', { className: 'dsfl-btn', onClick: refresh, style: { marginTop: 8 } }, '手动刷新'),
        ]),
        // 3. 已绑 Agent
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
        // 4. 说明
        h('div', { className: 'dsfl-settings-group' }, [
          h('div', { className: 'dsfl-settings-title' }, '路线 A'),
          h('div', { className: 'dsfl-note' }, 'P0：飞书扫码绑 + WSS 长连接 + 双向消息（手机↔DSH Agent）+ IM 中心（路线 A overlay）。待 DSH 端开口后内嵌 sidebar 行级图标（路线 B）。'),
          h('div', { className: 'dsfl-note', style: { marginTop: 6 } }, '参考：'),
          h('div', { className: 'dsfl-note' }, '· 调研档案：dsh-plugin/RESEARCH-im-binding.md（v3）'),
          h('div', { className: 'dsfl-note' }, '· 设计文档：dsh-plugin/dsh-feishu-link/docs/ADR-GRILLING-UX.md'),
        ]),
      ])
    }

    // ============ 组件 6: BindHint (input.dock 提示条) ============
    function BindHint(props) {
      const [agents, setAgents] = React.useState([])
      const [showHint, setShowHint] = React.useState(false)
      React.useEffect(() => {
        listAgentsRpc().then(function (r) { if (r && r.ok) setAgents(r.agents || []) }).catch(function () {})
        if (typeof localStorage !== 'undefined') {
          if (!localStorage.getItem('dsfl-hint-dismissed')) setShowHint(true)
        }
      }, [])
      if (agents.length > 0) return null
      const dismiss = function () {
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
    const disposers = [
      slots.inject('sidebar.footer.action', function () {
        return slots.register({
          name: 'sidebar.footer.action',
          id: 'dsh-feishu-link',
          label: function () { return '飞书 IM' },
          order: 6,
        }, SidebarButton)
      }),
      slots.inject('shell.overlay', function () {
        return slots.register({
          name: 'shell.overlay',
          id: 'dsfl-overlay',
          order: 12,
        }, IMStationOverlay)
      }),
      slots.inject('settings.plugins.tab', function () {
        return slots.register({
          name: 'settings.plugins.tab',
          id: 'dsfl-settings',
          order: 50,
          label: function () { return '飞书 IM' },
        }, SettingsPage)
      }),
      slots.inject('conversation.input.dock', function () {
        return slots.register({
          name: 'conversation.input.dock',
          id: 'dsfl-dock',
          order: 41,
        }, BindHint)
      }),
    ]
    ctx.effect(function () {
      return function () { disposers.forEach(function (d) { try { if (d) d() } catch (_) {} }) }
    }, 'dsh-feishu-link: slots')
  },
}
