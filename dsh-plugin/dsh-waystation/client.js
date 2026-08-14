/**
 * DSH-Waystation · Client 半（UX 原型 v3 · 评审反馈迭代）
 *
 * 对应地图 #342：原型 #355（v3 评审）+ 开始此 Issue 流程 #347（host.call 认领 RPC + 模板配置 + 前置黄条）。
 * v3 变更（2026-08-14 评审）：
 *   1. 状态栏固定在输入框正上方（conversation.input.dock 末位行）
 *   2. 交互：去掉「面板」专用按钮；点「就绪/可接/占用」开合面板；时间区做成隐约按键，点击即刷新
 *   3. 面板可拖动（头部）、可调大小（右下角手柄），不再固定右侧遮挡
 *   4. 外观方案（Run 卡内可切换）：4 套 SVG 图标（罗盘/灯塔/雷达/图钉）+ 4 个动作词（沉淀/落纸/存档/快照）
 *
 * 数据源（#344/#346 已接真）：就绪检查走 host.call('wf.status')；面板/地图/票务走
 * host.call('wf.snapshot' | 'wf.refresh')。FIX 仅保留就绪检查兜底；FIX.maps 假地图已移除。
 *
 * 本文件内容 = cordis_define 的 code.client（纯 JS 函数体，返回 Cordis Plugin）。
 */
