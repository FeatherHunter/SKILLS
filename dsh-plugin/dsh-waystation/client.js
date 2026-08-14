/**
 * DSH-Waystation · Client 半（UX v20 · 2026-08-14 第六批执行）
 *
 * v20 变更（用户拍板）：
 *   43. 标签「+N」可点击展开全部标签（含颜色），再点「收起」折叠；悬停 +N tooltip 显示全部标签名；
 *       store 新增 expTags（按 issue number 记录展开态）
 *
 * v19：grilling→讨论 / 头部 repo 名 / 环境段末尾 / map 详情执行+任务动作 / map 行进度 /
 * 交接时间戳+查最新+复制。
 * v18：可接/占用列表口径 / 按钮去开始（诊断/执行/修复）/ 点击预填输入框。
 * v17：isLight 改 YIQ 感知亮度。v16：按钮色 = label 配置色。
 * v15：状态栏防换行自适应 / map 置顶 / 被阻塞标签 / 会话 cwd 改 SessionSummary.cwd。
 * v14：全部执行批次（三选一动作 / map 行突出 / 已关闭折叠 / chips 深边框 / 窄屏折叠 /
 * 刷新遮罩 / 主题安全色 / 交接按钮 / 状态栏等宽 / 按会话 store）。
 * v13：cwd 权威反查（wf.cwd）+ sessionId 变化重探测。v12：repoKey 按 cwd 缓存 /
 * 失败不兜假数据 / 三视图收敛 / 沉淀=注入快照模板。
 * v11：label 颜色 = GitHub 配置色。v10：cwd 关联 / 标签视图 / 圆形技能环。
 * v9：DESIGN.md §12.2 Round 3 定稿 1A-7A 落实。
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
      '.dsws-panel{position:fixed;left:16px;top:76px;width:460px;max-height:calc(100vh - 24px);display:flex;flex-direction:column;background:var(--dsw-alias-bg-layer-2,#16181d);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.45);z-index:9999;font-family:var(--dsw-font-family);font-size:13px;color:var(--dsw-alias-label-primary,#e6edf3);line-height:1.6;overflow:hidden}',
      '.dsws-head{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--dsw-alias-border-l1,#2a2d35);cursor:move;user-select:none}',
      '.dsws-tabs{display:flex;gap:4px;padding:8px 12px 0}',
      '.dsws-tab{padding:4px 10px;border-radius:6px;cursor:pointer;border:1px solid transparent;background:transparent;color:var(--dsw-alias-label-secondary,#a1a1aa);font-size:12px}',
      '.dsws-tab.on{background:var(--dsw-alias-interactive-bg-active,rgba(255,255,255,.14));color:var(--dsw-alias-label-primary,#e6edf3);border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-body{flex:1;overflow-y:auto;padding:10px 12px}',
      '.dsws-rz{position:absolute;z-index:6}',
      '.dsws-rz-n{top:0;left:8px;right:8px;height:5px;cursor:ns-resize}',
      '.dsws-rz-s{bottom:0;left:8px;right:8px;height:5px;cursor:ns-resize}',
      '.dsws-rz-e{right:0;top:8px;bottom:8px;width:5px;cursor:ew-resize}',
      '.dsws-rz-w{left:0;top:8px;bottom:8px;width:5px;cursor:ew-resize}',
      '.dsws-rz-ne{top:0;right:0;width:10px;height:10px;cursor:nesw-resize}',
      '.dsws-rz-nw{top:0;left:0;width:10px;height:10px;cursor:nwse-resize}',
      '.dsws-rz-se{bottom:0;right:0;width:14px;height:14px;cursor:nwse-resize;background:linear-gradient(135deg,transparent 50%,var(--dsw-alias-label-caption,#8b8b95) 50%);opacity:.5;border-radius:0 0 12px 0}',
      '.dsws-rz-se:hover{opacity:1}',
      '.dsws-rz-sw{bottom:0;left:0;width:10px;height:10px;cursor:nesw-resize}',
      '.dsws-maprow{border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:8px;padding:9px 12px;margin-bottom:8px;cursor:pointer;background:var(--dsw-alias-bg-layer-1,#10131a)}',
      '.dsws-maprow:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a)}',
      '.dsws-mtitle{font-weight:600;font-size:13px}',
      '.dsws-prog{height:4px;border-radius:2px;background:var(--dsw-alias-bg-layer-3,#0c0e12);overflow:hidden;margin-top:4px}',
      '.dsws-prog>i{display:block;height:100%;background:var(--dsw-alias-state-success-primary,#4ade80);border-radius:2px}',
      '.dsws-chip{display:inline-flex;align-items:center;gap:3px;padding:1px 8px;border-radius:99px;font-size:11px;line-height:1.7;margin-right:4px;white-space:nowrap}',
      '.dsws-chip-r{background:rgba(88,166,255,.18);color:#58a6ff}',
      '.dsws-chip-p{background:rgba(247,120,186,.16);color:#f778ba}',
      '.dsws-chip-g{background:rgba(63,185,80,.16);color:#3fb950}',
      '.dsws-chip-t{background:rgba(240,136,62,.16);color:#f0883e}',
      '.dsws-chip-m{background:rgba(188,140,255,.16);color:#bc8cff}',
      '.dsws-trow{display:flex;align-items:flex-start;gap:8px;padding:7px 8px;border-radius:6px;border:1px solid transparent}',
      '.dsws-trow:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-trow .dsws-tt{flex:1;min-width:0}',
      '.dsws-tt-name{font-size:12.5px;word-break:break-all;display:flex;align-items:center;gap:5px}',
      '.dsws-tt-sub{font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-btn{padding:3px 10px;border-radius:6px;border:1px solid var(--dsw-alias-border-l1,#2a2d35);background:var(--dsw-alias-bg-layer-1,#10131a);color:var(--dsw-alias-label-primary,#e6edf3);font-size:12px;cursor:pointer}',
      '.dsws-btn:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a)}',
      // v14-5：主色按钮固定主题安全色（不再依赖 alias 变量，当前主题下会解析成深色导致黑底黑字）
      '.dsws-btn.primary{background:#c084fc;border-color:transparent;color:#140a1e;font-weight:600}',
      '.dsws-btn.primary:hover{border-color:rgba(20,10,30,.55)}',
      '.dsws-btn.ghost{background:transparent;border-color:transparent;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-grp{margin:12px 0 4px;font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa);display:flex;align-items:center;gap:6px}',
      '.dsws-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}',
      '.dsws-modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:10000}',
      '.dsws-modalbox{width:460px;max-width:94vw;background:var(--dsw-alias-bg-layer-2,#16181d);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;padding:14px 16px;font-family:var(--dsw-font-family);font-size:13px;color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-ta{width:100%;min-height:90px;background:var(--dsw-alias-bg-layer-1,#10131a);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:6px;color:var(--dsw-alias-label-primary,#e6edf3);font-family:var(--ds-font-family-code,monospace);font-size:12px;padding:8px;box-sizing:border-box}',
      '.dsws-note{position:absolute;right:14px;top:46px;padding:6px 12px;border-radius:6px;background:var(--dsw-alias-toast-bg,#22252c);border:1px solid var(--dsw-alias-border-l1,#2a2d35);color:var(--dsw-alias-label-primary,#e6edf3);font-size:12px;z-index:10001;box-shadow:0 4px 20px rgba(0,0,0,.4)}',
      '.dsws-skill{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px}',
      '.dsws-skill:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06))}',
      '.dsws-skill .dsws-tt{flex:1;min-width:0}',
      '.dsws-seg{cursor:pointer;padding:2px 7px;border-radius:99px;border:1px solid transparent;display:inline-flex;align-items:center;gap:4px}',
      '.dsws-seg:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-timebtn{cursor:pointer;padding:2px 7px;border-radius:99px;border:1px dashed transparent;color:var(--dsw-alias-label-caption,#8b8b95);white-space:nowrap;font-variant-numeric:tabular-nums;flex:none}',
      '.dsws-timebtn:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08));border-color:var(--dsw-alias-border-l1,#2a2d35);color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-uirow{display:flex;align-items:center;gap:6px;margin:4px 0;flex-wrap:wrap}',
      '.dsws-uirow .dsws-btn.on{border-color:var(--dsw-alias-state-success-primary,#4ade80);color:var(--dsw-alias-state-success-primary,#4ade80)}',
      // v14-22：数字区固定两位数等宽（98/99 5 字符；--/8 等宽；未来 9/10 不变宽）
      '.dsws-num{display:inline-block;min-width:5ch;text-align:center;font-variant-numeric:tabular-nums;font-family:var(--ds-font-family-code,Consolas,Menlo,monospace);font-size:11px;line-height:1.5;white-space:nowrap}',
      // v15-24：胶囊宽度适配内容（fit-content 不压缩不换行；上限放宽）
      '.dsws-capsule{max-width:min(92vw,640px);width:fit-content;margin:0 auto;display:flex;align-items:center;gap:2px;background:var(--dsw-alias-bg-layer-1,#10131a);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:999px;padding:3px 6px;font-size:12px;color:var(--dsw-alias-label-secondary,#a1a1aa);cursor:pointer;user-select:none;white-space:nowrap}',
      '.dsws-capsule .dsws-capsule-word{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:99px;font-weight:600;color:var(--dsw-alias-label-primary,#e6edf3);flex:none}',
      '.dsws-capsule .dsws-capsule-word:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08))}',
      '.dsws-capsule .dsws-seg{flex:none}',
      '.dsws-capsule .dsws-timebtn{flex:none}',
      '.dsws-banner{display:flex;align-items:center;gap:8px;border-radius:8px;padding:6px 10px;font-size:12px;margin:6px 0;cursor:pointer}',
      '.dsws-banner.bad{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.45);color:#f87171}',
      '.dsws-banner.warn{background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.45);color:#fbbf24}',
      '.dsws-banner.ok{background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.35);color:#4ade80}',
      '.dsws-aggrow{display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;border:1px solid transparent}',
      '.dsws-aggrow:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      '.dsws-ellip{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}',
      '.dsws-cgroup{margin:10px 0 2px;font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa);display:flex;align-items:center;gap:6px}',
      '.dsws-ccard{border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:8px;padding:8px 10px;margin-bottom:6px;background:var(--dsw-alias-bg-layer-1,#10131a)}',
      '.dsws-ccard .nm{font-size:12.5px;font-weight:600}',
      '.dsws-ccard .dt{font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-ccard .act{margin-top:5px;display:flex;gap:6px}',
      // v14-17：手动刷新全面板遮罩 + spinner
      '.dsws-shade{position:absolute;inset:0;background:rgba(8,10,14,.55);display:flex;align-items:center;justify-content:center;gap:8px;z-index:7;border-radius:12px}',
      '.dsws-spinner{width:16px;height:16px;border-radius:50%;border:2px solid rgba(255,255,255,.18);border-top-color:#c084fc;animation:dsws-spin .8s linear infinite;flex:none}',
      '@keyframes dsws-spin{to{transform:rotate(360deg)}}',
    ].join(''))

    // ============================================================
    // 1. 技能目录 + 场景推荐映射
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
      research: ['research', 'r', '研究'],
      prototype: ['prototype', 'p', '原型'],
      grilling: ['grilling', 'g', '对齐'],
      task: ['task', 't', '任务'],
    }
    const TYPE_ICON = { research: 'search', prototype: 'hammer', grilling: 'chat', task: 'gear' }

    // ============================================================
    // 2. 外观方案（图标 + 动作词，可切换）
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
      const common = { viewBox: '0 0 24 24', width: s, height: s, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', style: { display: 'inline-block', verticalAlign: '-2px', flex: 'none' } }
      if (scheme === 'beacon') return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 4, fill: 'currentColor', stroke: 'none' }), h('path', { d: 'M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1' })])
      if (scheme === 'radar') return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('circle', { cx: 12, cy: 12, r: 5 }), h('circle', { cx: 12, cy: 12, r: 1.2, fill: 'currentColor', stroke: 'none' }), h('path', { d: 'M12 12L19 8' }), h('circle', { cx: 16.5, cy: 6.5, r: 1.1, fill: 'currentColor', stroke: 'none' })])
      if (scheme === 'pin') return h('svg', common, [h('path', { d: 'M12 21s-6-5.1-6-10a6 6 0 1112 0c0 4.9-6 10-6 10z' }), h('circle', { cx: 12, cy: 11, r: 2.2, fill: 'currentColor', stroke: 'none' })])
      return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('polygon', { points: '15.5 8.5 13 13 8.5 15.5 11 11', fill: 'currentColor', stroke: 'none' })])
    }

    // ---- 通用图标集（统一 SVG stroke 风格）----
    const Ic = ({ n, size, color }) => {
      const s = size || 13
      const common = { viewBox: '0 0 24 24', width: s, height: s, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', style: { display: 'inline-block', verticalAlign: '-2px', flex: 'none' }, color: color || undefined }
      switch (n) {
        case 'dot': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 4.5, fill: 'currentColor', stroke: 'none' })])
        case 'target': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 8 }), h('circle', { cx: 12, cy: 12, r: 2.4, fill: 'currentColor', stroke: 'none' })])
        case 'lock': return h('svg', common, [h('rect', { x: 5, y: 11, width: 14, height: 9, rx: 2 }), h('path', { d: 'M8 11V8a4 4 0 018 0v3' })])
        case 'map': return h('svg', common, [h('path', { d: 'M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z' }), h('path', { d: 'M9 3v15M15 6v15' })])
        case 'compass': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('polygon', { points: '15.5 8.5 13 13 8.5 15.5 11 11', fill: 'currentColor', stroke: 'none' })])
        case 'gear': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 3 }), h('path', { d: 'M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1' })])
        case 'refresh': return h('svg', common, [h('path', { d: 'M21 12a9 9 0 11-2.6-6.4' }), h('polyline', { points: '21 3 21 9 15 9' })])
        case 'note': return h('svg', common, [h('rect', { x: 4, y: 4, width: 16, height: 16, rx: 2 }), h('path', { d: 'M8 9h8M8 13h8M8 17h5' })])
        case 'fog': return h('svg', common, [h('path', { d: 'M8 17a4 4 0 010-8 5 5 0 019.6-1.6A3.5 3.5 0 0118 17z' }), h('path', { d: 'M3 21h18' })])
        case 'ban': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('path', { d: 'M5.6 5.6l12.8 12.8' })])
        case 'person': return h('svg', common, [h('circle', { cx: 12, cy: 8, r: 3.5 }), h('path', { d: 'M5 20a7 7 0 0114 0' })])
        case 'check': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('path', { d: 'M8.5 12.5l2.5 2.5 4.5-5' })])
        case 'play': return h('svg', common, [h('path', { d: 'M8 5.5l11 6.5-11 6.5z', fill: 'currentColor', stroke: 'none' })])
        case 'link': return h('svg', common, [h('path', { d: 'M10 14a5 5 0 007.1 0l2.8-2.8a5 5 0 00-7.1-7.1L11 5.9' }), h('path', { d: 'M14 10a5 5 0 00-7.1 0l-2.8 2.8a5 5 0 007.1 7.1L13 18.1' })])
        case 'back': return h('svg', common, [h('path', { d: 'M19 12H5' }), h('polyline', { points: '12 19 5 12 12 5' })])
        case 'alert': return h('svg', common, [h('path', { d: 'M12 3l10 18H2z' }), h('path', { d: 'M12 9.5V14' }), h('circle', { cx: 12, cy: 17, r: 0.7, fill: 'currentColor', stroke: 'none' })])
        case 'x': return h('svg', common, [h('path', { d: 'M6 6l12 12M18 6L6 18' })])
        case 'star': return h('svg', common, [h('path', { d: 'M12 3l2.7 5.8 6.3.7-4.7 4.3 1.3 6.2-5.6-3.2-5.6 3.2 1.3-6.2L3 9.5l6.3-.7z', fill: 'currentColor', stroke: 'none' })])
        case 'search': return h('svg', common, [h('circle', { cx: 11, cy: 11, r: 7 }), h('path', { d: 'M21 21l-4.3-4.3' })])
        case 'hammer': return h('svg', common, [h('path', { d: 'M14 4l6 6-2.5 2.5-6-6z' }), h('path', { d: 'M3 21l7.5-7.5' }), h('path', { d: 'M12.5 9.5l2 2' })])
        case 'chat': return h('svg', common, [h('path', { d: 'M21 15a2 2 0 01-2 2H8l-5 4V5a2 2 0 012-2h14a2 2 0 012 2z' })])
        case 'clipboard': return h('svg', common, [h('rect', { x: 5, y: 4, width: 14, height: 16, rx: 2 }), h('path', { d: 'M9 2h6v4H9z' }), h('path', { d: 'M9 11h6M9 15h4' })])
        case 'list': return h('svg', common, [h('path', { d: 'M8 6h12M8 12h12M8 18h12' }), h('circle', { cx: 4, cy: 6, r: 0.8, fill: 'currentColor', stroke: 'none' }), h('circle', { cx: 4, cy: 12, r: 0.8, fill: 'currentColor', stroke: 'none' }), h('circle', { cx: 4, cy: 18, r: 0.8, fill: 'currentColor', stroke: 'none' })])
        case 'info': return h('svg', common, [h('circle', { cx: 12, cy: 12, r: 9 }), h('path', { d: 'M12 11v5' }), h('circle', { cx: 12, cy: 8, r: 0.7, fill: 'currentColor', stroke: 'none' })])
        case 'handoff': return h('svg', common, [h('path', { d: 'M7 17l-4-4 4-4' }), h('path', { d: 'M3 13h6a6 6 0 016 6' }), h('path', { d: 'M17 7l4 4-4 4' }), h('path', { d: 'M21 11h-6a6 6 0 00-6-6' })])
        default: return null
      }
    }

    // ============================================================
    // 3. store（v14：按会话隔离；无 sid 时用 shared）
    // ============================================================
    const makeStore = () => ({
      open: false, tab: 'list', activeMap: null,
      notice: null, injector: null, tick: 0,
      pos: null, size: { w: 460, h: null },
      ui: { icon: 'compass', word: '沉淀' },
      snapshot: null, cfgOpen: false,
      cwd: '', lblFilter: null, skillView: 'list',
      checks: null, checksUpdatedAt: '', checksMode: 'loading', checksError: null, checking: false,
      snapMode: 'loading', snapError: null, snapLoading: false,
      refreshing: false, handoffReady: false, expTags: {}, subs: [],
    })
    const shared = makeStore()
    const stores = {}
    const storeOf = (sid) => {
      if (!sid) return shared
      let st = stores[sid]
      if (!st) { st = makeStore(); stores[sid] = st }
      return st
    }
    const emit = (st) => { st.tick++; (st.subs || []).forEach(function (f) { f(st.tick) }) }
    const sub = (st, f) => { st.subs.push(f); return () => { const i = st.subs.indexOf(f); if (i >= 0) st.subs.splice(i, 1) } }
    const useStore = (sid) => {
      const st = storeOf(sid)
      const [, set] = React.useState(0)
      React.useEffect(() => sub(st, (n) => set(n)), [st])
      return st
    }
    const NOTICE_COLOR = { ok: '#4ade80', warn: '#fbbf24', info: '#a1a1aa' }
    const noticeIcon = (k) => k === 'ok' ? 'check' : k === 'warn' ? 'alert' : 'clipboard'
    const flash = (st, msg, kind) => {
      st.notice = { text: msg, kind: kind || 'info' }; emit(st)
      if (timer !== undefined) timer.timeout(function () { if (st.notice && st.notice.text === msg) { st.notice = null; emit(st) } }, 2800)
    }

    // 派生：票务分组（frontier/claimed/blocked/closed）
    const compute = (st) => {
      const maps = (st.snapshot && Array.isArray(st.snapshot.maps)) ? st.snapshot.maps : []
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
    const frontierAll = (st) => compute(st).reduce(function (n, g) { return n + g.frontier.length }, 0)

    // v18-30：状态栏可接/占用改用「列表 open issue」口径（与面板列表一致）：
    //   可接 = open issue 中未认领且未被 open 阻塞；占用 = 已认领 + 被阻塞；两者之和 = 全部 open issue
    const openIssuesOf = (st) => ((st.snapshot && Array.isArray(st.snapshot.issues)) ? st.snapshot.issues : []).filter(function (x) { return x.state !== 'CLOSED' })
    const isOccupied = function (st, x) {
      if (x.assignees && x.assignees.length) return true
      const maps = (st.snapshot && st.snapshot.maps) || []
      for (let mi = 0; mi < maps.length; mi++) {
        const m = maps[mi]
        if (!m.tickets || !m.tickets.length) continue
        const byNum = {}
        m.tickets.forEach(function (t) { byNum[t.number] = t })
        const t = byNum[x.number]
        if (t && t.blockedBy && t.blockedBy.length) {
          const openBlockers = t.blockedBy.filter(function (b) { const bt = byNum[b]; return bt && bt.state === 'OPEN' })
          if (openBlockers.length) return true
        }
      }
      return false
    }
    const occCount = (st) => openIssuesOf(st).filter(function (x) { return isOccupied(st, x) }).length
    const frontierCount = (st) => openIssuesOf(st).length - occCount(st)

    // v19：共享 —— 标签配置色映射（从快照 issues 收集 GitHub label 配置色，动态查询非写死）
    const buildColorOf = function (st) {
      const colorOf = {}
      const issues = (st.snapshot && Array.isArray(st.snapshot.issues)) ? st.snapshot.issues : []
      issues.forEach(function (x) {
        (x.labels || []).forEach(function (l) { if (l.color && !colorOf[l.name]) colorOf[l.name] = l.color })
      })
      return colorOf
    }
    // v19：共享 —— 行级动作（列表与 map 详情共用）：按 label 四选一（诊断/修复/讨论/执行），预填输入框；
    // 按钮主体色 = 对应 label 的 GitHub 配置色（YIQ 感知亮度定文字色）
    const mkRowAction = function (st, x, narrow, colorOf) {
      const url = 'https://github.com/' + repoStr(st) + '/issues/' + x.number
      const has = function (nm) { return (x.labels || []).some(function (l) { return (typeof l === 'string') ? l === nm : l.name === nm }) }
      const isLight = function (hex) {
        try {
          const hh = String(hex || '').replace('#', '')
          if (!/^[0-9a-fA-F]{6}$/.test(hh)) return false
          const r = parseInt(hh.slice(0, 2), 16), g = parseInt(hh.slice(2, 4), 16), b = parseInt(hh.slice(4, 6), 16)
          return (299 * r + 587 * g + 114 * b) / 1000 > 160
        } catch (e) { return false }
      }
      const btnColor = function (nm, fb) { const c = colorOf[nm]; return c ? '#' + c : fb }
      const mk = (icon, label, text, colorHex) => {
        const light = isLight(colorHex)
        return h('button', {
          className: 'dsws-btn primary',
          onClick: function (e) { e.stopPropagation(); inject(st, text) },
          style: { display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 6px', fontSize: 11, flex: 'none', background: colorHex, borderColor: 'transparent', color: light ? '#140a1e' : '#ffffff' },
          title: label,
        }, [Ic({ n: icon, size: 10 }), narrow ? null : h('span', null, label)])
      }
      if (has('needs-triage')) return mk('chat', '诊断', '/triage\n' + url + '\n\n请按 triage 流程为这个 issue 分流：categorise → verify → grill → 写 agent-ready brief。', btnColor('needs-triage', '#f59e0b'))
      if (has('bug')) return mk('hammer', '修复', '/wayfinder\n' + url + '\n\n请按 wayfinder 流程开始修复这个 bug：对齐所属 map 的 Destination，认领后处理。', btnColor('bug', '#f87171'))
      if (has('wayfinder:grilling')) return mk('chat', '讨论', '/wayfinder\n' + url + '\n\n请按 wayfinder 流程处理这个 grilling 票：加载所属 map 对齐 Destination，按 grilling 流程穷追不舍地对齐设计问题；完成后以 resolution comment 收尾。', btnColor('wayfinder:grilling', '#d93f0b'))
      return mk('play', '执行', startText(st, x), '#c084fc')
    }
    // v19：交接文档时间戳文件名（YYYYMMDD-HHMMSS）
    const timeStampStr = () => {
      try {
        const d = new Date()
        const p = function (n) { return String(n).padStart(2, '0') }
        return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds())
      } catch (e) { return 'latest' }
    }

    // ---- 环境检查（#344 · host.call('wf.status')；host 侧 30s 缓存 / force 重查）----
    // v12：失败不再兜假数据 —— 非 real 状态一律视为未知（--/8），不展示假绿点
    const CHECKS_TOTAL = 8
    const loadChecks = (st, force) => {
      if (st.checking) return Promise.resolve()
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        st.checksMode = 'err'
        st.checksError = 'host.call 不可用（Host 半未加载）'
        emit(st)
        return Promise.resolve()
      }
      st.checking = true
      if (force) st.checksMode = 'loading'
      emit(st)
      const args = Object.assign({}, st.cwd ? { cwd: st.cwd } : {}, force ? { force: true } : {})
      return host.call('wf.status', args).then(function (res) {
        st.checking = false
        if (res && res.checks && res.checks.length) {
          st.checks = res.checks
          st.checksUpdatedAt = nowStr()
          st.checksMode = 'real'
          st.checksError = null
        } else {
          st.checksMode = 'err'
          st.checksError = (res && res.error) ? String(res.error).slice(0, 160) : 'wf.status 返回空结果'
        }
        emit(st)
      }).catch(function (e) {
        st.checking = false
        st.checksMode = 'err'
        st.checksError = String((e && e.message) || e).slice(0, 160)
        emit(st)
      })
    }
    const activeChecks = (st) => (st.checksMode === 'real' && st.checks && st.checks.length) ? st.checks : []
    const readyCount = (st) => { const cs = activeChecks(st); return cs.length ? cs.filter(function (c) { return c.level === 'ok' }).length : -1 }
    // v14-22：返回纯数字串（'6/8' / '--/8'），由状态栏 num() 固定宽度渲染
    const envLabel = (st) => { const n = readyCount(st); return n < 0 ? '--/8' : n + '/8' }
    const setupCheck = (st) => (st.checks || []).find(function (c) { return c.id === 2 })

    const blockerNames = (t, m) => t.blockedBy.map(function (b) {
      const bt = m.tickets.find(function (x) { return x.number === b })
      return bt ? bt.title : ('#' + b)
    }).join('；')

    // v10：从会话快照探测当前工作目录（ConversationSnapshot 字段名多探几个）
    const detectCwd = function (ss) {
      try {
        if (ss && typeof ss === 'object') {
          for (const k of ['cwd', 'workspacePath', 'projectPath', 'path', 'dir', 'root']) {
            if (typeof ss[k] === 'string' && ss[k]) return ss[k]
          }
        }
      } catch (e) { /* 探测失败走 host 默认 */ }
      return ''
    }
    // v11：label 用 GitHub 配置色渲染 —— hex → rgba（.18 背景），无效 hex 返回 null 走兜底
    const hexA = function (hex, a) {
      try {
        const hh = String(hex || '').replace('#', '')
        if (!/^[0-9a-fA-F]{6}$/.test(hh)) return null
        const r = parseInt(hh.slice(0, 2), 16), g = parseInt(hh.slice(2, 4), 16), b = parseInt(hh.slice(4, 6), 16)
        return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')'
      } catch (e) { return null }
    }
    // v14-18：hex → HSL 亮度下调 amt（0-1）→ hex（chips 边框比 label 色深一档）
    const darken = function (hex, amt) {
      try {
        const hh = String(hex || '').replace('#', '')
        if (!/^[0-9a-fA-F]{6}$/.test(hh)) return null
        const r = parseInt(hh.slice(0, 2), 16) / 255, g = parseInt(hh.slice(2, 4), 16) / 255, b = parseInt(hh.slice(4, 6), 16) / 255
        const mx = Math.max(r, g, b), mn = Math.min(r, g, b)
        const l = (mx + mn) / 2
        let hue = 0, sat = 0
        if (mx !== mn) {
          const d = mx - mn
          sat = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn)
          if (mx === r) hue = ((g - b) / d + (g < b ? 6 : 0))
          else if (mx === g) hue = ((b - r) / d + 2)
          else hue = ((r - g) / d + 4)
          hue *= 60
        }
        const l2 = Math.max(0, l - amt)
        const hue2rgb = function (p, q, t) { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < 1 / 2) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p }
        const q2 = l2 < 0.5 ? l2 * (1 + sat) : l2 + sat - l2 * sat
        const p2 = 2 * l2 - q2
        const rr = Math.round(hue2rgb(p2, q2, hue / 360 + 1 / 3) * 255)
        const gg = Math.round(hue2rgb(p2, q2, hue / 360) * 255)
        const bb = Math.round(hue2rgb(p2, q2, hue / 360 - 1 / 3) * 255)
        return '#' + ((1 << 24) + (rr << 16) + (gg << 8) + bb).toString(16).slice(1)
      } catch (e) { return null }
    }

    // ============================================================
    // 4. 文本生成 + 复制/注入
    // ============================================================
    const nowStr = () => {
      try { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0') } catch (e) { return '' }
    }
    // 定稿 1A：时间固定格式 MM-DD HH:MM（本地）
    const timeOf = (snap) => {
      if (!snap) return ''
      try {
        const ms = (typeof snap.generatedMs === 'number' && snap.generatedMs) || Date.parse(snap.updatedAt || '')
        if (!ms) return ''
        const d = new Date(ms)
        return String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
      } catch (e) { return '' }
    }
    // 开始模板配置（#347 · localStorage 持久化）
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

    // 快照（#346：面板数据源；force 走 wf.refresh 全量重建；wf.snapshot 侧 5s 缓存）
    const loadSnapshot = function (st, force) {
      if (st.snapLoading) return Promise.resolve()
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        st.snapMode = 'err'
        st.snapError = 'host.call 不可用（Host 半未加载）'
        emit(st)
        return Promise.resolve()
      }
      st.snapLoading = true
      if (force) st.snapMode = 'loading'
      emit(st)
      const args = st.cwd ? { cwd: st.cwd } : {}
      const p = force ? host.call('wf.refresh', args) : host.call('wf.snapshot', args)
      return p.then(function (snap) {
        st.snapLoading = false
        if (snap && snap.ok === true && Array.isArray(snap.maps)) {
          st.snapshot = snap
          st.snapMode = 'real'
          st.snapError = null
        } else {
          st.snapMode = 'err'
          st.snapError = (snap && snap.error) ? String(snap.error).slice(0, 160) : 'wf.snapshot 返回异常'
          if (force) flash(st, '快照刷新失败：' + st.snapError, 'warn')
        }
        emit(st)
      }).catch(function (e) {
        st.snapLoading = false
        st.snapMode = 'err'
        st.snapError = String((e && e.message) || e).slice(0, 160)
        if (force) flash(st, '快照刷新失败：' + st.snapError, 'warn')
        emit(st)
      })
    }

    // v14-17：手动刷新（状态栏「更新」/ 列表「刷新」/ 检查页「重新检查」）→ 全面板遮罩 + 禁点
    const refreshAll = function (st) {
      if (st.refreshing) return
      st.refreshing = true; emit(st)
      Promise.all([loadChecks(st, true), loadSnapshot(st, true)]).then(function () {
        st.refreshing = false; emit(st)
      })
    }

    const repoStr = (st) => (st.snapshot && st.snapshot.repo)
      ? st.snapshot.repo.owner + '/' + st.snapshot.repo.name
      : 'FeatherHunter/SKILLS'

    // 开始 prompt：/wayfinder + URL + 流程指令（v12：点击「开始」直接复制，不再弹窗/开新会话）
    const startText = (st, t) => {
      const url = 'https://github.com/' + repoStr(st) + '/issues/' + t.number
      if (startCfg.custom) {
        return startCfg.custom
          .replace(/\{number\}/g, String(t.number))
          .replace(/\{url\}/g, url)
          .replace(/\{title\}/g, t.title)
      }
      const body = url +
        '\n\n**本 ticket 应在独立的新会话中执行**（wayfinder 语义：每张 ticket 一个会话，设计者要求彼此独立）。' +
        '保持当前工作目录；会话命名建议：' + newSessionTitle(t) +
        '\n\n请按 wayfinder 流程处理这个 ticket：先加载所属 map 的低分辨率视图对齐 Destination，认领该 ticket，再用 Notes 中指定的技能（如 /research）解析它；完成后以 resolution comment 收尾并关闭 issue。本 session 只解析这一个 ticket。'
      return (startCfg.withWayfinder ? '/wayfinder\n' : '') + body
    }
    const SESSION_TITLE_PREFIX = '[dsh-waystation]'
    const newSessionTitle = (t) => SESSION_TITLE_PREFIX + ' ' + t.title + ' #' + t.number

    // v10：沉淀 = 会话级动作 —— 注入「零丢失快照」prompt，用户回车即发给 AI
    const FIXATE_PROMPT = '里程碑固化点。暂停推进，执行「零丢失快照」，从第一性原理出发：\n' +
      '\n' +
      '1. 全量复述：把我从会话开始到现在说过的全部信息，按「目的地 / 约束与偏好 / 已确认的决定 / 待决问题 / 雾区（隐约可见但还不清晰）」五类，逐条列出——不压缩、不合并，宁可啰嗦不可省略。\n' +
      '2. 每条后面标注出处：用我的原话引用，让我知道它来自我哪句话。\n' +
      '3. 单独列一节「可疑遗漏」：凡是我提过、但你觉得与主线无关、太模糊或像执行细节而没纳入的，全部摆出来，写明你当初不纳入的理由，由我裁决。\n' +
      '4. 列完后停下等我逐条核对。我确认或修正完毕后，你再把清单落盘：已有地图就写进 map 正文和对应 ISSUE；还没建图就先生成一份快照笔记并告诉我存哪，等建图时搬入。'
    const injectFixate = (st) => { inject(st, FIXATE_PROMPT) }

    // v14-20 + v19-41：交接（M9 定向传递）—— 第一击只提示（不再注入模板，文档名带时间戳）；
    // 文案变「交接给新会话」；第二击 = host 查最新时间戳交接文档 → 预填 + 复制到剪贴板
    // + workspaces.startSession 新开空白会话（非 fork，避免复制旧上下文）
    const HANDOFF_READ = '/read .scratch/handoff/latest.md'
    let pendingDraft = null  // 跨会话预填（新会话 dock 挂载后消费）
    const doHandoff = function (st) {
      if (!st.handoffReady) {
        st.handoffReady = true
        flash(st, '交接：发送 /handoff 生成交接文档（建议命名 .scratch/handoff/' + timeStampStr() + '.md）；再点「交接给新会话」开新会话接手', 'ok')
        return
      }
      const ws = ctx.get('workspaces')
      const cwdArg = st.cwd ? { cwd: st.cwd } : {}
      const finish = function (readPath, msg) {
        pendingDraft = readPath
        copyText(st, readPath, msg || '已复制交接文档路径')
        if (ws && typeof ws.startSession === 'function') {
          ws.startSession()
        } else {
          pendingDraft = null
        }
      }
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        finish(HANDOFF_READ, '已复制交接文档路径（无法查询最新文档，兜底）')
        return
      }
      host.call('wf.handoffLatest', cwdArg).then(function (res) {
        const file = (res && res.ok && res.file) ? res.file : null
        if (file) finish('/read .scratch/handoff/' + file, '已复制交接文档路径：' + file)
        else finish(HANDOFF_READ, '未找到交接文档，已复制默认路径；可先发送 /handoff 生成')
      }).catch(function () {
        finish(HANDOFF_READ, '已复制交接文档路径（查询失败兜底）')
      })
    }

    const inject = (st, text) => {
      if (st.injector) { st.injector(text); flash(st, '已注入输入框，确认后发送', 'ok') }
      else copyText(st, text, '已复制到剪贴板（输入框不可用，兜底）')
    }
    const copyText = (st, text, okMsg) => {
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { flash(st, okMsg || '已复制', 'ok') }).catch(function () { flash(st, '复制失败，请手动复制', 'warn') })
      } else flash(st, '剪贴板不可用', 'warn')
    }

    // ============================================================
    // 5. 组件
    // ============================================================
    const Dot = ({ level }) => h('span', { className: 'dsws-dot', style: { background: level === 'ok' ? '#4ade80' : level === 'warn' ? '#f59e0b' : level === 'bad' ? '#f87171' : '#52525b' } })
    const TypeChip = ({ type }) => {
      const t = TYPE_LABEL[type] || [type, '', type]
      const cls = { research: 'dsws-chip-r', prototype: 'dsws-chip-p', grilling: 'dsws-chip-g', task: 'dsws-chip-t' }[type] || ''
      return h('span', { className: 'dsws-chip ' + cls }, [
        Ic({ n: TYPE_ICON[type] || 'dot', size: 11 }),
        h('span', null, t[2]),
      ])
    }

    // ---- 5.1 侧栏脚部入口（跟随当前激活会话）----
    const SidebarButton = (props) => {
      const cur = props.useSessions((x) => x.current)
      const s = useStore(cur)
      const n = readyCount(s)
      return h('button', {
        type: 'button',
        onClick: function (e) { e.stopPropagation(); s.open = true; emit(s) },
        style: { display: 'flex', alignItems: 'center', gap: 6, background: 'transparent', border: 'none', color: 'var(--dsw-alias-label-primary,#e6edf3)', fontSize: 12, cursor: 'pointer', padding: '4px 6px', borderRadius: 6 },
      }, [
        h('span', { style: { color: n < 0 ? '#f87171' : n === 8 ? '#4ade80' : '#f59e0b' } }, Icon({ scheme: s.ui.icon, size: 15 })),
        h('span', null, 'Waystation'),
        h('span', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 11 } }, (n < 0 ? '--/8' : n + '/8') + ' · ' + frontierCount(s) + ' 可接'),
      ])
    }

    // ---- 5.2 输入区状态栏（定稿 1A 居中胶囊 · 反馈不进状态栏 · cwd 关联 · v14 数字区等宽 + 交接段）----
    const StatusBar = (props) => {
      const sid = props && props.sessionId
      const s = useStore(sid)
      // v15-27：宿主权威 cwd —— SessionSummary.cwd（会话列表工作区标题同源），替换字段名猜测链
      const summaryCwd = props.useSessions(function (x) {
        return (sid && x.byId && x.byId[sid]) ? x.byId[sid].cwd : undefined
      })
      React.useEffect(function () {
        if (props && props.inputActions && typeof props.inputActions.setDraft === 'function') {
          s.injector = props.inputActions.setDraft
          // v14-20：跨会话预填（交接开新会话后，新 dock 挂载即消费）
          if (pendingDraft) { props.inputActions.setDraft(pendingDraft); pendingDraft = null }
        }
      }, [props])
      // v13：会话工作目录探测 —— 依赖 sessionId 变化重跑（切换对话必触发）。
      // v15-27：优先 SessionSummary.cwd（宿主权威）；次选 props.session 直取；最后 host wf.cwd 兜底。
      // cwd 变化后主动重拉快照与检查（否则面板/状态栏仍显示旧仓库数据）。
      React.useEffect(function () {
        const apply = function (cwd) {
          if (cwd && cwd !== s.cwd) { s.cwd = cwd; emit(s); loadChecks(s, false); loadSnapshot(s, false) }
        }
        if (summaryCwd) { apply(summaryCwd); return }
        const cwd0 = detectCwd(props && props.session)
        if (cwd0) { apply(cwd0); return }
        if (sid && typeof host !== 'undefined' && typeof host.call === 'function') {
          host.call('wf.cwd', { sessionId: sid }).then(function (res) {
            if (res && res.ok && res.cwd) apply(res.cwd)
          }).catch(function () { /* 保持现有 cwd */ })
        }
      }, [sid, summaryCwd])
      React.useEffect(function () { loadChecks(s, false); loadSnapshot(s, false) }, [])
      // v18-30：可接/占用 = 列表 open issue 口径（与面板列表一致）
      const fr = frontierCount(s)
      const blk = occCount(s)
      const n = readyCount(s)
      const timeStr = timeOf(s.snapshot) || (s.checksUpdatedAt ? s.checksUpdatedAt.slice(5, 16) : '') || '-- --:--'
      const setup = setupCheck(s)
      const amber = s.checksMode === 'real' && setup && setup.level !== 'ok'
      const go = function (tab) { s.tab = tab; s.open = true; emit(s) }
      // v14-22：数字区固定两位数等宽（环境 5ch 容 '98/99'；可接/占用 2ch）
      const num = (txt, minW) => h('span', { className: 'dsws-num', style: minW ? { minWidth: minW } : null }, txt)
      const seg = (icon, label, color, onGo, title) => h('span', { className: 'dsws-seg', onClick: function (e) { e.stopPropagation(); onGo() }, title: title || '', style: { display: 'inline-flex', alignItems: 'center', gap: 4, color: color } }, [
        Ic({ n: icon, size: 12 }),
        label,
      ])
      const capsule = h('div', { className: 'dsws-capsule', onClick: function () { s.open = true; emit(s) } }, [
        h('span', { className: 'dsws-capsule-word', onClick: function (e) { e.stopPropagation(); s.open = !s.open; emit(s) } }, [
          Icon({ scheme: s.ui.icon, size: 14 }),
          h('span', null, 'Waystation'),
        ]),
        seg('target', [h('span', null, '可接'), num(String(fr), '2ch')], '#4ade80', function () { go('list') }),
        seg('lock', [h('span', null, '占用'), num(String(blk), '2ch')], '#f0883e', function () { go('list') }),
        seg('note', s.ui.word, '#c084fc', function () { injectFixate(s) }, '沉淀：注入零丢失快照 prompt'),
        seg('handoff', s.handoffReady ? '交接给新会话' : '交接', '#58a6ff', function () { doHandoff(s) }, s.handoffReady ? '开新会话并预填交接文档路径' : '交接：发送 /handoff 生成交接文档'),
        // v19-36：环境段移至末尾（更新左侧），用户少点
        seg('dot', [h('span', null, '环境'), num(envLabel(s))], n < 0 ? '#f87171' : n === 8 ? '#4ade80' : '#f59e0b', function () { go('checks') }),
        h('span', { className: 'dsws-timebtn', onClick: function (e) { e.stopPropagation(); refreshAll(s) }, title: '重新检查 + 刷新快照' }, '更新 ' + timeStr),
      ])
      if (!amber) return h('div', { style: { display: 'flex', justifyContent: 'center', padding: '3px 8px 0' } }, [capsule])
      return h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '3px 8px 0' } }, [
        capsule,
        h('div', { className: 'dsws-banner warn', style: { margin: 0, maxWidth: 560, cursor: 'default' } }, [
          Ic({ n: 'alert', size: 13 }),
          h('span', null, 'setup 未执行'),
          h('button', { className: 'dsws-btn', style: { borderColor: 'rgba(245,158,11,.6)' }, onClick: function () { inject(s, '/setup-matt-pocock-skills\n（请选择 GitHub Issues 作为 issue tracker）') } }, '帮我执行 /setup-matt-pocock-skills'),
        ]),
      ])
    }

    // ---- 5.3 票务行（地图详情内：标题/阻塞来源 ellipsis；v19：按标签给 诊断/修复/讨论/执行 动作，预填输入框）----
    const TicketRow = ({ st, g, t, indent, colorOf }) => {
      const openBlocker = function (b) { const bt = g.m.tickets.find(function (x) { return x.number === b }); return bt && bt.state === 'OPEN' }
      const blocked = t.state === 'OPEN' && t.blockedBy.some(openBlocker)
      const subItem = (icon, color, text) => h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 3, color: color, minWidth: 0 } }, [
        Ic({ n: icon, size: 11 }),
        h('span', { className: 'dsws-ellip', style: { maxWidth: 200 }, title: text }, text),
      ])
      return h('div', { className: 'dsws-trow', style: indent ? { paddingLeft: 18 } : null }, [
        h('div', { className: 'dsws-tt' }, [
          h('div', { className: 'dsws-tt-name' }, [
            TypeChip({ type: t.type }),
            h('span', { className: 'dsws-ellip', style: { flex: 1 }, title: t.title }, t.title),
            h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)', fontSize: 11, flex: 'none' } }, '#' + t.number),
          ]),
          h('div', { className: 'dsws-tt-sub', style: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' } }, [
            t.claimedBy ? subItem('person', '#58a6ff', '已认领 ' + t.claimedBy) : null,
            t.blockedBy.length ? subItem('lock', '#f0883e', '被阻塞：' + blockerNames(t, g.m)) : null,
            t.state === 'CLOSED' ? subItem('check', '#3fb950', '已关闭') : null,
          ]),
        ]),
        t.state === 'OPEN' ? h('div', { style: { display: 'flex', gap: 4, alignItems: 'center', flex: 'none' } }, [
          blocked ? null : mkRowAction(st, t, false, colorOf),
          h('a', { className: 'dsws-btn ghost', href: 'https://github.com/' + repoStr(st) + '/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '3px 6px' } }, Ic({ n: 'link', size: 12 })),
        ]) : h('a', { className: 'dsws-btn ghost', href: 'https://github.com/' + repoStr(st) + '/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none' } }, '查看'),
      ])
    }

    // ---- 5.4 地图详情（定稿 3A 垂直走廊：可接/已认领/被阻塞常显，已关闭折叠；阻塞缩进；v19 顶部执行 + 任务按状态动作）----
    const MapDetail = ({ st, g }) => {
      const m = g.m
      const colorOf = buildColorOf(st)
      return h('div', null, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 } }, [
          h('button', { className: 'dsws-btn', onClick: function () { st.activeMap = null; emit(st) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
            Ic({ n: 'back', size: 12 }),
            h('span', null, '返回列表'),
          ]),
          h('span', { className: 'dsws-chip dsws-chip-m' }, [Ic({ n: 'map', size: 11 }), h('span', null, 'wayfinder:map')]),
          h('span', { style: { flex: 1 } }),
          // v19-38：顶部「执行」= 整张 map 的执行入口（预填输入框）
          h('button', { className: 'dsws-btn primary', onClick: function () { inject(st, '/wayfinder\n' + m.url + '\n\n请按 wayfinder 流程执行这张 map：加载低分辨率视图对齐 Destination，按 Notes 指定技能推进；完成后以 resolution comment 收尾并关闭。') }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', fontSize: 11 } }, [
            Ic({ n: 'play', size: 10 }),
            h('span', null, '执行'),
          ]),
        ]),
        h('div', { className: 'dsws-mtitle dsws-ellip', title: m.title }, m.title),
        m.error ? h('div', { style: { color: '#f87171', fontSize: 11, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'alert', size: 11 }), h('span', null, String((m.error && m.error.error) || '加载失败').slice(0, 160))]) : null,
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#4ade80', margin: '2px 0 2px' } }, [Ic({ n: 'target', size: 12 }), h('span', { className: 'dsws-ellip', title: m.destination }, m.destination || '（未填写 Destination）')]),
        m.notes ? h('div', { style: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginBottom: 4 } }, [Ic({ n: 'note', size: 11 }), h('span', { className: 'dsws-ellip', title: m.notes }, m.notes)]) : null,
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Decisions so far（' + m.decisions.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.decisions.map(function (d, i) {
            return h('div', { key: i, className: 'dsws-ellip', title: d.title + ' ' + d.gist }, '· ' + d.title)
          })),
        ]),
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Not yet specified（战雾 ' + m.fog.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.fog.map(function (f, i) { return h('div', { key: i, className: 'dsws-ellip', title: f }, '· ' + f) })),
        ]),
        h('details', { style: { marginBottom: 8 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, 'Out of scope（' + m.outOfScope.length + '）'),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.outOfScope.map(function (o, i) { return h('div', { key: i, className: 'dsws-ellip', title: o }, '· ' + o) })),
        ]),
        g.frontier.length ? h('div', { className: 'dsws-grp' }, [Ic({ n: 'target', size: 12, color: '#4ade80' }), h('span', null, '可接 ' + g.frontier.length)]) : null,
        g.frontier.map(function (t) { return h(TicketRow, { key: t.number, st: st, g: g, t: t, colorOf: colorOf }) }),
        g.claimed.length ? h('div', { className: 'dsws-grp' }, [Ic({ n: 'person', size: 12, color: '#58a6ff' }), h('span', null, '已认领 ' + g.claimed.length)]) : null,
        g.claimed.map(function (t) { return h(TicketRow, { key: t.number, st: st, g: g, t: t, colorOf: colorOf }) }),
        g.blocked.length ? h('div', { className: 'dsws-grp' }, [Ic({ n: 'lock', size: 12, color: '#f0883e' }), h('span', null, '被阻塞 ' + g.blocked.length)]) : null,
        g.blocked.map(function (t) { return h(TicketRow, { key: t.number, st: st, g: g, t: t, indent: true, colorOf: colorOf }) }),
        h('details', { style: { marginTop: 8 } }, [
          h('summary', { className: 'dsws-grp', style: { margin: '6px 0 2px', cursor: 'pointer' } }, [Ic({ n: 'check', size: 12, color: '#52525b' }), h('span', null, '已关闭 ' + g.closed.length)]),
          h('div', null, g.closed.map(function (t) { return h(TicketRow, { key: t.number, st: st, g: g, t: t, colorOf: colorOf }) })),
        ]),
      ])
    }

    // ---- 5.5 主列表（v14：三选一动作 / map 行突出 + 开始执行 / 已关闭折叠行 / chips 深边框 / 窄屏双栏）----
    const ListTab = ({ st, narrow }) => {
      const issues = (st.snapshot && Array.isArray(st.snapshot.issues)) ? st.snapshot.issues : []
      const openIssues = issues.filter(function (x) { return x.state !== 'CLOSED' })
      const closedIssues = issues.filter(function (x) { return x.state === 'CLOSED' })
      // v15-25：open 列表 map 优先置顶（map 内部按 updatedAt 倒序），其余按 updatedAt 倒序；已关闭行保持纯时间序
      openIssues.sort(function (a, b) {
        const am = (a.labels || []).some(function (l) { return l.name === 'wayfinder:map' }) ? 0 : 1
        const bm = (b.labels || []).some(function (l) { return l.name === 'wayfinder:map' }) ? 0 : 1
        if (am !== bm) return am - bm
        return String(b.updatedAt).localeCompare(String(a.updatedAt))
      })
      const groups = compute(st)
      const occ = groups.reduce(function (n, g) { return n + g.blocked.length + g.claimed.length }, 0)
      const cs = activeChecks(st)
      const nBad = cs.filter(function (c) { return c.level === 'bad' }).length
      // 标签统计（open + closed 全量）与配色
      const stat = {}
      const colorOf = {}
      issues.forEach(function (x) {
        (x.labels || []).forEach(function (l) {
          stat[l.name] = (stat[l.name] || 0) + 1
          if (l.color && !colorOf[l.name]) colorOf[l.name] = l.color
        })
      })
      const tagNames = Object.keys(stat).sort(function (a, b) { return stat[b] - stat[a] })
      const filtered = st.lblFilter ? openIssues.filter(function (x) { return (x.labels || []).some(function (l) { return l.name === st.lblFilter }) }) : openIssues
      const has = function (x, nm) { return (x.labels || []).some(function (l) { return l.name === nm }) }
      const findMap = function (num) { return (st.snapshot && st.snapshot.maps || []).find(function (m) { return m.number === num }) }
      // v15-26：主列表关联 map 子票阻塞信息（open 阻塞者才算阻塞；数据来自快照 maps.tickets.blockedBy，无需额外请求）
      const blockOf = {}
      ;(st.snapshot && st.snapshot.maps || []).forEach(function (m) {
        const byNum = {}
        m.tickets.forEach(function (t) { byNum[t.number] = t })
        m.tickets.forEach(function (t) {
          if (!t.blockedBy || !t.blockedBy.length) return
          const openBlockers = t.blockedBy.filter(function (b) { const bt = byNum[b]; return bt && bt.state === 'OPEN' })
          if (openBlockers.length) blockOf[t.number] = { map: m.number, mapTitle: m.title, by: openBlockers }
        })
      })
      const openBlocked = function (blk) { st.activeMap = blk.map; emit(st) }
      // v14-18：chips 常显深一档边框（边框色 = label 色 HSL 亮度 -16%）
      const chip = (nm, withCount, on, isAll) => {
        const c = colorOf[nm]
        const borderColor = isAll ? 'rgba(255,255,255,.35)' : (darken(c, 0.16) || 'rgba(188,140,255,.6)')
        const selColor = isAll ? 'rgba(255,255,255,.65)' : (c ? '#' + c : '#bc8cff')
        return h('span', {
          key: nm,
          className: 'dsws-chip',
          // v14-1：「全部」恒清空过滤并保持选中，与普通标签 toggle 语义分离
          onClick: function (e) { e.stopPropagation(); st.lblFilter = isAll ? null : ((st.lblFilter === nm) ? null : nm); emit(st) },
          style: {
            cursor: 'pointer', marginRight: 4, marginBottom: 3, fontSize: 10,
            background: isAll ? 'rgba(255,255,255,.08)' : (hexA(c, 0.18) || 'rgba(188,140,255,.16)'),
            color: isAll ? 'var(--dsw-alias-label-secondary,#a1a1aa)' : (c ? '#' + c : '#bc8cff'),
            border: '1px solid ' + (on ? selColor : borderColor),
          },
        }, nm + (withCount ? ' · ' + stat[nm] : ''))
      }
      const copyUrl = function (x) { copyText(st, 'https://github.com/' + repoStr(st) + '/issues/' + x.number, '已复制链接 #' + x.number) }
      // v14-4：行级动作按 label 四选一（诊断/修复/讨论/执行），全部预填输入框；
      // v19：共享 mkRowAction（列表与 map 详情同逻辑，按钮色动态取 label 配置色）；v14-3 按钮 80%；v14-19 窄屏折叠为纯图标
      // v14-19：行 = 左列(flex:1 截断) + 右列按钮组(flex:none 不换行)
      const issueRow = function (x, isOpen, narrow) {
        const isMap = has(x, 'wayfinder:map')
        const mapObj = isMap ? findMap(x.number) : null
        // v15-26：被阻塞判定（open 阻塞者）→ 隐藏动作按钮 + 红色「被阻塞」标签（点击跳所属 map 详情）
        const blk = blockOf[x.number]
        const blocked = !!(blk && blk.by && blk.by.length)
        // v20-43：展开态（st.expTags[num]）→ 显示全部标签；默认只显示前 2 个，「+N」可点击展开
        const expanded = !!(st.expTags && st.expTags[x.number])
        const shown = expanded ? (x.labels || []) : (x.labels || []).slice(0, 2)
        const rest = expanded ? 0 : (x.labels || []).length - shown.length
        const allNames = (x.labels || []).map(function (l) { return l.name }).join('、')
        const toggleTags = function (e) { e.stopPropagation(); st.expTags[x.number] = !expanded; emit(st) }
        const rightCol = h('div', { style: { display: 'flex', gap: 3, alignItems: 'center', flex: 'none' } }, [
          isOpen && !blocked ? mkRowAction(st, x, narrow, colorOf) : null,
          h('button', { className: 'dsws-btn ghost', onClick: function (e) { e.stopPropagation(); copyUrl(x) }, title: '复制链接', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '3px 5px', flex: 'none' } }, Ic({ n: 'clipboard', size: 12 })),
          h('a', { className: 'dsws-btn ghost', href: 'https://github.com/' + repoStr(st) + '/issues/' + x.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '3px 5px', flex: 'none' } }, Ic({ n: 'link', size: 12 })),
        ])
        return h('div', {
          key: x.number,
          className: 'dsws-aggrow',
          onClick: function () { if (isMap && mapObj) { st.activeMap = x.number; emit(st) } },
          title: (isMap && mapObj) ? '查看地图详情' : undefined,
          // v14-2：地图行突出 —— 紫色竖条 + 浅紫底
          style: isMap ? { cursor: 'pointer', borderLeft: '3px solid #c084fc', background: 'rgba(188,140,255,.07)' } : undefined,
        }, [
          h('div', { style: { flex: 1, minWidth: 0 } }, [
            h('div', { style: { display: 'flex', alignItems: 'center', gap: 5 } }, [
              isMap ? h('span', { className: 'dsws-chip dsws-chip-m', style: { fontSize: 11, flex: 'none', fontWeight: 600 } }, [Ic({ n: 'map', size: 12 }), h('span', null, '地图')]) : null,
              h('span', { className: 'dsws-ellip', style: { flex: 1, fontWeight: isMap ? 600 : undefined }, title: x.title }, x.title),
              h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)', fontSize: 11, flex: 'none' } }, '#' + x.number),
            ]),
            (shown.length || blocked) ? h('div', { style: { marginTop: 3, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 } }, [
              shown.map(function (l, i) {
                return h('span', { key: i, className: 'dsws-chip', style: { fontSize: 10, marginRight: 0, background: hexA(l.color, 0.18) || 'rgba(188,140,255,.16)', color: l.color ? '#' + l.color : '#bc8cff', border: '1px solid ' + (darken(l.color, 0.16) || 'rgba(188,140,255,.6)') } }, l.name)
              }),
              rest > 0 ? h('span', { key: 'more', className: 'dsws-chip', onClick: toggleTags, title: '全部标签：' + allNames + '（点击展开）', style: { fontSize: 10, marginRight: 0, background: 'rgba(188,140,255,.1)', color: '#bc8cff', border: '1px dashed rgba(188,140,255,.55)', cursor: 'pointer' } }, '+' + rest) : null,
              expanded ? h('span', { key: 'less', className: 'dsws-chip', onClick: toggleTags, title: '收起标签', style: { fontSize: 10, marginRight: 0, background: 'rgba(255,255,255,.06)', color: 'var(--dsw-alias-label-caption,#8b8b95)', border: '1px dashed rgba(255,255,255,.3)', cursor: 'pointer' } }, '收起') : null,
              blocked ? h('span', { key: 'blk', className: 'dsws-chip', onClick: function (e) { e.stopPropagation(); openBlocked(blk) }, title: '被 ' + blk.by.map(function (b) { return '#' + b }).join('、') + ' 阻塞（点击查看地图详情）', style: { fontSize: 10, marginRight: 0, background: 'rgba(248,113,113,.16)', color: '#f87171', border: '1px solid rgba(248,113,113,.55)', cursor: 'pointer' } }, [Ic({ n: 'lock', size: 10 }), h('span', null, '被阻塞')]) : null,
            ]) : null,
            // v19-40：map 行进度（已完成/总数 + 进度条，如 13/14）
            (isMap && mapObj && mapObj.stats) ? h('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 } }, [
              h('div', { className: 'dsws-prog', style: { flex: 1 } }, [h('i', { style: { width: (mapObj.stats.total ? Math.round(mapObj.stats.closed / mapObj.stats.total * 100) : 0) + '%' } })]),
              h('span', { style: { fontSize: 10, color: 'var(--dsw-alias-label-caption,#8b8b95)', flex: 'none' } }, mapObj.stats.closed + '/' + mapObj.stats.total),
            ]) : null,
          ]),
          rightCol,
        ])
      }
      const kpi = (num, lab, icon, color) => h('div', { style: { display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, [Ic({ n: icon, size: 11, color: color }), h('span', null, String(num) + ' ' + lab)])
      return h('div', null, [
        // KPI 行 + 环境提示（v18-30：可接/占用 = 列表 open issue 口径）
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4, flexWrap: 'wrap' } }, [
          kpi(frontierCount(st), '可接', 'target', '#4ade80'),
          kpi(occCount(st), '占用', 'lock', '#f0883e'),
          kpi(closedIssues.length, '已关闭', 'check', '#52525b'),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', onClick: function () { refreshAll(st) }, style: { fontSize: 11, padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'refresh', size: 11 }), h('span', null, '刷新')]),
        ]),
        nBad > 0 ? h('div', { className: 'dsws-banner bad', onClick: function () { st.tab = 'checks'; emit(st) } }, [
          Ic({ n: 'alert', size: 13 }),
          h('span', null, nBad + ' 项环境未就绪，点此查看'),
        ]) : null,
        // 标签过滤 chips（动态统计 · GitHub 配置色 · v14-18 深边框）
        h('div', { style: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0, marginBottom: 6 } }, [
          chip('全部', false, st.lblFilter === null, true),
          tagNames.slice(0, 9).map(function (nm) { return chip(nm, true, st.lblFilter === nm, false) }),
        ]),
        st.snapMode === 'loading' ? h('div', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 12, padding: '14px 0', textAlign: 'center' } }, '加载中…') : null,
        st.snapMode === 'err' ? h('div', { style: { color: '#f87171', fontSize: 12, padding: '14px 0', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 } }, [Ic({ n: 'alert', size: 12 }), h('span', null, '快照加载失败：' + st.snapError)]) : null,
        filtered.length === 0 ? h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', padding: '14px 0', textAlign: 'center' } }, '暂无') : filtered.map(function (x) { return issueRow(x, true, narrow) }),
        // v14-4⑤：列表底部「已关闭 (N)」折叠行（默认收起，只占一行，展开可见）
        closedIssues.length ? h('details', { style: { marginTop: 8 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, padding: '4px 2px', userSelect: 'none' } }, [
            Ic({ n: 'check', size: 11 }),
            h('span', null, '已关闭 ' + closedIssues.length),
          ]),
          h('div', null, closedIssues.map(function (x) { return issueRow(x, false, narrow) })),
        ]) : null,
      ])
    }

    // ---- 5.6 技能雷达（定稿 4A 推荐+列表 · 4B 圆形技能环，A/B 切换）----
    const RingSkills = ({ st, rec, list }) => {
      const cx = 110, cy = 108, R2 = 88
      const center = rec[0] || 'ask-matt'
      const ring = list.filter(function (sk) { return sk.name !== center }).slice(0, 8)
      const nodes = ring.map(function (sk, i) {
        const a = (i / ring.length) * Math.PI * 2 - Math.PI / 2
        const x = cx + R2 * Math.cos(a), y = cy + R2 * Math.sin(a)
        const filled = sk.level === 'ok'
        return h('div', { key: sk.name, title: sk.use, onClick: function () { inject(st, '/' + sk.name) }, style: { position: 'absolute', left: x - 15, top: y - 15, width: 30, height: 30, borderRadius: '50%', border: filled ? '2px solid #4ade80' : '2px solid #52525b', background: filled ? 'rgba(74,222,128,.15)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9.5, cursor: 'pointer', color: filled ? '#4ade80' : '#8b8b95', lineHeight: 1.2, textAlign: 'center' } }, sk.name.length > 4 ? sk.name.slice(0, 4) + '…' : sk.name)
      })
      return h('div', null, [
        h('div', { style: { position: 'relative', width: 220, height: 220, margin: '0 auto 6px' } }, [
          h('div', { onClick: function () { inject(st, '/' + center) }, title: center, style: { position: 'absolute', left: cx - 30, top: cy - 30, width: 60, height: 60, borderRadius: '50%', background: 'rgba(188,140,255,.18)', border: '2px solid #c084fc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#c084fc', cursor: 'pointer', textAlign: 'center', lineHeight: 1.3 } }, '/' + center),
          nodes,
        ]),
        h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', textAlign: 'center', marginBottom: 8 } }, '中心 = 推荐 · 环绕 = 相关（实心已装/空心未装）· 点击注入 /skill'),
        h('div', { className: 'dsws-grp' }, [Ic({ n: 'compass', size: 12 }), h('span', null, '全部技能')]),
        list.map(function (sk) {
          const on = rec.indexOf(sk.name) >= 0
          return h('div', { key: sk.name, className: 'dsws-skill', style: on ? { background: 'rgba(188,140,255,.12)', borderRadius: 6 } : null }, [
            Dot({ level: sk.level }),
            h('div', { className: 'dsws-tt' }, [
              h('div', { className: 'dsws-tt-name', style: on ? { color: '#c084fc' } : null }, [h('span', null, '/' + sk.name), on ? Ic({ n: 'star', size: 11, color: '#c084fc' }) : null]),
              h('div', { className: 'dsws-tt-sub dsws-ellip', title: sk.use }, sk.use),
            ]),
            h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + sk.name) } }, '加载'),
          ])
        }),
      ])
    }

    const SkillsTab = ({ st }) => {
      const groups = compute(st)
      let rec = []
      let recTitle = '通用建议'
      if (st.activeMap !== null) {
        const g = groups.find(function (x) { return x.m.number === st.activeMap })
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
            h('div', { className: 'dsws-tt-name', style: on ? { color: '#c084fc' } : null }, [
              h('span', null, '/' + sk.name),
              on ? Ic({ n: 'star', size: 11, color: '#c084fc' }) : null,
            ]),
            h('div', { className: 'dsws-tt-sub dsws-ellip', title: sk.use }, sk.use),
          ]),
          h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + sk.name) } }, '加载'),
        ])
      })
      const head = h('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 } }, [
        h('div', { className: 'dsws-grp', style: { margin: 0 } }, [Ic({ n: 'compass', size: 12 }), h('span', null, recTitle)]),
        h('span', { style: { flex: 1 } }),
        h('span', { className: 'dsws-seg' + (st.skillView === 'list' ? ' on' : ''), onClick: function () { st.skillView = 'list'; emit(st) }, style: { fontSize: 11 } }, '列表'),
        h('span', { className: 'dsws-seg' + (st.skillView === 'ring' ? ' on' : ''), onClick: function () { st.skillView = 'ring'; emit(st) }, style: { fontSize: 11 } }, '圆环'),
      ])
      if (st.skillView === 'ring') return h('div', null, [head, h(RingSkills, { st: st, rec: rec, list: SKILLS })])
      return h('div', null, [
        head,
        h('div', { style: { marginBottom: 8 } }, rec.map(function (r, i) {
          return h('span', { key: i, className: 'dsws-chip dsws-chip-m' }, '/' + r)
        })),
        list,
      ])
    }

    // ---- 5.7 环境检查（定稿 5A：横幅 + 红/黄/绿分组卡；v12 失败不兜假数据）----
    const ChecksTab = ({ st }) => {
      React.useEffect(function () { loadChecks(st, false) }, [])
      const cs = activeChecks(st)
      const bad = cs.filter(function (c) { return c.level === 'bad' })
      const warn = cs.filter(function (c) { return c.level === 'warn' })
      const ok = cs.filter(function (c) { return c.level === 'ok' })
      const actBtn = (c) => {
        const hint = c.hint || ''
        const m = hint.match(/\/([a-z0-9-]+)/i)
        if (!m) return null
        return h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + m[1]) } }, '用 /' + m[1] + ' 处理')
      }
      const card = (c) => h('div', { key: c.id, className: 'dsws-ccard' }, [
        h('div', { className: 'nm' }, c.name),
        h('div', { className: 'dt dsws-ellip', title: c.detail }, c.detail),
        c.hint ? h('div', { className: 'act' }, [actBtn(c)]) : null,
      ])
      const grp = (title, color, items) => items.length ? h('div', null, [
        h('div', { className: 'dsws-cgroup' }, [h('span', { style: { width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' } }), h('span', null, title + ' ' + items.length)]),
        items.map(card),
      ]) : null
      return h('div', null, [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 } }, [
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'gear', size: 12 }), h('span', null, '环境检查 ' + envLabel(st))]),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', disabled: st.checking, onClick: function () { refreshAll(st) }, style: { fontSize: 11, padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
            Ic({ n: 'refresh', size: 11 }),
            h('span', null, st.checking ? '检查中…' : '重新检查'),
          ]),
        ]),
        st.checksMode === 'err' ? h('div', { className: 'dsws-banner bad', style: { cursor: 'default' } }, [Ic({ n: 'alert', size: 13 }), h('span', null, '环境检查失败：' + st.checksError)]) : null,
        st.checksMode === 'loading' ? h('div', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 12, marginBottom: 6 } }, '检测中…') : null,
        bad.length ? h('div', { className: 'dsws-banner bad', style: { cursor: 'default' } }, [Ic({ n: 'alert', size: 13 }), h('span', null, bad.length + ' 项缺失，先补齐再开始 wayfinder 工作')]) : null,
        grp('缺失', '#f87171', bad),
        grp('部分就绪', '#f59e0b', warn),
        grp('就绪', '#4ade80', ok),
      ])
    }

    // ---- 5.8 主面板（可拖动 · 8 向缩放 · 三视图 · v14 跟随当前会话 + 刷新遮罩）----
    const OverlayPanel = (props) => {
      const cur = props.useSessions((x) => x.current)
      const s = useStore(cur)
      const panelRef = React.useRef(null)
      React.useEffect(function () { if (s.open) loadSnapshot(s, false) }, [s.open])
      if (!s.open) return null
      const groups = compute(s)
      const active = s.activeMap !== null ? groups.find(function (x) { return x.m.number === s.activeMap }) : null
      // v14-19：窄屏阈值（面板宽 <380px 时动作按钮折叠为纯图标）
      const narrow = s.size.w < 380
      const tabBtn = (id, icon, label) => h('button', { className: 'dsws-tab' + (s.tab === id ? ' on' : ''), onClick: function () { s.tab = id; emit(s) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
        Ic({ n: icon, size: 12 }),
        h('span', null, label),
      ])

      const startDrag = function (e) {
        if (typeof document === 'undefined' || typeof window === 'undefined') return
        if (!panelRef.current) return
        e.preventDefault()
        const rect = panelRef.current.getBoundingClientRect()
        const r0 = { x: s.pos ? s.pos.x : rect.left, y: s.pos ? s.pos.y : rect.top, sx: e.clientX, sy: e.clientY }
        const mm = function (ev) { s.pos = { x: r0.x + ev.clientX - r0.sx, y: r0.y + ev.clientY - r0.sy }; emit(s) }
        const mu = function () { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu) }
        document.addEventListener('mousemove', mm)
        document.addEventListener('mouseup', mu)
      }
      const onBodyDown = function (e) {
        if (e.target === e.currentTarget) startDrag(e)
      }

      const onResizeDown = function (dir) {
        return function (e) {
          e.stopPropagation()
          e.preventDefault()
          if (typeof document === 'undefined' || typeof window === 'undefined' || !panelRef.current) return
          const rect = panelRef.current.getBoundingClientRect()
          const r0 = { x: s.pos ? s.pos.x : rect.left, y: s.pos ? s.pos.y : rect.top, w: s.size.w || rect.width, h: s.size.h || rect.height, sx: e.clientX, sy: e.clientY }
          const mm = function (ev) {
            const dx = ev.clientX - r0.sx, dy = ev.clientY - r0.sy
            let w = r0.w, h = r0.h
            if (dir.indexOf('e') >= 0) w = r0.w + dx
            if (dir.indexOf('s') >= 0) h = r0.h + dy
            if (dir.indexOf('w') >= 0) w = r0.w - dx
            if (dir.indexOf('n') >= 0) h = r0.h - dy
            w = Math.min(900, Math.max(340, w))
            h = Math.min(920, Math.max(240, h))
            let x = r0.x, y = r0.y
            if (dir.indexOf('w') >= 0) x = r0.x + (r0.w - w)
            if (dir.indexOf('n') >= 0) y = r0.y + (r0.h - h)
            s.pos = { x: x, y: y }
            s.size = { w: w, h: h }
            emit(s)
          }
          const mu = function () { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu) }
          document.addEventListener('mousemove', mm)
          document.addEventListener('mouseup', mu)
        }
      }

      const panelStyle = { width: s.size.w, ...(s.size.h ? { height: s.size.h } : {}), ...(s.pos ? { left: s.pos.x, top: s.pos.y, right: 'auto' } : { left: 16, top: 76, right: 'auto' }) }
      return h('div', { ref: panelRef, className: 'dsws-panel', style: panelStyle }, [
        h('div', { className: 'dsws-head', onMouseDown: startDrag }, [
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 } }, Icon({ scheme: s.ui.icon, size: 17 }), 'DSH-Waystation'),
          // v19-35：「真数据」→ 显示 repo 名（对未来用户更有意义；异常时红色提示）
          h('span', { className: 'dsws-chip ' + (s.snapMode === 'err' ? 'dsws-chip-t' : 'dsws-chip-m'), style: { maxWidth: 220 } }, [
            Ic({ n: s.snapMode === 'err' ? 'alert' : 'info', size: 11 }),
            h('span', { className: 'dsws-ellip', title: repoStr(s) }, s.snapMode === 'err' ? '快照异常' : s.snapMode === 'loading' ? '加载中…' : repoStr(s)),
          ]),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn ghost', onClick: function () { s.open = false; emit(s) }, style: { display: 'inline-flex', alignItems: 'center' } }, Ic({ n: 'x', size: 12 })),
        ]),
        h('div', { className: 'dsws-tabs' }, [tabBtn('list', 'list', '列表'), tabBtn('skills', 'compass', '技能'), tabBtn('checks', 'gear', '环境检查')]),
        h('div', { className: 'dsws-body', onMouseDown: onBodyDown }, [
          s.tab === 'list' ? (active ? h(MapDetail, { st: s, g: active }) : h(ListTab, { st: s, narrow: narrow })) : null,
          s.tab === 'skills' ? h(SkillsTab, { st: s }) : null,
          s.tab === 'checks' ? h(ChecksTab, { st: s }) : null,
        ]),
        h('div', { className: 'dsws-rz dsws-rz-n', onMouseDown: onResizeDown('n'), title: '向上拉大' }),
        h('div', { className: 'dsws-rz dsws-rz-s', onMouseDown: onResizeDown('s'), title: '向下拉大' }),
        h('div', { className: 'dsws-rz dsws-rz-e', onMouseDown: onResizeDown('e'), title: '向右拉大' }),
        h('div', { className: 'dsws-rz dsws-rz-w', onMouseDown: onResizeDown('w'), title: '向左拉大' }),
        h('div', { className: 'dsws-rz dsws-rz-ne', onMouseDown: onResizeDown('ne'), title: '右上角缩放' }),
        h('div', { className: 'dsws-rz dsws-rz-nw', onMouseDown: onResizeDown('nw'), title: '左上角缩放' }),
        h('div', { className: 'dsws-rz dsws-rz-se', onMouseDown: onResizeDown('se'), title: '右下角缩放' }),
        h('div', { className: 'dsws-rz dsws-rz-sw', onMouseDown: onResizeDown('sw'), title: '左下角缩放' }),
        // v14-17：手动刷新遮罩（期间禁点）
        s.refreshing ? h('div', { className: 'dsws-shade' }, [
          h('div', { className: 'dsws-spinner' }),
          h('span', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, '刷新中…'),
        ]) : null,
        s.notice ? h('div', { className: 'dsws-note', style: { display: 'flex', alignItems: 'center', gap: 6 } }, [
          Ic({ n: noticeIcon(s.notice.kind), size: 13, color: NOTICE_COLOR[s.notice.kind] || '#4ade80' }),
          h('span', null, s.notice.text),
        ]) : null,
        s.cfgOpen ? h(StartCfgModal, { st: s }) : null,
      ])
    }

    // ---- 5.9 开始模板配置 ----
    const StartCfgModal = ({ st }) => {
      const [wf, setWf] = React.useState(startCfg.withWayfinder)
      const [custom, setCustom] = React.useState(startCfg.custom)
      const save = function () { startCfg.withWayfinder = wf; startCfg.custom = custom; saveStartCfg(); st.cfgOpen = false; emit(st); flash(st, '开始模板已保存', 'ok') }
      const reset = function () { startCfg.withWayfinder = true; startCfg.custom = ''; saveStartCfg(); setWf(true); setCustom('') }
      return h('div', { className: 'dsws-modal', onClick: function () { st.cfgOpen = false; emit(st) } }, [
        h('div', { className: 'dsws-modalbox', onClick: function (e) { e.stopPropagation() } }, [
          h('div', { style: { fontWeight: 600, marginBottom: 8 } }, '开始模板配置'),
          h('label', { style: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginBottom: 8, cursor: 'pointer' } }, [
            h('input', { type: 'checkbox', checked: wf, onChange: function (e) { setWf(e.target.checked) } }),
            h('span', null, '复制文本带 /wayfinder 前缀（默认开）'),
          ]),
          h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginBottom: 4 } }, '自定义模板（留空用默认；占位符 {number} {url} {title}）：'),
          h('textarea', { className: 'dsws-ta', style: { minHeight: 70 }, placeholder: '/wayfinder\n{url}\n\n请按 wayfinder 流程处理这个 ticket：…', value: custom, onChange: function (e) { setCustom(e.target.value) } }),
          h('div', { style: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 } }, [
            h('button', { className: 'dsws-btn', onClick: reset }, '恢复默认'),
            h('button', { className: 'dsws-btn', onClick: function () { st.cfgOpen = false; emit(st) } }, '取消'),
            h('button', { className: 'dsws-btn primary', onClick: save }, '保存'),
          ]),
        ]),
      ])
    }

    // ---- 5.10 Run 卡控制面板（外观方案切换 · 跟随当前激活会话）----
    const RunPanel = (props) => {
      const cur = props.useSessions((x) => x.current)
      const s = useStore(cur)
      const setIcon = function (id) { s.ui.icon = id; emit(s) }
      const setWord = function (w) { s.ui.word = w; emit(s) }
      return h('div', { style: { border: '1px solid var(--dsw-alias-border-l1,#2a2d35)', borderRadius: 8, padding: '10px 12px', background: 'var(--dsw-alias-bg-layer-1,#10131a)', fontFamily: 'var(--dsw-font-family)', fontSize: 13, color: 'var(--dsw-alias-label-primary,#e6edf3)', lineHeight: 1.6 } }, [
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }, [
          h('strong', null, 'DSH-Waystation'),
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 4, color: '#4ade80', fontSize: 12 } }, [Ic({ n: 'dot', size: 10 }), h('span', null, '已加载')]),
        ]),
        h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', margin: '6px 0' } }, '环境检查（wf.status · #344）+ 面板（wf.snapshot · #346）均已接真。'),
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
          h('button', { className: 'dsws-btn', onClick: function () { s.open = true; emit(s) } }, '打开面板'),
          h('button', { className: 'dsws-btn', onClick: function () { s.cfgOpen = true; emit(s) } }, '开始模板'),
        ]),
      ])
    }

    // ============================================================
    // 6. 插槽注册
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
    slots.inject('tool.view.cordis', function () {
      return slots.register({ name: 'tool.view.cordis', key: 'self' }, RunPanel)
    })

    // #347：加载真数据快照（repo 链接 + 前置检测兜底），失败静默
    loadSnapshot(shared, false)
  },
}