return {
  apply(ctx) {
    const slots = ctx.get('slots')
    if (slots === undefined) return
    const timer = ctx.get('timer')
    const h = React.createElement

    // ============================================================
    // 0. 样式
    // ============================================================
    styles.insert([
      '.dsws-panel{position:fixed;right:12px;top:12px;width:420px;display:flex;flex-direction:column;background:var(--dsw-alias-bg-layer-2,#16181d);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.45);z-index:9999;font-family:var(--dsw-font-family);font-size:13px;color:var(--dsw-alias-label-primary,#e6edf3);line-height:1.6;overflow:hidden}',
      '.dsws-head{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--dsw-alias-border-l1,#2a2d35);cursor:move;user-select:none}',
      '.dsws-tabs{display:flex;gap:4px;padding:8px 12px 0}',
      '.dsws-tab{padding:4px 10px;border-radius:6px;cursor:pointer;border:1px solid transparent;background:transparent;color:var(--dsw-alias-label-secondary,#a1a1aa);font-size:12px}',
      '.dsws-tab.on{background:var(--dsw-alias-interactive-bg-active,rgba(255,255,255,.14));color:var(--dsw-alias-label-primary,#e6edf3);border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-body{flex:1;overflow-y:auto;padding:10px 12px}',
      '.dsws-resize{position:absolute;right:0;bottom:0;width:18px;height:18px;cursor:nwse-resize;background:linear-gradient(135deg,transparent 50%,var(--dsw-alias-label-caption,#8b8b95) 50%);opacity:.5;border-radius:0 0 12px 0}',
      '.dsws-resize:hover{opacity:1}',
      '.dsws-maprow{border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:8px;padding:10px 12px;margin-bottom:8px;cursor:pointer;background:var(--dsw-alias-bg-layer-1,#10131a)}',
      '.dsws-maprow:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a)}',
      '.dsws-mtitle{font-weight:600;font-size:13px}',
      '.dsws-mdest{color:var(--dsw-alias-label-secondary,#a1a1aa);font-size:12px;margin:2px 0 6px}',
      '.dsws-prog{height:4px;border-radius:2px;background:var(--dsw-alias-bg-layer-3,#0c0e12);overflow:hidden;margin-top:4px}',
      '.dsws-prog>i{display:block;height:100%;background:var(--dsw-alias-state-success-primary,#4ade80);border-radius:2px}',
      '.dsws-chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;line-height:1.7;margin-right:4px;white-space:nowrap}',
      '.dsws-chip-r{background:rgba(88,166,255,.18);color:#58a6ff}',
      '.dsws-chip-p{background:rgba(247,120,186,.16);color:#f778ba}',
      '.dsws-chip-g{background:rgba(63,185,80,.16);color:#3fb950}',
      '.dsws-chip-t{background:rgba(240,136,62,.16);color:#f0883e}',
      '.dsws-chip-m{background:rgba(188,140,255,.16);color:#bc8cff}',
      '.dsws-trow{display:flex;align-items:flex-start;gap:8px;padding:7px 8px;border-radius:6px;border:1px solid transparent}',
      '.dsws-trow:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-trow .dsws-tt{flex:1;min-width:0}',
      '.dsws-tt-name{font-size:12.5px;word-break:break-all}',
      '.dsws-tt-sub{font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-btn{padding:3px 10px;border-radius:6px;border:1px solid var(--dsw-alias-border-l1,#2a2d35);background:var(--dsw-alias-bg-layer-1,#10131a);color:var(--dsw-alias-label-primary,#e6edf3);font-size:12px;cursor:pointer}',
      '.dsws-btn:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a)}',
      '.dsws-btn.primary{background:var(--dsw-alias-button-primary-fill,#c084fc);border-color:transparent;color:#140a1e;font-weight:600}',
      '.dsws-btn.ghost{background:transparent;border-color:transparent;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-grp{margin:10px 0 4px;font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa);display:flex;align-items:center;gap:6px}',
      '.dsws-dot{width:8px;height:8px;border-radius:50%;display:inline-block}',
      '.dsws-modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:10000}',
      '.dsws-modalbox{width:440px;max-width:92vw;background:var(--dsw-alias-bg-layer-2,#16181d);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;padding:14px 16px;font-family:var(--dsw-font-family);font-size:13px;color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-ta{width:100%;min-height:90px;background:var(--dsw-alias-bg-layer-1,#10131a);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:6px;color:var(--dsw-alias-label-primary,#e6edf3);font-family:var(--ds-font-family-code,monospace);font-size:12px;padding:8px;box-sizing:border-box}',
      '.dsws-check{display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px dashed var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-note{position:absolute;right:14px;top:46px;padding:6px 12px;border-radius:6px;background:var(--dsw-alias-toast-bg,#22252c);border:1px solid var(--dsw-alias-border-l1,#2a2d35);color:var(--dsw-alias-label-primary,#e6edf3);font-size:12px;z-index:10001;box-shadow:0 4px 20px rgba(0,0,0,.4)}',
      '.dsws-skill{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px}',
      '.dsws-skill:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06))}',
      '.dsws-skill .dsws-tt{flex:1;min-width:0}',
      '.dsws-remind{display:flex;align-items:center;gap:8px;padding:6px 12px;margin:6px 0;border-radius:8px;background:rgba(188,140,255,.1);border:1px solid rgba(188,140,255,.35);font-size:12px;color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-seg{cursor:pointer;padding:2px 6px;border-radius:6px;border:1px solid transparent}',
      '.dsws-seg:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-timebtn{cursor:pointer;padding:2px 6px;border-radius:6px;border:1px dashed transparent;color:var(--dsw-alias-label-caption,#8b8b95)}',
      '.dsws-timebtn:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08));border-color:var(--dsw-alias-border-l1,#2a2d35);color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-uirow{display:flex;align-items:center;gap:6px;margin:4px 0;flex-wrap:wrap}',
      '.dsws-uirow .dsws-btn.on{border-color:var(--dsw-alias-state-success-primary,#4ade80);color:var(--dsw-alias-state-success-primary,#4ade80)}',
    ].join(''))

    // ============================================================
    // 1. 假数据 fixture（覆盖全状态 + 3 级阻塞链）
    // ============================================================
    const FIX = {
      mode: 'fake',
      updatedAt: '21:30',
      checks: [
        { id: 1, name: '仓库定位', level: 'ok', detail: 'FeatherHunter/SKILLS', hint: '' },
        { id: 2, name: 'setup 已执行', level: 'ok', detail: 'docs/agents/issue-tracker.md 存在', hint: '' },
        { id: 3, name: 'tracker = GitHub', level: 'ok', detail: 'GitHub Issues + gh CLI', hint: '' },
        { id: 4, name: 'gh CLI 可用', level: 'ok', detail: 'D:\\0Tools\\GitHubCLI\\gh.exe (2.97.0)', hint: '' },
        { id: 5, name: 'gh 已登录', level: 'ok', detail: 'FeatherHunter (keyring)', hint: '' },
        { id: 6, name: 'API 可达', level: 'ok', detail: 'api.github.com 200', hint: '' },
        { id: 7, name: 'wayfinder 技能', level: 'warn', detail: '已安装但未挂载到当前会话', hint: '用 /wayfinder 加载' },
        { id: 8, name: 'ask-matt 技能', level: 'warn', detail: '已安装但未挂载到当前会话', hint: '用 /ask-matt 加载' },
      ],
    }

    // ============================================================
    // 2. 技能目录 + 场景推荐映射
    // ============================================================
    const SKILLS = [
      { name: 'ask-matt', level: 'warn', use: '技能路由器：不知道该用哪个 skill 时问它' },
      { name: 'setup-matt-pocock-skills', level: 'ok', use: '仓库初始化：issue tracker / 标签 / 文档路径' },
      { name: 'wayfinder', level: 'warn', use: '巨型项目决策地图（本插件服务的对象）' },
      { name: 'triage', level: 'ok', use: 'issue 状态机流转：categorise→verify→grill' },
      { name: 'grilling', level: 'ok', use: '穷追不舍的对齐提问（设计树）' },
      { name: 'domain-modeling', level: 'ok', use: '领域术语与统一语言' },
      { name: 'research', level: 'ok', use: '后台调研，写进 repo 内 markdown 并引源' },
      { name: 'prototype', level: 'ok', use: '一次性原型回答设计问题' },
      { name: 'implement', level: 'warn', use: '把规格落成代码（task 型 ticket）' },
      { name: 'code-review', level: 'ok', use: '按标准 + 规格双轴审查改动' },
      { name: 'codebase-design', level: 'ok', use: '深模块设计词汇' },
      { name: 'diagnosing-bugs', level: 'ok', use: '硬 bug 与性能回归诊断循环' },
      { name: 'improve-codebase-architecture', level: 'ok', use: '扫 deepening opportunities 出 HTML 报告' },
      { name: 'tdd', level: 'ok', use: '红-绿-重构' },
      { name: 'handoff', level: 'warn', use: '把当前对话压缩成交接文档' },
      { name: 'teach', level: 'ok', use: '跨 session 教你新技能' },
      { name: 'to-spec', level: 'warn', use: '把讨论固化成规格' },
      { name: 'to-tickets', level: 'warn', use: '把规格拆成 tickets' },
      { name: 'resolving-merge-conflicts', level: 'ok', use: '解决合并冲突' },
      { name: 'writing-great-skills', level: 'warn', use: '写出优秀技能' },
    ]
    const TYPE_SKILLS = {
      research: ['research'],
      prototype: ['prototype'],
      grilling: ['grilling', 'domain-modeling'],
      task: ['implement'],
    }
    const TYPE_LABEL = {
      research: ['research', 'r', '🔍 研究'],
      prototype: ['prototype', 'p', '🛠 原型'],
      grilling: ['grilling', 'g', '💬 对齐'],
      task: ['task', 't', '⚙ 任务'],
    }

    // ============================================================
    // 3. 外观方案（图标 + 动作词，可切换）
    // ============================================================
    const ICON_SCHEMES = [
      { id: 'compass', label: '罗盘' },
      { id: 'beacon', label: '灯塔' },
      { id: 'radar', label: '雷达' },
      { id: 'pin', label: '图钉' },
    ]
    const WORD_SCHEMES = ['沉淀', '落纸', '存档', '快照']

    const Icon = ({ scheme, size }) => {
      const s = size || 16
      const common = { viewBox: '0 0 24 24', width: s, height: s, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', style: { display: 'inline-block', verticalAlign: '-2px' } }
      if (scheme === 'beacon') return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 4, fill: 'currentColor', stroke: 'none' }), h('path', { d: 'M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1' })])
      if (scheme === 'radar') return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('circle', { cx: 12, cy: 12, r: 5 }), h('circle', { cx: 12, cy: 12, r: 1.2, fill: 'currentColor', stroke: 'none' }), h('path', { d: 'M12 12L19 8' }), h('circle', { cx: 16.5, cy: 6.5, r: 1.1, fill: 'currentColor', stroke: 'none' })])
      if (scheme === 'pin') return h('svg', common, [h('path', { d: 'M12 21s-6-5.1-6-10a6 6 0 1112 0c0 4.9-6 10-6 10z' }), h('circle', { cx: 12, cy: 11, r: 2.2, fill: 'currentColor', stroke: 'none' })])
      return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('polygon', { points: '15.5 8.5 13 13 8.5 15.5 11 11', fill: 'currentColor', stroke: 'none' })])
    }

    // ============================================================
    // 4. 迷你 store（跨插槽共享状态）
    // ============================================================
    const S = {
      open: false, tab: 'maps', activeMap: null, startFor: null, fixateFor: null,
      notice: null, injector: null, remindDismissed: false, tick: 0,
      pos: null, size: { w: 420, h: null },
      ui: { icon: 'compass', word: '沉淀' },
      snapshot: null, cfgOpen: false,
      checks: null, checksUpdatedAt: '', checksMode: 'loading', checksError: null, checking: false,
      snapMode: 'loading', snapError: null, snapLoading: false,
    }
    const subs = []
    const emit = () => { S.tick++; subs.forEach(function (f) { f(S.tick) }) }
    const sub = (f) => { subs.push(f); return () => { const i = subs.indexOf(f); if (i >= 0) subs.splice(i, 1) } }
    const flash = (msg) => {
      S.notice = msg; emit()
      if (timer !== undefined) timer.timeout(function () { if (S.notice === msg) { S.notice = null; emit() } }, 2800)
    }
    const useStore = () => {
      const [, set] = React.useState(0)
      React.useEffect(() => sub((n) => set(n)), [])
      return S
    }
    const WORD = () => S.ui.word

    // 派生：票务分组（frontier/claimed/blocked/closed · #346 接真快照）
    const compute = () => {
      const maps = (S.snapshot && Array.isArray(S.snapshot.maps)) ? S.snapshot.maps : []
      return maps.map(function (m) {
        const byNum = {}; m.tickets.forEach(function (t) { byNum[t.number] = t })
        const openBlocker = (b) => { const t = byNum[b]; return t !== undefined && t.state === 'OPEN' }
        const open = m.tickets.filter(function (t) { return t.state === 'OPEN' })
        const closed = m.tickets.filter(function (t) { return t.state === 'CLOSED' })
        const frontier = open.filter(function (t) { return !t.claimedBy && !t.blockedBy.some(openBlocker) })
        const claimed = open.filter(function (t) { return t.claimedBy })
        const blocked = open.filter(function (t) { return !t.claimedBy && t.blockedBy.some(openBlocker) })
        return { m: m, open: open, closed: closed, frontier: frontier, claimed: claimed, blocked: blocked }
      })
    }
    const frontierAll = () => compute().reduce(function (n, g) { return n + g.frontier.length }, 0)

    // ---- 就绪检查（#344 · host.call('wf.status') 真数据；host 侧 30s 缓存 / force 重查）----
    const CHECKS_TOTAL = 8
    const loadChecks = (force) => {
      if (S.checking) return
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        S.checksMode = 'err'
        S.checksError = 'host.call 不可用（Host 半未加载）'
        emit()
        return
      }
      S.checking = true
      emit()
      host.call('wf.status', force ? { force: true } : {}).then(function (res) {
        S.checking = false
        if (res && res.checks && res.checks.length) {
          S.checks = res.checks
          S.checksUpdatedAt = nowStr()
          S.checksMode = 'real'
          S.checksError = null
        } else {
          S.checksMode = 'err'
          S.checksError = (res && res.error) ? String(res.error).slice(0, 160) : 'wf.status 返回空结果'
        }
        emit()
      }).catch(function (e) {
        S.checking = false
        S.checksMode = 'err'
        S.checksError = String((e && e.message) || e).slice(0, 160)
        emit()
      })
    }
    const activeChecks = () => (S.checks && S.checks.length ? S.checks : FIX.checks)
    const readyCount = () => activeChecks().filter(function (c) { return c.level === 'ok' }).length
    const setupCheck = () => (S.checks || []).find(function (c) { return c.id === 2 })

    const blockerNames = (t, m) => t.blockedBy.map(function (b) {
      const bt = m.tickets.find(function (x) { return x.number === b })
      return bt ? bt.title : ('#' + b)
    }).join('；')

    // ============================================================
    // 5. 文本生成 + 注入
    // ============================================================
    const nowStr = () => {
      try { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0') } catch (e) { return '' }
    }
    // 开始模板配置（#347 · localStorage 持久化）：是否带 /wayfinder 前缀 + 自定义模板
    const START_CFG_KEY = 'dsws.startCfg'
    const startCfg = (function () {
      const d = { withWayfinder: true, custom: '' }
      try {
        const raw = localStorage.getItem(START_CFG_KEY)
        if (raw) return Object.assign(d, JSON.parse(raw))
      } catch (e) { /* 存储不可用用默认 */ }
      return d
    })()
    const saveStartCfg = function () { try { localStorage.setItem(START_CFG_KEY, JSON.stringify(startCfg)) } catch (e) {} }

    // 真数据快照（#346：面板数据源；force 走 wf.refresh 全量重建；wf.snapshot 侧 5s 缓存）
    const loadSnapshot = function (force) {
      if (S.snapLoading) return
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        S.snapMode = 'err'
        S.snapError = 'host.call 不可用（Host 半未加载）'
        emit()
        return
      }
      S.snapLoading = true
      S.snapMode = 'loading'
      emit()
      const p = force ? host.call('wf.refresh', {}) : host.call('wf.snapshot', {})
      p.then(function (snap) {
        S.snapLoading = false
        if (snap && snap.ok === true && Array.isArray(snap.maps)) {
          S.snapshot = snap
          S.snapMode = 'real'
          S.snapError = null
        } else {
          S.snapMode = 'err'
          S.snapError = (snap && snap.error) ? String(snap.error).slice(0, 160) : 'wf.snapshot 返回异常'
        }
        emit()
      }).catch(function (e) {
        S.snapLoading = false
        S.snapMode = 'err'
        S.snapError = String((e && e.message) || e).slice(0, 160)
        emit()
      })
    }

    const repoStr = () => (S.snapshot && S.snapshot.repo)
      ? S.snapshot.repo.owner + '/' + S.snapshot.repo.name
      : 'FeatherHunter/SKILLS'

    const startText = (t) => {
      const url = 'https://github.com/' + repoStr() + '/issues/' + t.number
      if (startCfg.custom) {
        return startCfg.custom
          .replace(/\{number\}/g, String(t.number))
          .replace(/\{url\}/g, url)
          .replace(/\{title\}/g, t.title)
      }
      const body = url +
        '\n\n⚠️ 本 ticket 应在**独立的新会话**中执行（wayfinder 语义：每张 ticket 一个会话，设计者要求彼此独立）。' +
        '保持当前工作目录；会话命名建议：' + newSessionTitle(t) +
        '\n\n请按 wayfinder 流程处理这个 ticket：先加载所属 map 的低分辨率视图对齐 Destination，认领该 ticket，再用 Notes 中指定的技能（如 /research）解析它；完成后以 resolution comment 收尾并关闭 issue。本 session 只解析这一个 ticket。'
      return (startCfg.withWayfinder ? '/wayfinder\n' : '') + body
    }
    // 会话命名格式（拍板：与插件 DSH-Waystation 同名前缀）
    const SESSION_TITLE_PREFIX = '[dsh-waystation]'
    const newSessionTitle = (t) => SESSION_TITLE_PREFIX + ' ' + t.title + ' #' + t.number

    // 一键开新会话（拍板后新增需求）：同 cwd + 自动命名 + 切换；任何一步失败降级为提醒手动
    const openInNewSession = async function (t) {
      const sessions = ctx.get('sessions')
      if (sessions === undefined || typeof sessions.create !== 'function' || typeof sessions.open !== 'function') {
        flash('⚠️ 无法自动开新会话（sessions 服务不可用）：请手动开新会话，命名「' + newSessionTitle(t) + '」')
        return false
      }
      let cwd = ''
      try {
        const st = await host.call('wf.status')
        if (st && st.cwd) cwd = st.cwd
      } catch (e) { /* cwd 不可得 → 走 host 默认项目目录 */ }
      try {
        const res = await sessions.create(cwd ? { cwd: cwd } : {})
        const sid = res && res.sessionId
        if (!sid) {
          flash('⚠️ 开新会话失败：' + String(((res && res.error) || '未知')).slice(0, 120) + '（可手动开新会话）')
          return false
        }
        let renamed = false
        try {
          const scoped = (typeof sessions.scope === 'function') ? sessions.scope(sid) : undefined
          const face = (scoped && typeof sessions.sessionOf === 'function') ? sessions.sessionOf(scoped) : undefined
          if (face && typeof face.rename === 'function') {
            const rr = await face.rename(newSessionTitle(t))
            renamed = !!(rr && rr.title)
          }
        } catch (e2) { renamed = false }
        if (renamed) flash('✅ 已开新会话并命名：「' + newSessionTitle(t) + '」')
        else flash('✅ 已开新会话（自动命名不可用，可手动重命名）：' + newSessionTitle(t))
        try { sessions.open(sid) } catch (e3) { flash('新会话已创建（' + newSessionTitle(t) + '），请从会话列表打开') }
        return true
      } catch (e) {
        flash('⚠️ 开新会话失败：' + String((e && e.message) || e).slice(0, 120) + '（请手动开新会话）')
        return false
      }
    }
    const fixateText = (t) => '【' + WORD() + ' ' + nowStr() + '】' + t.title + ' #' + t.number + '\n\n'
    const inject = (text) => {
      if (S.injector) { S.injector(text); flash('✅ 已注入输入框（inputActions.setDraft），确认后发送') }
      else if (typeof navigator !== 'undefined' && navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () { flash('📋 已复制到剪贴板（输入框不可用，兜底）') }).catch(function () { flash('复制失败，请手动粘贴') })
      } else flash('无法注入：输入框不可用')
    }

    // ============================================================
    // 6. 组件
    // ============================================================
    const Dot = ({ level }) => h('span', { className: 'dsws-dot', style: { background: level === 'ok' ? '#4ade80' : level === 'warn' ? '#f59e0b' : level === 'bad' ? '#f87171' : '#52525b' } })
    const TypeChip = ({ type }) => {
      const t = TYPE_LABEL[type] || [type, '', type]
      const cls = { research: 'dsws-chip-r', prototype: 'dsws-chip-p', grilling: 'dsws-chip-g', task: 'dsws-chip-t' }[type] || ''
      return h('span', { className: 'dsws-chip ' + cls }, t[2])
    }

    // ---- 6.1 侧栏脚部入口 ----
    const SidebarButton = () => {
      const s = useStore()
      return h('button', {
        onClick: function () { s.open = !s.open; emit() },
        style: { display: 'flex', alignItems: 'center', gap: 6, background: 'transparent', border: 'none', color: 'var(--dsw-alias-label-primary,#e6edf3)', fontSize: 12, cursor: 'pointer', padding: '4px 6px', borderRadius: 6 },
      }, [
        h('span', { style: { color: readyCount() === activeChecks().length ? '#4ade80' : '#f59e0b' } }, Icon({ scheme: s.ui.icon, size: 15 })),
        h('span', null, 'Waystation'),
        h('span', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 11 } }, readyCount() + '/' + activeChecks().length + ' · ' + frontierAll() + ' 可接'),
      ])
    }

    // ---- 6.2 输入区状态条（输入框正上方 · 兼注入落点 · #344 接真）----
    const StatusBar = (props) => {
      const s = useStore()
      React.useEffect(function () {
        if (props && props.inputActions && typeof props.inputActions.setDraft === 'function') s.injector = props.inputActions.setDraft
      }, [props])
      React.useEffect(function () { loadChecks(false); loadSnapshot(false) }, [])
      const fr = frontierAll()
      const blk = compute().reduce(function (n, g) { return n + g.blocked.length + g.claimed.length }, 0)
      const cs = activeChecks()
      const toggle = function () { s.open = !s.open; emit() }
      const refresh = function () { loadChecks(true); loadSnapshot(true) }
      const modeTag = (s.checksMode === 'real' && S.snapMode === 'real') ? ' · 真数据' : s.checksMode === 'real' ? ' · 就绪真数据' : s.checksMode === 'err' ? ' · 就绪异常' : s.checksMode === 'loading' ? ' · 检测中…' : (FIX.mode === 'fake' ? ' · 假数据' : '')
      const timeStr = (S.snapshot && S.snapshot.updatedAt) ? String(S.snapshot.updatedAt).slice(11, 16) : (s.checksUpdatedAt || FIX.updatedAt)
      const setup = setupCheck()
      const amber = s.checksMode === 'real' && setup && setup.level !== 'ok'
      const row = h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', padding: '2px 4px', flexWrap: 'wrap' } }, [
        h('span', { style: { display: 'flex', alignItems: 'center', gap: 5, marginRight: 2 } }, Icon({ scheme: s.ui.icon, size: 14 })),
        h('span', null, 'Waystation'),
        h('span', { className: 'dsws-seg', onClick: toggle, style: { color: readyCount() === cs.length ? '#4ade80' : '#f59e0b' } }, '● 就绪 ' + readyCount() + '/' + cs.length),
        h('span', { className: 'dsws-seg', onClick: toggle, style: { color: '#4ade80' } }, '🟢 可接 ' + fr),
        h('span', { className: 'dsws-seg', onClick: toggle, style: { color: '#f0883e' } }, '🔒 占用 ' + blk),
        h('span', { className: 'dsws-timebtn', onClick: refresh, title: '点击重新检查（就绪 + 面板快照）' }, '更新 ' + timeStr + modeTag),
        s.notice ? h('span', { style: { color: 'var(--dsw-alias-state-success-primary,#4ade80)' } }, s.notice) : null,
      ])
      if (!amber) return row
      return h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 } }, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(245,158,11,.12)', border: '1px solid rgba(245,158,11,.45)', color: '#fbbf24', borderRadius: 6, padding: '3px 10px', fontSize: 12 } }, [
          h('span', null, '⚠️ 本仓库尚未初始化 Matt 技能配置（setup 未跑）'),
          h('button', { className: 'dsws-btn', style: { borderColor: 'rgba(245,158,11,.6)' }, onClick: function () { inject('/setup-matt-pocock-skills\n（请选择 GitHub Issues 作为 issue tracker）') } }, '帮我执行 /setup-matt-pocock-skills'),
        ]),
        row,
      ])
    }

    // ---- 6.3 票务行 ----
    const TicketRow = ({ g, t }) => {
      const s = useStore()
      const canStart = t.state === 'OPEN' && !t.claimedBy && !t.blockedBy.some(function (b) {
        const bt = g.m.tickets.find(function (x) { return x.number === b }); return bt && bt.state === 'OPEN'
      })
      return h('div', { className: 'dsws-trow' }, [
        h('div', { className: 'dsws-tt' }, [
          h('div', { className: 'dsws-tt-name' }, [
            TypeChip({ type: t.type }),
            h('span', null, t.title),
            h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)', fontSize: 11 } }, ' #' + t.number),
          ]),
          h('div', { className: 'dsws-tt-sub' }, [
            t.claimedBy ? h('span', { style: { color: '#58a6ff' } }, '🔵 已认领 ' + t.claimedBy + '　') : null,
            t.blockedBy.length ? h('span', { style: { color: '#f0883e' } }, '🔒 被阻塞：' + blockerNames(t, g.m)) : null,
            t.state === 'CLOSED' ? h('span', { style: { color: '#3fb950' } }, '✅ 已关闭' + (t.resolution ? ' · ' + t.resolution : '')) : null,
          ]),
        ]),
        t.state === 'OPEN' ? h('div', { style: { display: 'flex', gap: 4 } }, [
          canStart ? h('button', { className: 'dsws-btn primary', onClick: function () { s.startFor = t; emit() } }, '▶ 开始此 Issue') : null,
          h('button', { className: 'dsws-btn', onClick: function () { s.fixateFor = t; emit() } }, WORD()),
          h('a', { className: 'dsws-btn ghost', href: 'https://github.com/FeatherHunter/SKILLS/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none' } }, '🔗'),
        ]) : h('a', { className: 'dsws-btn ghost', href: 'https://github.com/FeatherHunter/SKILLS/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none' } }, '查看'),
      ])
    }

    // ---- 6.4 地图详情 ----
    const MapDetail = ({ g }) => {
      const s = useStore()
      const m = g.m
      return h('div', null, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 } }, [
          h('button', { className: 'dsws-btn', onClick: function () { s.activeMap = null; emit() } }, '← 全部地图'),
          h('span', { className: 'dsws-chip dsws-chip-m' }, 'wayfinder:map'),
        ]),
        h('div', { className: 'dsws-mtitle' }, m.title),
        m.error ? h('div', { style: { color: '#f87171', fontSize: 11, marginBottom: 6 } }, '⚠️ ' + String((m.error && m.error.error) || '加载失败').slice(0, 160)) : null,
        h('div', { className: 'dsws-mdest' }, '🎯 ' + (m.destination || '（未填写 Destination）')),
        h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginBottom: 4 } }, '📝 Notes：' + m.notes),
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Decisions so far（' + m.decisions.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.decisions.map(function (d, i) {
            return h('div', { key: i }, '· ' + d.title + '（' + d.gist + '）')
          })),
        ]),
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Not yet specified（战雾 ' + m.fog.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.fog.map(function (f, i) { return h('div', { key: i }, '🌫 ' + f) })),
        ]),
        h('details', { style: { marginBottom: 8 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Out of scope（' + m.outOfScope.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.outOfScope.map(function (o, i) { return h('div', { key: i }, '🚫 ' + o) })),
        ]),
        h('div', { className: 'dsws-grp' }, [h('span', { className: 'dsws-dot', style: { background: '#4ade80' } }), h('span', null, '🟢 可接（frontier · ' + g.frontier.length + '）')]),
        g.frontier.map(function (t) { return h(TicketRow, { key: t.number, g: g, t: t }) }),
        h('div', { className: 'dsws-grp' }, [h('span', { className: 'dsws-dot', style: { background: '#58a6ff' } }), h('span', null, '🔵 已认领（' + g.claimed.length + '）')]),
        g.claimed.map(function (t) { return h(TicketRow, { key: t.number, g: g, t: t }) }),
        h('div', { className: 'dsws-grp' }, [h('span', { className: 'dsws-dot', style: { background: '#f0883e' } }), h('span', null, '🔒 被阻塞（' + g.blocked.length + '）')]),
        g.blocked.map(function (t) { return h(TicketRow, { key: t.number, g: g, t: t }) }),
        h('details', { style: { marginTop: 8 } }, [
          h('summary', { className: 'dsws-grp', style: { margin: '6px 0 2px', cursor: 'pointer' } }, [h('span', { className: 'dsws-dot', style: { background: '#52525b' } }), h('span', null, '✅ 已关闭（' + g.closed.length + '）')]),
          h('div', null, g.closed.map(function (t) { return h(TicketRow, { key: t.number, g: g, t: t }) })),
        ]),
      ])
    }

    // ---- 6.5 地图列表（#346：真快照 + 刷新/加载/错误态）----
    const MapList = () => {
      const s = useStore()
      const groups = compute()
      const repoTag = (S.snapshot && S.snapshot.repo) ? S.snapshot.repo.owner + '/' + S.snapshot.repo.name : ''
      return h('div', null, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 } }, [
          h('span', { className: 'dsws-grp', style: { margin: 0 } }, '🗺 地图 ' + groups.length + ' 张' + (repoTag ? ' · ' + repoTag : '')),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', onClick: function () { loadSnapshot(true) }, style: { fontSize: 11, padding: '2px 8px' } }, '↻ 刷新'),
        ]),
        S.snapMode === 'loading' ? h('div', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 12, padding: '14px 0', textAlign: 'center' } }, '加载中…（拉取全部 wayfinder:map 与子票）') : null,
        S.snapMode === 'err' ? h('div', { style: { color: '#f87171', fontSize: 12, padding: '14px 0', textAlign: 'center' } }, '⚠️ 快照加载失败：' + s.snapError) : null,
        groups.map(function (g) {
          const m = g.m
          const pct = m.tickets.length ? Math.round(g.closed.length / m.tickets.length * 100) : 0
          return h('div', { key: m.number, className: 'dsws-maprow', onClick: function () { s.activeMap = m.number; emit() } }, [
            h('div', { className: 'dsws-mtitle' }, m.title),
            h('div', { className: 'dsws-mdest' }, '🎯 ' + (m.destination || '（未填写 Destination）')),
            m.error ? h('div', { style: { color: '#f87171', fontSize: 11, marginBottom: 4 } }, '⚠️ ' + String((m.error && m.error.error) || '加载失败').slice(0, 120)) : null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, [
              h('span', null, '进度 ' + g.closed.length + '/' + m.tickets.length),
              h('span', { style: { color: '#4ade80' } }, '🟢 可接 ' + g.frontier.length),
              h('span', { style: { color: '#f0883e' } }, '🔒 ' + (g.blocked.length + g.claimed.length)),
            ]),
            h('div', { className: 'dsws-prog' }, [h('i', { style: { width: pct + '%' } })]),
          ])
        }),
      ])
    }

    // ---- 6.6 技能雷达 ----
    const SkillsTab = () => {
      const s = useStore()
      const groups = compute()
      let rec = []
      let recTitle = '通用建议'
      if (s.startFor) {
        rec = TYPE_SKILLS[s.startFor.type] || []
        recTitle = '「' + s.startFor.title + '」按类型推荐'
      } else if (s.activeMap !== null) {
        const g = groups.find(function (x) { return x.m.number === s.activeMap })
        if (g && /research/.test(g.m.notes)) rec = ['research']
        if (g && /grill/.test(g.m.notes)) rec = ['grilling', 'domain-modeling']
        recTitle = '「' + g.m.title + '」Notes 指定'
      }
      if (!rec.length) rec = ['ask-matt']
      const list = SKILLS.map(function (sk) {
        const on = rec.indexOf(sk.name) >= 0
        return h('div', { key: sk.name, className: 'dsws-skill', style: on ? { background: 'rgba(188,140,255,.12)', borderRadius: 6 } : null }, [
          Dot({ level: sk.level }),
          h('div', { className: 'dsws-tt' }, [
            h('div', { className: 'dsws-tt-name', style: on ? { color: '#c084fc' } : null }, '/' + sk.name + (on ? ' ★' : '')),
            h('div', { className: 'dsws-tt-sub' }, sk.use),
          ]),
          h('button', { className: 'dsws-btn', onClick: function () { inject('/' + sk.name) } }, '加载'),
        ])
      })
      return h('div', null, [
        h('div', { className: 'dsws-grp' }, '🧭 ' + recTitle),
        h('div', { style: { marginBottom: 8 } }, rec.map(function (r, i) {
          return h('span', { key: i, className: 'dsws-chip dsws-chip-m' }, '/' + r)
        })),
        list,
      ])
    }

    // ---- 6.7 就绪检查（#344 · 真数据 wf.status；host 不可用时假数据兜底）----
    const ChecksTab = () => {
      const s = useStore()
      React.useEffect(function () { loadChecks(false) }, [])
      const cs = activeChecks()
      return h('div', null, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 } }, [
          h('span', null, '就绪 ' + readyCount() + '/' + CHECKS_TOTAL + '（双层探测：DSH 会话级 + 文件系统级）'),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', onClick: function () { loadChecks(true) }, style: { fontSize: 11, padding: '2px 8px' } }, '↻ 重新检查'),
        ]),
        s.checksMode === 'err' ? h('div', { style: { color: '#f87171', fontSize: 12, marginBottom: 6 } }, '⚠️ 就绪检测失败：' + s.checksError + '（展示假数据兜底）') : null,
        s.checksMode === 'loading' ? h('div', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 12, marginBottom: 6 } }, '检测中…') : null,
        cs.map(function (c) {
          return h('div', { key: c.id, className: 'dsws-check' }, [
            Dot({ level: c.level }),
            h('div', { style: { flex: 1 } }, [
              h('div', { className: 'dsws-tt-name' }, c.name),
              h('div', { className: 'dsws-tt-sub' }, c.detail + (c.hint ? ' → ' + c.hint : '')),
            ]),
          ])
        }),
      ])
    }

    // ---- 6.8 主面板（可拖动 · 可调大小）----
    const OverlayPanel = () => {
      const s = useStore()
      const dragRef = React.useRef(null)
      React.useEffect(function () { if (s.open) loadSnapshot(false) }, [s.open])
      if (!s.open) return null
      const groups = compute()
      const active = s.activeMap !== null ? groups.find(function (x) { return x.m.number === s.activeMap }) : null
      const tabBtn = (id, label) => h('button', { className: 'dsws-tab' + (s.tab === id ? ' on' : ''), onClick: function () { s.tab = id; emit() } }, label)

      const onHeaderDown = function (e) {
        if (typeof document === 'undefined' || typeof window === 'undefined') return
        const w = s.size.w || 420
        dragRef.current = {
          sx: e.clientX, sy: e.clientY,
          px: s.pos ? s.pos.x : window.innerWidth - w - 12,
          py: s.pos ? s.pos.y : 12,
        }
        const mm = function (ev) { s.pos = { x: dragRef.current.px + ev.clientX - dragRef.current.sx, y: dragRef.current.py + ev.clientY - dragRef.current.sy }; emit() }
        const mu = function () { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu) }
        document.addEventListener('mousemove', mm)
        document.addEventListener('mouseup', mu)
      }
      const onResizeDown = function (e) {
        e.stopPropagation()
        if (typeof document === 'undefined' || typeof window === 'undefined') return
        const r0 = { sw: s.size.w || 420, sh: s.size.h || (window.innerHeight - 24), sx: e.clientX, sy: e.clientY }
        const mm = function (ev) { s.size = { w: Math.min(900, Math.max(320, r0.sw + ev.clientX - r0.sx)), h: Math.min(920, Math.max(240, r0.sh + ev.clientY - r0.sy)) }; emit() }
        const mu = function () { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu) }
        document.addEventListener('mousemove', mm)
        document.addEventListener('mouseup', mu)
      }

      const panelStyle = { width: s.size.w, ...(s.size.h ? { height: s.size.h } : {}), ...(s.pos ? { left: s.pos.x, top: s.pos.y, right: 'auto' } : { right: 12, top: 12 }) }
      return h('div', { className: 'dsws-panel', style: panelStyle }, [
        h('div', { className: 'dsws-head', onMouseDown: onHeaderDown }, [
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 } }, Icon({ scheme: s.ui.icon, size: 17 }), 'DSH-Waystation'),
          h('span', { className: 'dsws-chip ' + (S.snapMode === 'err' ? 'dsws-chip-t' : 'dsws-chip-m') }, S.snapMode === 'real' ? '真数据' : S.snapMode === 'err' ? '快照异常' : S.snapMode === 'loading' ? '加载中…' : '原型 · 假数据'),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn ghost', onClick: function () { s.open = false; emit() } }, '✕'),
        ]),
        h('div', { className: 'dsws-tabs' }, [tabBtn('maps', '🗺 地图'), tabBtn('skills', '🧭 技能'), tabBtn('checks', '⚙ 就绪')]),
        h('div', { className: 'dsws-body' }, [
          s.tab === 'maps' ? (active ? h(MapDetail, { g: active }) : h(MapList, null)) : null,
          s.tab === 'skills' ? h(SkillsTab, null) : null,
          s.tab === 'checks' ? h(ChecksTab, null) : null,
        ]),
        h('div', { className: 'dsws-resize', onMouseDown: onResizeDown, title: '拖动调整大小' }),
        s.notice ? h('div', { className: 'dsws-note' }, s.notice) : null,
        s.startFor ? h(StartModal, { t: s.startFor }) : null,
        s.fixateFor ? h(FixateModal, { t: s.fixateFor }) : null,
        s.cfgOpen ? h(StartCfgModal, null) : null,
      ])
    }

    // ---- 6.9 开始此 Issue 确认框（#347 认领 RPC + 黄条；新会话增强：提醒 + 一键开新会话同 cwd + 自动命名）----
    const StartModal = ({ t }) => {
      const s = useStore()
      const [claim, setClaim] = React.useState(true)
      const [openInNew, setOpenInNew] = React.useState(true)
      const [warnings, setWarnings] = React.useState([])
      const [busy, setBusy] = React.useState(false)
      const rec = TYPE_SKILLS[t.type] || []
      React.useEffect(function () {
        let alive = true
        const probe = async function () {
          const w = []
          try {
            if (typeof host !== 'undefined' && typeof host.call === 'function') {
              try {
                const st = await host.call('wf.status')
                if (st && st.checks && st.checks.length) {
                  st.checks.forEach(function (c) {
                    if (!c.ok) w.push(c.name + '：' + (c.hint || c.detail || '未就绪'))
                  })
                  if (alive) { setWarnings(w); return }
                }
              } catch (e) {
                if (!/not registered|method-not-found/.test(String((e && e.message) || e))) w.push('就绪检测失败：' + String((e && e.message) || e))
              }
              // wf.status 未注册（#344 未落地时）→ 快照 env 兜底
              const snap = s.snapshot || await host.call('wf.snapshot')
              if (snap && snap.ok === false) w.push('GitHub 快照失败：' + String(snap.error || '未知').slice(0, 80))
              else if (snap && snap.env && !snap.env.ghPath) w.push('gh CLI 不可用：' + (snap.env.ghError || '未找到'))
            }
          } catch (e2) { /* 探测失败不阻断 */ }
          if (alive) setWarnings(w)
        }
        probe()
        return function () { alive = false }
      }, [])
      const confirm = async function () {
        if (busy) return
        const n = t.number
        if (claim && typeof host !== 'undefined' && typeof host.call === 'function') {
          setBusy(true)
          try {
            const res = await host.call('wf.claim', { number: n })
            if (res && res.ok) {
              t.claimedBy = res.assignedTo || '已认领'
              flash('✅ 已认领 #' + n + '（GitHub assignee 已更新）')
              try { host.call('wf.refresh', {}) } catch (e2) { /* 刷新失败不阻断 */ }
            } else {
              const err = (res && res.error) ? ((res.error && res.error.error) || res.error) : '未知错误'
              flash('⚠️ 认领失败（仍会注入）：' + String(err).slice(0, 120))
            }
          } catch (e) {
            flash('⚠️ 认领失败（仍会注入）：' + String((e && e.message) || e).slice(0, 120))
          }
          setBusy(false)
        } else if (claim) {
          t.claimedBy = '已认领'
          flash('⚠️ 无 Host 认领能力：已本地标记（需加载插件 Host 半）')
        }
        // 2) 开新会话（勾选时：create+rename+open 内部完成；失败自动降级为提醒）
        let opened = false
        if (openInNew) { opened = await openInNewSession(t) }
        // 3) 注入/复制指令（新会话就绪用）：已切走时走剪贴板，否则写入当前输入框
        const text = startText(t)
        if (opened) {
          try {
            if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
              await navigator.clipboard.writeText(text)
              flash('✅ 指令已复制，请在新会话中粘贴发送')
            } else { inject(text) }
          } catch (e) { inject(text) }
        } else {
          inject(text)
        }
        s.startFor = null
        emit()
      }
      return h('div', { className: 'dsws-modal', onClick: function () { if (!busy) { s.startFor = null; emit() } } }, [
        h('div', { className: 'dsws-modalbox', onClick: function (e) { e.stopPropagation() } }, [
          warnings.length ? h('div', { style: { background: 'rgba(245,158,11,.12)', border: '1px solid rgba(245,158,11,.45)', color: '#f59e0b', borderRadius: 6, padding: '6px 10px', fontSize: 12, marginBottom: 10 } }, '⚠️ 前置未就绪：' + warnings.join('；') + '（不阻断，可继续）') : null,
          h('div', { style: { background: 'rgba(188,140,255,.1)', border: '1px solid rgba(188,140,255,.35)', color: '#c084fc', borderRadius: 6, padding: '6px 10px', fontSize: 12, marginBottom: 10 } }, '⚠️ 每张 ticket 应在**独立的新会话**中完成（wayfinder 语义）。勾选后：保持当前工作目录开新会话 → 自动命名「' + SESSION_TITLE_PREFIX + ' <标题> #号」→ /wayfinder 指令就绪供新会话发送'),
          h('div', { style: { fontWeight: 600, marginBottom: 8 } }, '▶ 开始此 Issue'),
          h('div', { style: { marginBottom: 4 } }, [TypeChip({ type: t.type }), h('span', null, t.title), h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)' } }, ' #' + t.number)]),
          h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', marginBottom: 8 } }, '推荐技能：' + (rec.length ? rec.map(function (r) { return '/' + r }).join(' + ') : '（无）') + '　·　注入后将自动带上 /wayfinder 与流程指令'),
          h('label', { style: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginBottom: 6, cursor: 'pointer' } }, [
            h('input', { type: 'checkbox', checked: claim, disabled: busy, onChange: function (e) { setClaim(e.target.checked) } }),
            h('span', null, '同时认领（assign 给自己 · wayfinder 的 claim 语义）'),
          ]),
          h('label', { style: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginBottom: 12, cursor: 'pointer' } }, [
            h('input', { type: 'checkbox', checked: openInNew, disabled: busy, onChange: function (e) { setOpenInNew(e.target.checked) } }),
            h('span', null, '同时在新会话中打开（保持当前工作目录 · 自动命名）'),
          ]),
          h('div', { style: { display: 'flex', gap: 8, justifyContent: 'flex-end' } }, [
            h('button', { className: 'dsws-btn', disabled: busy, onClick: function () { s.startFor = null; emit() } }, '取消'),
            h('button', { className: 'dsws-btn primary', disabled: busy, onClick: confirm }, busy ? '认领中…' : '确认开始'),
          ]),
        ]),
      ])
    }

    // ---- 6.10 动作弹窗（原「固化」，词随方案）----
    const FixateModal = ({ t }) => {
      const s = useStore()
      const [text, setText] = React.useState(fixateText(t))
      const doSave = function (withComment) {
        s.fixateFor = null; emit()
        if (withComment) flash('✅ 已' + WORD() + '（原型）：本地 .scratch/wayfinder-notes/… + gh issue comment #' + t.number)
        else flash('✅ 已' + WORD() + '（原型）：仅本地 .scratch/wayfinder-notes/…')
      }
      return h('div', { className: 'dsws-modal', onClick: function () { s.fixateFor = null; emit() } }, [
        h('div', { className: 'dsws-modalbox', onClick: function (e) { e.stopPropagation() } }, [
          h('div', { style: { fontWeight: 600, marginBottom: 8 } }, WORD() + '讨论 → ' + t.title + ' #' + t.number),
          h('textarea', { className: 'dsws-ta', value: text, onChange: function (e) { setText(e.target.value) } }),
          h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', margin: '6px 0' } }, '本地：.scratch/wayfinder-notes/<map>/<n>-<slug>.md 追加　·　GitHub：resolution comment 到 #' + t.number),
          h('div', { style: { display: 'flex', gap: 8, justifyContent: 'flex-end' } }, [
            h('button', { className: 'dsws-btn', onClick: function () { s.fixateFor = null; emit() } }, '取消'),
            h('button', { className: 'dsws-btn', onClick: function () { doSave(false) } }, '仅本地保存'),
            h('button', { className: 'dsws-btn primary', onClick: function () { doSave(true) } }, '保存并评论到 Issue'),
          ]),
        ]),
      ])
    }

    // ---- 6.10b 开始模板配置（#347：/wayfinder 前缀 + 自定义模板）----
    const StartCfgModal = () => {
      const s = useStore()
      const [wf, setWf] = React.useState(startCfg.withWayfinder)
      const [custom, setCustom] = React.useState(startCfg.custom)
      const save = function () { startCfg.withWayfinder = wf; startCfg.custom = custom; saveStartCfg(); s.cfgOpen = false; emit(); flash('✅ 开始模板已保存') }
      const reset = function () { startCfg.withWayfinder = true; startCfg.custom = ''; saveStartCfg(); setWf(true); setCustom('') }
      return h('div', { className: 'dsws-modal', onClick: function () { s.cfgOpen = false; emit() } }, [
        h('div', { className: 'dsws-modalbox', onClick: function (e) { e.stopPropagation() } }, [
          h('div', { style: { fontWeight: 600, marginBottom: 8 } }, '开始模板配置'),
          h('label', { style: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginBottom: 8, cursor: 'pointer' } }, [
            h('input', { type: 'checkbox', checked: wf, onChange: function (e) { setWf(e.target.checked) } }),
            h('span', null, '注入文本带 /wayfinder 前缀（默认开）'),
          ]),
          h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginBottom: 4 } }, '自定义模板（留空用默认；占位符 {number} {url} {title}；设置后整体替换默认文本）：'),
          h('textarea', { className: 'dsws-ta', style: { minHeight: 70 }, placeholder: '/wayfinder\n{url}\n\n请按 wayfinder 流程处理这个 ticket：…', value: custom, onChange: function (e) { setCustom(e.target.value) } }),
          h('div', { style: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 } }, [
            h('button', { className: 'dsws-btn', onClick: reset }, '恢复默认'),
            h('button', { className: 'dsws-btn', onClick: function () { s.cfgOpen = false; emit() } }, '取消'),
            h('button', { className: 'dsws-btn primary', onClick: save }, '保存'),
          ]),
        ]),
      ])
    }

    // ---- 6.11 turnTail 智能提醒条 ----
    const TurnTail = () => {
      const s = useStore()
      if (s.remindDismissed) return null
      const groups = compute()
      const target = groups.length && groups[0].frontier.length ? groups[0].frontier[0] : null
      return h('div', { className: 'dsws-remind' }, [
        h('span', null, '本轮讨论已涉及 wayfinder 工作，可' + WORD() + '到' + (target ? '「' + target.title + '」#' + target.number : '某张 ticket') + '：'),
        h('button', { className: 'dsws-btn', onClick: function () { if (target) { s.fixateFor = target; emit() } } }, WORD()),
        h('button', { className: 'dsws-btn ghost', onClick: function () { s.remindDismissed = true; emit() } }, '✕'),
      ])
    }

    // ---- 6.12 Run 卡控制面板（含外观方案切换）----
    const RunPanel = () => {
      const s = useStore()
      const setIcon = function (id) { s.ui.icon = id; emit() }
      const setWord = function (w) { s.ui.word = w; emit() }
      return h('div', { style: { border: '1px solid var(--dsw-alias-border-l1,#2a2d35)', borderRadius: 8, padding: '10px 12px', background: 'var(--dsw-alias-bg-layer-1,#10131a)', fontFamily: 'var(--dsw-font-family)', fontSize: 13, color: 'var(--dsw-alias-label-primary,#e6edf3)', lineHeight: 1.6 } }, [
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }, [
          h('strong', null, 'DSH-Waystation 原型'),
          h('span', { style: { color: '#4ade80', fontSize: 12 } }, '● 已加载（假数据）'),
        ]),
        h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', margin: '6px 0' } }, '就绪（wf.status · #344）+ 面板（wf.snapshot · #346）均已接真；剩余 UX 细节待 #348 拍板。'),
        h('div', { className: 'dsws-uirow' }, [
          h('span', { style: { fontSize: 12 } }, '图标：'),
          ICON_SCHEMES.map(function (ic) {
            return h('button', { key: ic.id, className: 'dsws-btn' + (s.ui.icon === ic.id ? ' on' : ''), onClick: function () { setIcon(ic.id) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [Icon({ scheme: ic.id, size: 13 }), h('span', null, ic.label)])
          }),
        ]),
        h('div', { className: 'dsws-uirow' }, [
          h('span', { style: { fontSize: 12 } }, '动作词：'),
          WORD_SCHEMES.map(function (w) {
            return h('button', { key: w, className: 'dsws-btn' + (s.ui.word === w ? ' on' : ''), onClick: function () { setWord(w) } }, w)
          }),
        ]),
        h('div', { className: 'dsws-uirow' }, [
          h('button', { className: 'dsws-btn', onClick: function () { s.open = true; emit() } }, '打开面板'),
          h('button', { className: 'dsws-btn', onClick: function () { s.cfgOpen = true; emit() } }, '开始模板'),
          h('button', { className: 'dsws-btn', onClick: function () { flash('面板已接 wf.snapshot 真数据（#346）') } }, '数据源：真数据'),
          h('a', { className: 'dsws-btn', href: 'https://github.com/FeatherHunter/SKILLS/issues/355', target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none' } }, 'Ticket #355'),
        ]),
      ])
    }

    // ============================================================
    // 7. 插槽注册
    // ============================================================
    slots.inject('sidebar.footer.action', function () {
      return slots.register({ name: 'sidebar.footer.action', id: 'dsh-waystation', label: 'Waystation', order: 5 }, SidebarButton)
    })
    slots.inject('shell.overlay', function () {
      return slots.register({ name: 'shell.overlay', id: 'dsws-overlay-v5', order: 10 }, OverlayPanel)
    })
    slots.inject('conversation.input.dock', function () {
      return slots.register({ name: 'conversation.input.dock', id: 'dsh-waystation', order: 40 }, StatusBar)
    })
    slots.inject('conversation.chat.turnTail', function () {
      return slots.register({ name: 'conversation.chat.turnTail', select: function () { return {} } }, TurnTail)
    })
    slots.inject('tool.view.cordis', function () {
      return slots.register({ name: 'tool.view.cordis', key: 'self' }, RunPanel)
    })

    // #347：加载真数据快照（repo 链接 + 前置检测兜底），失败静默
    loadSnapshot()
  },
}
