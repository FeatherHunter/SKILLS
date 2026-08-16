/**
 * DSH-Waystation · Client 半（UX v25 · 2026-08-14 T2a 配置页骨架）
 *
 * v26 变更（#373 用户拍板 2026-08-14）：
 *   打开形式收敛为「仅右侧 details 列」——移除 Document PiP 独立小窗（Electron 不可用、
 *   曾致桌面卡死）、停靠/悬浮双模式记忆（PANEL_MODE_KEY）、状态栏「停靠」seg、右栏「悬浮」按钮；
 *   状态栏胶囊允许换行（窄栏不再截断）。
 *
 * v25 变更（map #364）：
 *   T2a：配置页骨架（settings.plugins.tab「Waystation」+ 持久化 + 广播）；
 *   T2b：动作模板编辑器 + 占位符保护；
 *   T3（#366）：dsws locale 命名空间 zh/en 字典，全控件文字双语跟随 harness 语言（GitHub 数据不翻译）。
 *
 * v25 变更（map #364 · T2a）：
 *   50. 配置页骨架：settings.plugins.tab「Waystation」注册（设置 → 插件可见）；
 *       三组既有配置迁入（面板默认高度三档 / 开始模板 / 外观）；
 *       配置持久化 dsws.cfg + dsws.templates（旧 dsws.startCfg 自动迁移）；
 *       保存后广播同步所有会话 store（修复外观/尺寸不持久化隐性 bug）；
 *       面板内 StartCfgModal 移除，Run 卡保留「打开配置」引导按钮。
 *
 * v24 变更（用户反馈）：
 *   48. 交接第二击文件名修复：记忆第一击模板的时间戳，第二击读同一个文件
 *       （模板写什么名就读什么名；不再因目录无文档而兜底旧 latest.md；未点第一击才回退查最新）
 *   49. 面板默认高度 1/4 → 1/2（用户反馈 1/4 太小）
 *
 * v23：面板默认高度 = 屏幕约 1/4。
 * v22：引导句「从第一性原理出发完成任务，并对抗式审查。」；交接第一击恢复注入时间戳模板；
 * 第二击预填优化+复制。
 * v21：动作按钮 prompt 精简 + 统一引导句。
 * v20：标签「+N」点击展开全部标签/收起。
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
    // v1.3.3：面板版本号（tabs 行最右侧显示，便于核对已更新）
    const DSW_VERSION = 'v1.4.1'

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
      // v27（#396）：标题渲染策略。
      // 历史：word-break:break-all + 子 span 的 .dsws-ellip{white-space:nowrap} 导致长标题被静默省略号截断。
      // 现在：父 .dsws-tt-name 不再强制 break-all；标题 span 用 .dsws-tt-wrap（替换 .dsws-ellip），
      //   允许按空格/中文标点换行；hover 通过现有 title=... 兜底显示完整文本。
      '.dsws-tt-name{font-size:12.5px;display:flex;align-items:center;gap:5px}',
      '.dsws-tt-wrap{min-width:0;overflow-wrap:break-word;word-break:normal;line-break:auto;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}',
      '.dsws-tt-sub{font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-btn{padding:3px 10px;border-radius:6px;border:1px solid var(--dsw-alias-border-l1,#2a2d35);background:var(--dsw-alias-bg-layer-1,#10131a);color:var(--dsw-alias-label-primary,#e6edf3);font-size:12px;cursor:pointer}',
      '.dsws-btn:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a)}',
      // v14-5：主色按钮固定主题安全色（不再依赖 alias 变量，当前主题下会解析成深色导致黑底黑字）
      '.dsws-btn.primary{background:#c084fc;border-color:transparent;color:#140a1e;font-weight:600}',
      '.dsws-btn.primary:hover{border-color:rgba(20,10,30,.55)}',
      // v1.3.3：窄屏只剩图标时保持按钮高度、画成正方形（高=宽=按钮高），图标居中
      '.dsws-btn.narrow-icon{width:20px;height:20px;padding:0;justify-content:center;align-items:center;gap:0}',
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
      // #372 修复（2026-08-14 英文态溢出）：原上限 min(92vw,640px) 在英文长文案（如「Handoff · new session」）下触顶，
      //   内容从背景右缘溢出。放宽到 min(96vw,1400px)：width:fit-content + margin:0 auto → 胶囊始终
      //   以状态栏中心为轴向两边生长（背景完整包裹内容），不再截断/溢出。
      '.dsws-capsule{max-width:min(96vw,1400px);width:fit-content;margin:0 auto;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:2px 6px;background:var(--dsw-alias-bg-layer-1,#10131a);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:14px;padding:3px 6px;font-size:12px;color:var(--dsw-alias-label-secondary,#a1a1aa);cursor:pointer;user-select:none}',
      '.dsws-capsule .dsws-capsule-word{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:99px;font-weight:600;color:var(--dsw-alias-label-primary,#e6edf3);flex:none}',
      '.dsws-capsule .dsws-capsule-word:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08))}',
      '.dsws-capsule .dsws-seg{flex:none}',
      '.dsws-capsule .dsws-timebtn{flex:none}',
      '.dsws-banner{display:flex;align-items:center;gap:8px;border-radius:8px;padding:6px 10px;font-size:12px;margin:6px 0;cursor:pointer}',
      '.dsws-banner.bad{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.45);color:#f87171}',
      '.dsws-banner.warn{background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.45);color:#fbbf24}',
      '.dsws-banner.ok{background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.35);color:#4ade80}',
      // v1.3.3 UI 修复：aggrow 现含两行子块（行1 idcol+标题+圆环 / 行2 标签+按钮），必须纵向堆叠
      // v1.3.3：左侧预留空白减 20%（8px → 6.4px，map 行/普通行一致更紧凑）
      '.dsws-aggrow{display:flex;flex-direction:column;align-items:stretch;gap:6px;padding:6px 6.4px;border-radius:6px;border:1px solid transparent}',
      '.dsws-aggrow:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06));border-color:var(--dsw-alias-border-l1,#2a2d35)}',
      // v1.3.3 UI：辅助按钮（复制/外链）常显（用户要求一直显示，不 hover）
      '.dsws-aggrow .dsws-aux{display:inline-flex;align-items:center;gap:2px;flex:none}',
      // v1.3.3 UI：行2 标签贪心折叠（单行不换行，宽多窄少，+N 弹窗展开）
      '.dsws-tags{display:flex;align-items:center;gap:3px;flex:1 1 auto;min-width:0;overflow:hidden;white-space:nowrap}',
      '.dsws-tags .dsws-chip{flex:none}',
      // v1.3.3：+N 展开符号整体缩小 20%（padding 8→6px · font 11→9px · line-height 1.7→1.8）
      '.dsws-more{background:rgba(188,140,255,.1);color:#bc8cff;border:1px dashed rgba(188,140,255,.55);cursor:pointer;flex:none;transition:background .12s,border-color .12s;padding:0 6px;font-size:9px;line-height:1.8}',
      '.dsws-more:hover{background:rgba(188,140,255,.22);border-color:rgba(188,140,255,.8)}',
      // v1.3.3 UI：行1 编号 + map 徽章竖排（标题获得更宽展示区）
      '.dsws-idcol{display:flex;flex-direction:column;align-items:flex-start;gap:3px;flex:none}',
      // v1.3.3 UI：map 行迷你圆环进度（替代长条 + ✓）
      // v1.3.3 对齐修复：圆环与数字零间隙（gap 0 + 文本左对齐紧贴），
      //   文本固定最小宽度（5 字符容 26/27）→ 各行右缘对齐；
      //   v1.3.3 微调：min-width 38 → 35px（26/27 右侧空隙减半）
      '.dsws-ring{flex:none;display:inline-flex;align-items:center;gap:0}',
      '.dsws-ring svg{transform:rotate(-90deg)}',
      '.dsws-ring-txt{font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.5;flex:none;letter-spacing:.2px;min-width:35px;text-align:left}',
      // v1.3.3 UI：+N 弹窗（fixed 定位，自适应面板左右边界）
      '.dsws-pop{position:fixed;z-index:1000;background:#1c1f26;border:1px solid var(--dsw-alias-border-l2,#3a3f4a);border-radius:10px;box-shadow:0 10px 34px rgba(0,0,0,.55);padding:10px 12px;display:none}',
      '.dsws-pop .caret{position:absolute;width:10px;height:10px;background:#1c1f26;border-left:1px solid var(--dsw-alias-border-l2,#3a3f4a);border-top:1px solid var(--dsw-alias-border-l2,#3a3f4a);transform:rotate(45deg)}',
      '.dsws-pop .pt{font-size:10px;color:var(--dsw-alias-label-caption,#8b8b95);letter-spacing:1px;margin-bottom:6px;text-transform:uppercase}',
      '.dsws-pop .pl{display:flex;flex-wrap:wrap;gap:4px}',
      '.dsws-pop .ptitle{font-size:11px;color:var(--dsw-alias-label-secondary,#a1a1aa);margin-top:8px;border-top:1px solid var(--dsw-alias-border-l1,#2a2d35);padding-top:7px;line-height:1.55;overflow-wrap:break-word;word-break:break-word}',
      '.dsws-pop .ptitle b{color:var(--dsw-alias-label-primary,#e6edf3);font-weight:600}',
      // v1.4（T2 #443）：Map 详情页漏斗分层形态（D1-D8 规格）
      '.dsws-layers{display:flex;flex-direction:column;gap:4px;margin:10px 0;padding:8px 10px;border-radius:10px;background:linear-gradient(90deg,rgba(74,222,128,.05),rgba(255,255,255,.015));border:1px solid rgba(74,222,128,.2)}',
      '.dsws-layers .row1{display:flex;align-items:center;gap:8px}',
      '.dsws-layers .cap{font-size:9px;color:var(--dsw-alias-label-caption,#8b8b95);letter-spacing:.5px;text-transform:uppercase;flex:none}',
      '.dsws-layers .segs{flex:1;display:flex;gap:3px;height:12px}',
      '.dsws-layers .seg{flex:1;border-radius:3px;position:relative;background:rgba(255,255,255,.06);border:1px dashed rgba(255,255,255,.14)}',
      '.dsws-layers .seg.past{background:linear-gradient(180deg,rgba(74,222,128,.7),rgba(74,222,128,.4));border:none}',
      '.dsws-layers .seg.past::after{content:"✓";position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:7px;color:#04120a;font-weight:700}',
      '.dsws-layers .seg.curr{background:linear-gradient(180deg,#4ade80,#2dd45f);border:none;box-shadow:0 0 8px rgba(74,222,128,.5)}',
      '.dsws-layers .row2{display:flex;justify-content:space-between;font-size:8.5px;color:var(--dsw-alias-label-caption,#8b8b95);align-items:center}',
      '.dsws-layers .row2 .cur{color:#4ade80;font-weight:700;display:inline-flex;align-items:center;gap:4px}',
      '.dsws-start{display:flex;gap:8px;align-items:flex-start;margin:6px 0 2px}',
      '.dsws-start .cap{font-size:13px;font-weight:700;color:#fff;line-height:1.1}',
      '.dsws-start .desc{font-size:9px;color:var(--dsw-alias-label-caption,#8b8b95);font-style:italic;line-height:1.3}',
      '.dsws-layerTag{display:flex;align-items:center;gap:6px;font-size:9px;color:var(--dsw-alias-label-caption,#8b8b95);letter-spacing:.5px;margin:8px 0 4px;text-transform:uppercase}',
      '.dsws-layerTag .sp{flex:1;height:1px;background:linear-gradient(90deg,var(--dsw-alias-border-l1,#2a2d35),transparent)}',
      // v1.4 修复：并行票水平并列（符合原型 .A-layer 无 wrap 横排）—— 层内节点不换行，横向滚动看全部
      // v1.4 美化：滚动条深色细条（透明轨道 + 半透明滑块），贴合深色主题不再白条
      '.dsws-layer{display:flex;justify-content:flex-start;gap:8px;padding:2px 0 6px;overflow-x:auto;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.18) transparent}',
      '.dsws-layer::-webkit-scrollbar{height:5px}',
      '.dsws-layer::-webkit-scrollbar-track{background:transparent}',
      '.dsws-layer::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:3px}',
      '.dsws-layer::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.28)}',
      '.dsws-node{display:flex;flex-direction:column;gap:4px;border-radius:10px;padding:7px 8px;min-width:0;width:200px;flex:none;position:relative;background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.015));border:1.5px solid var(--dsw-alias-border-l1,#2a2d35);color:var(--dsw-alias-label-primary,#e6edf3)}',
      '.dsws-node.single{width:100%;flex:none}',
      // 窄框（面板 <380px）节点收窄，仍横排
      '.dsws-narrow .dsws-node{width:170px}',
      '.dsws-node .row1{display:flex;align-items:center;gap:6px}',
      '.dsws-node .icbox{width:22px;height:22px;flex:none;border-radius:7px;display:flex;align-items:center;justify-content:center;border:1.5px solid;background:rgba(0,0,0,.5);color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-node .meta{display:flex;align-items:center;gap:5px;margin-bottom:1px}',
      '.dsws-node .no{font-size:9px;color:var(--dsw-alias-label-caption,#8b8b95);font-family:var(--ds-font-family-code,Consolas,Menlo,monospace)}',
      '.dsws-node .tag{font-size:8px;padding:0 4px;border-radius:3px;border:1px solid;opacity:.85;font-family:var(--ds-font-family-code,Consolas,Menlo,monospace)}',
      '.dsws-node .tt{font-size:11px;font-weight:600;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;word-break:break-all}',
      '.dsws-node .acts{display:flex;gap:4px;flex-wrap:wrap;align-items:center}',
      '.dsws-node.done{opacity:.55}',
      '.dsws-node.now{border-color:rgba(74,222,128,.9);box-shadow:0 0 14px rgba(74,222,128,.3)}',
      '.dsws-node.wait{border-color:rgba(240,136,62,.5);border-style:dashed;opacity:.8}',
      '.dsws-node.fog{filter:blur(2.4px) brightness(.45);opacity:.6;cursor:pointer;border-color:rgba(192,132,252,.4)}',
      '.dsws-node.fog.revealed{filter:none;opacity:1;cursor:default}',
      '.dsws-node.fog .acts{pointer-events:none;filter:blur(1px)}',
      '.dsws-node.fog.revealed .acts{pointer-events:auto;filter:none}',
      '.dsws-node .qmark{position:absolute;right:7px;bottom:7px;width:12px;height:12px;color:rgba(192,132,252,.8);fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}',
      '.dsws-gate{height:26px;display:flex;align-items:center;justify-content:center;position:relative}',
      '.dsws-gate::before{content:"";position:absolute;top:0;bottom:0;left:50%;width:2px;background:linear-gradient(180deg,transparent,rgba(255,255,255,.15),transparent)}',
      '.dsws-gate .g{width:22px;height:22px;border-radius:50%;background:var(--dsw-alias-bg-layer-2,#16181d);border:2px solid;display:flex;align-items:center;justify-content:center;z-index:1;color:var(--dsw-alias-label-secondary,#a1a1aa)}',
      '.dsws-gate .g.lock{border-color:rgba(240,136,62,.55);color:#f0883e}',
      '.dsws-gate .g.open{border-color:rgba(74,222,128,.75);color:#4ade80;box-shadow:0 0 8px rgba(74,222,128,.3)}',
      '.dsws-dest{position:relative;margin-top:14px;border-radius:14px;padding:14px 12px 12px;text-align:center;background:linear-gradient(180deg,rgba(192,132,252,.1),rgba(88,166,255,.03) 70%,transparent);border:1.5px solid rgba(192,132,252,.35)}',
      '.dsws-dest .ring{width:72px;height:72px;margin:0 auto;position:relative}',
      // v1.4 修复：rotate(-90deg) 只作用于进度环 svg（直接子元素），不波及 core 旗帜（旗帜保持竖直）
      '.dsws-dest .ring > svg{transform:rotate(-90deg)}',
      '.dsws-dest .ring .track{stroke:rgba(255,255,255,.07);fill:none;stroke-width:6}',
      '.dsws-dest .ring .prog{fill:none;stroke-width:6;stroke-linecap:round;stroke:rgba(192,132,252,.7)}',
      '.dsws-dest .core{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}',
      '.dsws-dest .core svg{width:22px;height:22px;fill:none;stroke:#c084fc;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}',
      '.dsws-dest .title{font-size:15px;font-weight:700;margin-top:4px;color:#e6edf3}',
      '.dsws-dest .acts{display:flex;justify-content:center;gap:8px;margin-top:8px}',
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
      // v25 · T2b：配置页（settings.plugins.tab）专用样式
      '.dsws-cfg{max-width:720px;display:flex;flex-direction:column;gap:12px;padding:2px 2px 4px}',
      '.dsws-cfg-head{display:flex;align-items:center;gap:10px}',
      '.dsws-cfg-head .t{font-size:15px;font-weight:700;letter-spacing:.2px}',
      '.dsws-cfg-head .s{margin-left:auto;display:inline-flex;align-items:center;gap:5px;font-size:12px}',
      '.dsws-cfg-sub{font-size:12px;color:var(--dsw-alias-label-secondary,#a1a1aa);line-height:1.7}',
      '.dsws-cfg-group{border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;background:var(--dsw-alias-bg-layer-1,#10131a);padding:10px 14px}',
      '.dsws-cfg-gtitle{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:650;margin-bottom:4px}',
      '.dsws-cfg-gdesc{font-size:11.5px;color:var(--dsw-alias-label-caption,#8b8b95);margin-bottom:10px;line-height:1.65}',
      '.dsws-cfg-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:6px 0}',
      '.dsws-cfg-label{font-size:12px;color:var(--dsw-alias-label-secondary,#a1a1aa);flex:none}',
      '.dsws-cfg-seg{display:inline-flex;border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:8px;background:var(--dsw-alias-bg-layer-2,#16181d);padding:3px;gap:2px}',
      '.dsws-cfg-seg button{border:none;background:transparent;color:var(--dsw-alias-label-secondary,#a1a1aa);font-size:12px;padding:4px 14px;border-radius:6px;cursor:pointer;font-family:var(--dsw-font-family)}',
      '.dsws-cfg-seg button:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08))}',
      '.dsws-cfg-seg button.on{background:#c084fc;color:#140a1e;font-weight:600}',
      '.dsws-cfg-sw{display:inline-flex;align-items:center;gap:8px;cursor:pointer;user-select:none;font-size:12px}',
      '.dsws-cfg-sw input{display:none}',
      '.dsws-cfg-sw .tr{width:34px;height:19px;border-radius:99px;background:var(--dsw-alias-bg-layer-3,#0c0e12);border:1px solid var(--dsw-alias-border-l1,#2a2d35);position:relative;flex:none;transition:background .15s,border-color .15s}',
      '.dsws-cfg-sw .tr::after{content:"";position:absolute;left:2px;top:2px;width:13px;height:13px;border-radius:50%;background:var(--dsw-alias-label-caption,#8b8b95);transition:transform .15s,background .15s}',
      '.dsws-cfg-sw input:checked + .tr{background:rgba(192,132,252,.22);border-color:rgba(192,132,252,.55)}',
      '.dsws-cfg-sw input:checked + .tr::after{transform:translateX(15px);background:#c084fc}',
      '.dsws-cfg-ta{width:100%;min-height:56px;background:var(--dsw-alias-bg-layer-2,#16181d);border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:8px;color:var(--dsw-alias-label-primary,#e6edf3);font-family:var(--ds-font-family-code,Consolas,Menlo,monospace);font-size:11.5px;line-height:1.6;padding:7px 9px;box-sizing:border-box;resize:none;overflow:hidden}',
      '.dsws-cfg-ta:focus{outline:none;border-color:rgba(192,132,252,.6)}',
      '.dsws-cfg-chips{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:6px 0}',
      '.dsws-cfg-chip{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:99px;font-size:11px;font-family:var(--ds-font-family-code,Consolas,Menlo,monospace);cursor:pointer;background:rgba(188,140,255,.14);color:#bc8cff;border:1px solid rgba(188,140,255,.35);transition:background .12s}',
      '.dsws-cfg-chip:hover{background:rgba(188,140,255,.26)}',
      '.dsws-cfg-chip.req{background:rgba(248,113,113,.14);color:#f87171;border-color:rgba(248,113,113,.45)}',
      '.dsws-cfg-chip.req:hover{background:rgba(248,113,113,.26)}',
      '.dsws-cfg-chip .must{font-family:var(--dsw-font-family);font-size:10px;opacity:.85}',
      '.dsws-cfg-legend{font-size:11px;color:var(--dsw-alias-label-caption,#8b8b95);display:flex;align-items:center;gap:12px;margin-top:2px}',
      '.dsws-cfg-card{border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:12px;background:var(--dsw-alias-bg-layer-2,#16181d);padding:12px 14px;margin-bottom:10px}',
      '.dsws-cfg-card-head{display:flex;align-items:center;gap:8px;margin-bottom:2px}',
      '.dsws-cfg-card-name{font-size:13px;font-weight:650}',
      '.dsws-cfg-card-desc{font-size:11.5px;color:var(--dsw-alias-label-caption,#8b8b95);margin-bottom:4px;line-height:1.6}',
      '.dsws-cfg-preview{border:1px dashed var(--dsw-alias-border-l2,#3a3f4a);border-radius:8px;background:var(--dsw-alias-bg-layer-3,#0c0e12);padding:7px 10px;font-family:var(--ds-font-family-code,Consolas,Menlo,monospace);font-size:10.5px;line-height:1.6;color:var(--dsw-alias-label-secondary,#a1a1aa);white-space:pre-wrap;word-break:break-all;margin-top:5px}',
      '.dsws-cfg-preview .pv-label{display:block;font-family:var(--dsw-font-family);font-size:10px;letter-spacing:.5px;color:var(--dsw-alias-label-caption,#8b8b95);margin-bottom:3px}',
      '.dsws-cfg-err{border:1px solid rgba(248,113,113,.5);background:rgba(248,113,113,.1);border-radius:10px;padding:10px 12px;font-size:12px;color:#f87171;line-height:1.7}',
      '.dsws-cfg-err .t{font-weight:650;display:flex;align-items:center;gap:6px;margin-bottom:2px}',
      '.dsws-cfg-save{align-self:flex-end;background:#c084fc;color:#140a1e;border:none;border-radius:8px;font-size:13px;font-weight:650;padding:8px 28px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}',
      '.dsws-cfg-save:hover{filter:brightness(1.08)}',
      '.dsws-cfg-btn{background:transparent;border:1px solid var(--dsw-alias-border-l1,#2a2d35);border-radius:7px;color:var(--dsw-alias-label-secondary,#a1a1aa);font-size:11.5px;padding:3px 10px;cursor:pointer}',
      '.dsws-cfg-btn:hover{border-color:var(--dsw-alias-border-l2,#3a3f4a);color:var(--dsw-alias-label-primary,#e6edf3)}',
    ].join(''))

    // ============================================================
    // 0.5 locale（T3 #366 · dsws 命名空间 zh/en；跟随 harness 语言；GitHub 数据不翻译）
    // 契约：ctx.locale（dsh-client-locale）：register(ns, {zh, en}) + bind(ns) 稳定引用，调用时读当前语言；
    // 所有 outlet 在 locale 切换时自动重渲染（useLocaleRevision），模块级 t 即可生效。
    // 模板默认文本（GUIDE_LINE/FIXATE_PROMPT/TPL_DEFAULT）= 注入内容而非控件文案，不翻译（T3 决策）。
    // ============================================================
    const L = {
      zh: {
        'nav.word': '沉淀',
        'nav.takeable': '可接',
        'nav.occupied': '阻塞',
        'nav.env': '环境',
        'nav.envTitle': '环境检查 ({n}/8)',
        'nav.takeableTitle': '可接 = 未认领可执行的任务数',
        'nav.occupiedTitle': '阻塞 = 已认领未关闭的任务数',
        'nav.bug': 'BUG',
        'nav.bugTitle': '过滤：open + bug 标签',
        'nav.triage': '诊断',
        'nav.triageTitle': '过滤：open + needs-triage 标签',
        'nav.refresh': '更新',
        'nav.refreshTitle': '重新检查 + 刷新快照',
        'nav.fixateTitle': '保存进度快照 · 注入零丢失 prompt',
        'nav.handoff': '交接',
        'nav.handoffReady': '交接给新会话',
        'nav.handoffTitle': '交接：发送 /handoff 生成交接文档',
        'nav.handoffReadyTitle': '开新会话并预填交接文档路径',
        'banner.setup': 'setup 未执行',
        'banner.setupBtn': '帮我执行 /setup-matt-pocock-skills',
        'act.diagnose': '诊断',
        'act.fix': '修复',
        'act.discuss': '讨论',
        'act.execute': '执行',
        'act.view': '查看',
        'act.load': '加载',
        'act.done': '完成',
        'type.research': '研究',
        'type.prototype': '原型',
        'type.grilling': '对齐',
        'type.task': '任务',
        'list.back': '返回列表',
        'list.mapChip': '地图',
        'list.loadFail': '加载失败',
        'list.noDest': '（未填写 Destination）',
        'list.kpi.takeable': '可接',
        'list.kpi.occupied': '阻塞',
        'list.kpi.closed': '已关闭',
        'list.refresh': '刷新',
        'list.envWarn': '{n} 项环境未就绪，点此查看',
        'list.all': '全部',
        'list.loading': '加载中…',
        'list.errFull': '快照加载失败：{err}',
        'list.none': '暂无',
        'list.closedN': '已关闭 {n}',
        'list.collapse': '收起',
        'list.blocked': '被阻塞',
        'list.blockedTitle': '被 {by} 阻塞（点击查看地图详情）',
        'list.tagsTitle': '全部标签：{names}（点击展开）',
        'list.tagsCount': '全部标签 · {n} 个',
        'list.popTitle': '标题',
        'cfg.previewTitle': '示例 issue 标题',
        'list.tagsCollapseTitle': '收起标签',
        'list.copyLinkTitle': '复制链接',
        'list.openInGithubTitle': '在 GitHub 上查看 #{n}',
        'list.mapTitle': '查看地图详情',
        'list.state.all': '全部', 'list.state.open': 'Open', 'list.state.closed': '已关闭', 'list.state.blocked': '阻塞',
        'list.sort.updatedAt': '更新', 'list.sort.createdAt': '创建', 'list.sort.number': '编号', 'list.sort.title': '标题',
        'map.decisions': 'Decisions so far（{n}）',
        'map.fog': 'Not yet specified（战雾 {n}）',
        'map.outOfScope': 'Out of scope（{n}）',
        'map.grpTakeable': '可接 {n}',
        'map.grpClaimed': '已认领 {n}',
        'map.grpBlocked': '被阻塞 {n}',
        'map.grpClosed': '已关闭 {n}',
        'map.layer': '层 {n}',
        'map.progressCap': '地图进度',
        'map.curLayer': '当前：层 {n}',
        'map.layersPassed': '{n}/{t} 层已通过',
        'map.startCap': 'Start',
        'map.destCap': 'Destination',
        'map.startBtn': '开始 #{n}',
        'map.archive': '档案',
        'map.subClaimed': '已认领 {who}',
        'map.subBlocked': '被阻塞：{who}',
        'map.subClosed': '已关闭',
        'map.executeTitle': '执行 · 注入地图开始提示词',
        'map.doneTitle': '完成 · 注入收尾确认 prompt',
        'skill.centerRing': '中心 = 推荐 · 环绕 = 相关（实心已装/空心未装）· 点击注入 /skill',
        'skill.centerTitle': '推荐 {skill} · 注入 /{skill}',
        'skill.all': '全部技能',
        'skill.generic': '通用建议',
        'skill.notes': '「{m}」Notes 指定',
        'skill.treat': '用 /{s} 处理',
        'skill.list': '列表',
        'skill.ring': '圆环',
        'env.title': '环境检查 {n}/8',
        'env.recheck': '重新检查',
        'env.checking': '检查中…',
        'env.missing': '缺失',
        'env.partial': '部分就绪',
        'env.ready': '就绪',
        'env.failFull': '环境检查失败：{err}',
        'env.detecting': '检测中…',
        'env.missingBanner': '{n} 项缺失，先补齐再开始 wayfinder 工作',
        'env.openUrl': '打开网址',
        'env.copyUrl': '复制网址',
        'panel.snapErr': '快照异常',
        'panel.loading': '加载中…',
        'panel.tabList': '列表',
        'panel.tabSkills': '技能',
        'panel.tabChecks': '环境检查',
        'panel.refreshing': '刷新中…',
        'panel.closeTitle': '关闭面板',
        'rz.n': '拖上边 = 加高面板', 'rz.s': '拖下边 = 加高面板', 'rz.e': '拖右边 = 加宽面板', 'rz.w': '拖左边 = 加宽面板',
        'rz.ne': '右上角缩放', 'rz.nw': '左上角缩放', 'rz.se': '右下角缩放', 'rz.sw': '左下角缩放',
        'toast.injectedHandoff': '已注入 /handoff 交接模板（含时间戳文件名），确认后发送',
        'toast.copiedHandoff': '已复制交接文档指令',
        'toast.copiedHandoffFile': '已复制交接文档指令：{file}',
        'toast.copiedHandoffNoLatest': '已复制交接文档指令（无法查询最新文档，兜底）',
        'toast.handoffNotFound': '未找到交接文档，已复制默认路径；可先发送 /handoff 生成',
        'toast.copiedHandoffFail': '已复制交接文档指令（查询失败兜底）',
        'toast.injected': '已注入输入框，确认后发送',
        'toast.copiedFallback': '已复制到剪贴板（输入框不可用，兜底）',
        'toast.copied': '已复制',
        'toast.copyFailed': '复制失败，请手动复制',
        'toast.clipboardUnavailable': '剪贴板不可用',
        'toast.snapFail': '快照刷新失败：{err}',
        'toast.copiedLink': '已复制链接 #{n}',
        'toast.newSessionOpened': '已在新会话中打开并预填指令（同 cwd）',
        'toast.newSessionManual': '请手动新建会话并命名为「{title}」；指令已预填当前输入框',
        'toast.resetPanelWidthDone': '面板宽度已重置 · 下次打开生效',
        'toast.resetPanelWidthFail': 'layout 服务暂不支持重置 · 请更新 DSH harness',
        // #394：新会话按钮可见文字 + hover title（去掉冗余 detail，靠 #361 doc + 行为本身解释）
        'list.newSessionLabel': '新会话',
        'panel.newWayfinder': '新增 wayfinder',
        'panel.newWayfinderTitle': '注入 /wayfinder 新增需求 prompt（带当前仓库）',
        'panel.repoTitle': '当前仓库，点击打开 GitHub',
        'map.newSessionTitle': '在新会话打开（推进该 map）',
        'err.hostUnavailable': 'host.call 不可用（Host 半未加载）',
        'err.connUnavailable': 'connection 服务不可用（Host 半未加载）',
        'err.statusEmpty': 'wf.status 返回空结果',
        'err.snapshotEmpty': 'wf.snapshot 返回异常',
        'cfg.status': '配置',
        'cfg.saved': '已保存',
        'cfg.sub': '配置面板与动作提示词：静态文本可自由编辑，占位符由系统注入真值，点击即可插入。',
        'cfg.openIn': '打开位置',
        'cfg.openInDesc': '面板在哪个区域打开。better-sidebar 已安装时默认侧边栏；窗口缩小时侧边栏更稳。',
        'cfg.openInLabel': '打开位置',
        'cfg.openInDock': '停靠列',
        'cfg.openInSidebar': '侧边栏',
        'cfg.openInHint': '已即时生效：下次打开面板时按新位置打开',
        'cfg.panelWidth': '面板宽度',
        'cfg.resetPanelWidth': '重置面板宽度',
        'cfg.resetPanelWidthDesc': '下次打开面板时使用 layout 服务默认宽度（清掉上次的拖拽记忆）',
        'cfg.startTpl': '开始模板（执行动作）',
        'cfg.startTplDesc': '「执行」按钮注入的提示词；留空使用默认模板。',
        'cfg.withPrefix': '带 /wayfinder 前缀',
        'cfg.tplEditor': '动作模板编辑器',
        'cfg.tplEditorDesc': '「执行」外的六个动作按钮注入的提示词。点击下方占位符插入到光标处；红色「必填」占位符删除后无法保存。',
        'cfg.execHint': '「执行」模板在开始模板节编辑 →',
        'cfg.saveRejected': '保存被拒绝',
        'cfg.saveAll': '保存全部',
        'cfg.resetAll': '恢复全部默认',
        'cfg.reset': '恢复默认',
        'cfg.preview': '效果预览',
        'cfg.must': '必填',
        'cfg.chipReq': '必填占位符：删除后无法保存',
        'cfg.chipInsert': '点击插入到光标处',
        'tpl.missing': '缺少强制占位符 {list}',
        'tpl.unknown': '未知占位符 {list}',
        'tpl.name.diagnose': '诊断', 'tpl.name.fix': '修复', 'tpl.name.discuss': '讨论',
        'tpl.name.handoff1': '交接第一击', 'tpl.name.handoff2': '交接第二击', 'tpl.name.fixate': '沉淀',
        'tpl.desc.diagnose': 'needs-triage 票的行级动作',
        'tpl.desc.fix': 'bug 票的行级动作',
        'tpl.desc.discuss': 'wayfinder:grilling 票的行级动作',
        'tpl.desc.handoff1': '生成交接文档（含时间戳，两击文件名一致）',
        'tpl.desc.handoff2': '读取交接文档',
        'tpl.desc.fixate': '零丢失快照 prompt',
        'run.loaded': '已加载',
        'run.desc': '环境检查（wf.status）+ 面板（wf.snapshot）均已接真。',
        'run.openPanel': '打开面板',
        'run.openCfg': '打开配置',
        'run.cfgGuide': '配置页：设置 → 插件 → Waystation',
        'skilldesc.ask-matt': '技能路由器：不知道该用哪个 skill 时问它',
        'skilldesc.setup-matt-pocock-skills': '仓库初始化：issue tracker / 标签 / 文档路径',
        'skilldesc.wayfinder': '巨型项目决策地图（本插件服务的对象）',
        'skilldesc.triage': 'issue 状态机流转：categorise→verify→grill',
        'skilldesc.grilling': '穷追不舍的对齐提问（设计树）',
        'skilldesc.domain-modeling': '领域术语与统一语言',
        'skilldesc.research': '后台调研，写进 repo 内 markdown 并引源',
        'skilldesc.prototype': '一次性原型回答设计问题',
        'skilldesc.implement': '把规格落成代码（task 型 ticket）',
        'skilldesc.code-review': '按标准 + 规格双轴审查改动',
        'skilldesc.codebase-design': '深模块设计词汇',
        'skilldesc.diagnosing-bugs': '硬 bug 与性能回归诊断循环',
        'skilldesc.improve-codebase-architecture': '扫 deepening opportunities 出 HTML 报告',
        'skilldesc.tdd': '红-绿-重构',
        'skilldesc.handoff': '把当前对话压缩成交接文档',
        'skilldesc.teach': '跨 session 教你新技能',
        'skilldesc.to-spec': '把讨论固化成规格',
        'skilldesc.to-tickets': '把规格拆成 tickets',
        'skilldesc.resolving-merge-conflicts': '解决合并冲突',
        'skilldesc.writing-great-skills': '写出优秀技能',
      },
      en: {
        'nav.word': 'Consolidate',
        'nav.takeable': 'Ready',
        'nav.occupied': 'Busy',
        'nav.env': 'Env',
        'nav.envTitle': 'Environment checks ({n}/8)',
        'nav.takeableTitle': 'Ready = unclaimed, takeable tasks',
        'nav.occupiedTitle': 'Busy = claimed but not yet closed',
        'nav.bug': 'BUG',
        'nav.bugTitle': 'Filter: open + bug label',
        'nav.triage': 'Triage',
        'nav.triageTitle': 'Filter: open + needs-triage label',
        'nav.refresh': 'Refresh',
        'nav.refreshTitle': 'Re-check + refresh snapshot',
        'nav.fixateTitle': 'Save a snapshot · inject the zero-loss prompt',
        'nav.handoff': 'Handoff',
        'nav.handoffReady': 'Handoff · new session',
        'nav.handoffTitle': 'Handoff: send /handoff to generate the handoff doc',
        'nav.handoffReadyTitle': 'Open a new session with the handoff doc path prefilled',
        'banner.setup': 'setup not run yet',
        'banner.setupBtn': 'Run /setup-matt-pocock-skills for me',
        'act.diagnose': 'Diagnose',
        'act.fix': 'Fix',
        'act.discuss': 'Discuss',
        'act.execute': 'Execute',
        'act.view': 'View',
        'act.load': 'Load',
        'act.done': 'Complete',
        'type.research': 'Research',
        'type.prototype': 'Prototype',
        'type.grilling': 'Align',
        'type.task': 'Task',
        'list.back': 'Back to list',
        'list.mapChip': 'Map',
        'list.loadFail': 'Failed to load',
        'list.noDest': '(no Destination)',
        'list.kpi.takeable': 'Ready',
        'list.kpi.occupied': 'Blocked',
        'list.kpi.closed': 'Closed',
        'list.refresh': 'Refresh',
        'list.envWarn': '{n} check(s) not ready — click to view',
        'list.all': 'All',
        'list.loading': 'Loading…',
        'list.errFull': 'Snapshot failed: {err}',
        'list.none': 'None',
        'list.closedN': 'Closed {n}',
        'list.collapse': 'Collapse',
        'list.blocked': 'Blocked',
        'list.blockedTitle': 'Blocked by {by} (click for map details)',
        'list.tagsTitle': 'All labels: {names} (click to expand)',
        'list.tagsCount': 'All labels · {n}',
        'list.popTitle': 'Title',
        'cfg.previewTitle': 'Sample issue title',
        'list.tagsCollapseTitle': 'Collapse labels',
        'list.copyLinkTitle': 'Copy link',
        'list.openInGithubTitle': 'Open #{n} on GitHub',
        'list.mapTitle': 'View map details',
        'list.state.all': 'All', 'list.state.open': 'Open', 'list.state.closed': 'Closed', 'list.state.blocked': 'Blocked',
        'list.sort.updatedAt': 'Updated', 'list.sort.createdAt': 'Created', 'list.sort.number': 'Number', 'list.sort.title': 'Title',
        'map.decisions': 'Decisions so far ({n})',
        'map.fog': 'Not yet specified (fog {n})',
        'map.outOfScope': 'Out of scope ({n})',
        'map.grpTakeable': 'Ready {n}',
        'map.grpClaimed': 'Claimed {n}',
        'map.grpBlocked': 'Blocked {n}',
        'map.grpClosed': 'Closed {n}',
        'map.layer': 'Layer {n}',
        'map.progressCap': 'Map progress',
        'map.curLayer': 'Current: layer {n}',
        'map.layersPassed': '{n}/{t} layers passed',
        'map.startCap': 'Start',
        'map.destCap': 'Destination',
        'map.startBtn': 'Start #{n}',
        'map.archive': 'Archive',
        'map.subClaimed': 'Claimed by {who}',
        'map.subBlocked': 'Blocked by: {who}',
        'map.subClosed': 'Closed',
        'map.executeTitle': 'Execute · inject the map\'s start prompt',
        'map.doneTitle': 'Complete · inject the wrap-up confirmation prompt',
        'skill.centerRing': 'Center = recommended · Ring = related (filled = installed / hollow = not) · click to inject /skill',
        'skill.centerTitle': 'Recommended {skill} · click to inject /{skill}',
        'skill.all': 'All skills',
        'skill.generic': 'General suggestion',
        'skill.notes': 'Specified by "{m}" Notes',
        'skill.treat': 'Handle with /{s}',
        'skill.list': 'List',
        'skill.ring': 'Ring',
        'env.title': 'Environment checks {n}/8',
        'env.recheck': 'Re-check',
        'env.checking': 'Checking…',
        'env.missing': 'Missing',
        'env.partial': 'Partial',
        'env.ready': 'Ready',
        'env.failFull': 'Environment check failed: {err}',
        'env.detecting': 'Detecting…',
        'env.missingBanner': '{n} missing — fix them before starting wayfinder work',
        'env.openUrl': 'Open URL',
        'env.copyUrl': 'Copy URL',
        'panel.snapErr': 'Snapshot error',
        'panel.loading': 'Loading…',
        'panel.tabList': 'List',
        'panel.tabSkills': 'Skills',
        'panel.tabChecks': 'Checks',
        'panel.refreshing': 'Refreshing…',
        'panel.closeTitle': 'Close panel',
        'rz.n': 'Drag the top edge up = grow taller', 'rz.s': 'Drag the bottom edge down = grow taller', 'rz.e': 'Drag the right edge right = grow wider', 'rz.w': 'Drag the left edge left = grow wider',
        'rz.ne': 'Resize NE', 'rz.nw': 'Resize NW', 'rz.se': 'Resize SE', 'rz.sw': 'Resize SW',
        'toast.injectedHandoff': '/handoff template injected (timestamped filename) — confirm before sending',
        'toast.copiedHandoff': 'Handoff command copied',
        'toast.copiedHandoffFile': 'Handoff command copied: {file}',
        'toast.copiedHandoffNoLatest': 'Handoff command copied (cannot query the latest doc, fallback)',
        'toast.handoffNotFound': 'Handoff doc not found; default path copied. Send /handoff first to generate',
        'toast.copiedHandoffFail': 'Handoff command copied (query failed, fallback)',
        'toast.injected': 'Injected into the input box — confirm before sending',
        'toast.copiedFallback': 'Copied to clipboard (input box unavailable)',
        'toast.copied': 'Copied',
        'toast.copyFailed': 'Copy failed — copy manually',
        'toast.clipboardUnavailable': 'Clipboard unavailable',
        'toast.snapFail': 'Snapshot refresh failed: {err}',
        'toast.copiedLink': 'Link # {n} copied',
        'toast.newSessionOpened': 'Opened in a new session with the prompt prefilled (same cwd)',
        'toast.newSessionManual': 'Please create a new session manually and name it "{title}"; the prompt is prefilled in the current input',
        'toast.resetPanelWidthDone': 'Panel width reset · takes effect on next open',
        'toast.resetPanelWidthFail': 'Layout service doesn\'t support reset yet · please update DSH harness',
        // #394：visible label + hover title for new-session button
        'list.newSessionLabel': 'New session',
        'panel.newWayfinder': 'New wayfinder',
        'panel.newWayfinderTitle': 'Inject a /wayfinder new-requirement prompt (with the current repo)',
        'panel.repoTitle': 'Current repo — open on GitHub',
        'map.newSessionTitle': 'Open in a new session (advance this map)',
        'err.hostUnavailable': 'host.call unavailable (host half not loaded)',
        'err.connUnavailable': 'connection service unavailable (host half not loaded)',
        'err.statusEmpty': 'wf.status returned an empty result',
        'err.snapshotEmpty': 'wf.snapshot returned an error',
        'cfg.status': 'Config',
        'cfg.saved': 'Saved',
        'cfg.sub': 'Configure the panel and action prompts: static text is freely editable; placeholders are filled in by the system — click to insert.',
        'cfg.openIn': 'Open in',
        'cfg.openInDesc': 'Where the panel opens. Defaults to the sidebar when dsh-better-sidebar is installed; the sidebar stays put when the window shrinks.',
        'cfg.openInLabel': 'Open location',
        'cfg.openInDock': 'Details column',
        'cfg.openInSidebar': 'Sidebar',
        'cfg.openInHint': 'Applied instantly — next panel open uses this location',
        'cfg.panelWidth': 'Panel width',
        'cfg.resetPanelWidth': 'Reset panel width',
        'cfg.resetPanelWidthDesc': 'Next panel open will use the layout service default width (clears the persisted drag memory).',
        'cfg.startTpl': 'Start template (execute)',
        'cfg.startTplDesc': 'Prompt injected by the Execute button; leave empty for the default template.',
        'cfg.withPrefix': 'Prefix with /wayfinder',
        'cfg.tplEditor': 'Action template editor',
        'cfg.tplEditorDesc': 'Prompts for the six action buttons other than Execute. Click a placeholder below to insert at the cursor; deleting a red Required placeholder blocks saving.',
        'cfg.execHint': 'Edit the Execute template in the Start template section →',
        'cfg.saveRejected': 'Save rejected',
        'cfg.saveAll': 'Save all',
        'cfg.resetAll': 'Reset all defaults',
        'cfg.reset': 'Reset default',
        'cfg.preview': 'Preview',
        'cfg.must': 'Required',
        'cfg.chipReq': 'Required placeholder: cannot save without it',
        'cfg.chipInsert': 'Click to insert at cursor',
        'tpl.missing': 'Missing required placeholder(s): {list}',
        'tpl.unknown': 'Unknown placeholder(s): {list}',
        'tpl.name.diagnose': 'Diagnose', 'tpl.name.fix': 'Fix', 'tpl.name.discuss': 'Discuss',
        'tpl.name.handoff1': 'Handoff · first hit', 'tpl.name.handoff2': 'Handoff · second hit', 'tpl.name.fixate': 'Consolidate',
        'tpl.desc.diagnose': 'Row action for needs-triage tickets',
        'tpl.desc.fix': 'Row action for bug tickets',
        'tpl.desc.discuss': 'Row action for wayfinder:grilling tickets',
        'tpl.desc.handoff1': 'Generate the handoff doc (timestamped; both hits share the filename)',
        'tpl.desc.handoff2': 'Read the handoff doc',
        'tpl.desc.fixate': 'Zero-loss snapshot prompt',
        'run.loaded': 'Loaded',
        'run.desc': 'Environment checks (wf.status) and panel (wf.snapshot) are live.',
        'run.openPanel': 'Open panel',
        'run.openCfg': 'Open config',
        'run.cfgGuide': 'Config: Settings → Plugins → Waystation',
        'skilldesc.ask-matt': 'Skill router: ask it when unsure which skill to use',
        'skilldesc.setup-matt-pocock-skills': 'Repo bootstrap: issue tracker / labels / doc paths',
        'skilldesc.wayfinder': 'Decision maps for large projects (what this plugin serves)',
        'skilldesc.triage': 'Issue state machine: categorise→verify→grill',
        'skilldesc.grilling': 'Relentless alignment questioning (design tree)',
        'skilldesc.domain-modeling': 'Domain terms & ubiquitous language',
        'skilldesc.research': 'Background research written into repo markdown with sources',
        'skilldesc.prototype': 'One-off prototype answering a design question',
        'skilldesc.implement': 'Turn specs into code (task tickets)',
        'skilldesc.code-review': 'Review changes on standards + spec axes',
        'skilldesc.codebase-design': 'Deep module design vocabulary',
        'skilldesc.diagnosing-bugs': 'Diagnosis loop for hard bugs & performance regressions',
        'skilldesc.improve-codebase-architecture': 'Scan deepening opportunities, output an HTML report',
        'skilldesc.tdd': 'Red-green-refactor',
        'skilldesc.handoff': 'Compress this conversation into a handoff doc',
        'skilldesc.teach': 'Teach you new skills across sessions',
        'skilldesc.to-spec': 'Turn discussions into specs',
        'skilldesc.to-tickets': 'Split specs into tickets',
        'skilldesc.resolving-merge-conflicts': 'Resolve merge conflicts',
        'skilldesc.writing-great-skills': 'Write great skills',
      },
    }
    const localeSvc = ctx.get('locale')
    if (localeSvc && typeof localeSvc.register === 'function') {
      ctx.effect(function () {
        return localeSvc.register('dsws', L)
      }, 'dsws: locale')
    }
    // tr：locale 绑定（稳定引用，调用时读当前语言；命名 tr 避免与票务参数 t 冲突）；服务缺失时退化 zh 字典（与 locale 同语义：{name} 参数替换）
    const tr = (localeSvc && typeof localeSvc.bind === 'function')
      ? localeSvc.bind('dsws')
      : function (key, params) {
          let s = (L.zh[key] !== undefined) ? L.zh[key] : key
          if (params) s = s.replace(/\{(\w+)\}/g, function (m, name) { return name in params ? String(params[name]) : m })
          return s
        }

    // ============================================================
    // 1. 技能目录 + 场景推荐映射
    // ============================================================
    // T3：描述在渲染时 tr('skilldesc.<name>')（此处 use 字段为中文静态参考）
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
        // #394：与 nav.handoff 同图标造成「交接 / 新开会话」二义；新会话按钮换 external-link 消歧
        case 'external-link': return h('svg', common, [h('path', { d: 'M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6' }), h('polyline', { points: '15 3 21 3 21 9' }), h('line', { x1: 10, y1: 14, x2: 21, y2: 3 })])
        default: return null
      }
    }

    // ============================================================
    // 2.5 配置模型（v25 · T2a：dsws.cfg + dsws.templates；旧 dsws.startCfg 自动迁移）
    // 必须位于 §3 store 之前（DEFAULT_PANEL_H 固定 1/2）
    // ============================================================
    // v22：统一引导句（T1 拍板：普通静态文本，用户可改；不是占位符）
    const GUIDE_LINE = '从第一性原理出发完成任务，并对抗式审查。'
    // v1.4（T2 #443）：map 推进式执行 prompt —— 仅用于 map（详情页主按钮 + 列表 map 行执行），
    //   语义 = 在 map 上推进一步：加载技能 → 分析 map → 第一性原理挑下一个 frontier issue → 执行
    const MAP_EXECUTE_PROMPT = '请按以下流程推进该 map：\n' +
      '1. 加载 wayfinder 技能（如未加载）；\n' +
      '2. 分析这个 map（Destination / Notes / 阻塞关系 / 当前 frontier）；\n' +
      '3. 按第一性原理分析当前最适合推进的下一个 issue（frontier 中价值最高、风险最低、最解阻的）；\n' +
      '4. 去执行它：读该 issue 的 Description / Notes / 阻塞关系 → 制定方案 → 实施 → 验收。\n\n' +
      GUIDE_LINE
    // T4 #8：完成 prompt 措辞优化（直接对应用户原话：询问 AI 当前 issue 情况，为什么该 map 还没有关闭，请它进行检查和确认）
    const COMPLETE_PROMPT = '## 完成确认 · MAP #{n}\n' +
      '\n' +
      '当前地图显示 100% 完成：{closed}/{total} 个 issue 已关闭，但 map 本身仍 open。\n' +
      '\n' +
      '请按以下流程处理：\n' +
      '\n' +
      '1. 检查完成状态是否真实：{closed}/{total} 已 CLOSED —— 但 map 本身仍 OPEN。请检查：\n' +
      '   - 子票是否真的解决了原 Destination？\n' +
      '   - 是否还有 Not yet specified 中未毕业的事项？\n' +
      '   - 实际已完成却漏标 CLOSED 的 issue（漏关/误开）—— 逐个核对 ticket 的完成状态与关闭状态是否一致；\n' +
      '   - 是否有 issue 属于该 map 但未建立 sub-issue 关系；\n' +
      '2. 确认后处理：\n' +
      '   - 确实全部完成 → 调用 close + 在 Decisions so far 追加总结（每个 closed ticket 一行 gist）；\n' +
      '   - 发现遗漏 → 列出未完成项，先解决再重新判断；\n' +
      '   - 不确定 → 询问用户「该地图的全部工作是否已完成，需要做收尾吗？」不要擅自 close；\n' +
      '3. 最终目标：要么 close map + 写 Decisions so far 总结，要么明确指出未完成项。\n' +
      '\n' +
      GUIDE_LINE
    // v10：沉淀 = 会话级动作 —— 注入「零丢失快照」prompt（默认模板文本，T2b 可编辑）
    const FIXATE_PROMPT = '里程碑固化点。暂停推进，执行「零丢失快照」，从第一性原理出发：\n' +
      '\n' +
      '1. 全量复述：把我从会话开始到现在说过的全部信息，按「目的地 / 约束与偏好 / 已确认的决定 / 待决问题 / 雾区（隐约可见但还不清晰）」五类，逐条列出——不压缩、不合并，宁可啰嗦不可省略。\n' +
      '2. 每条后面标注出处：用我的原话引用，让我知道它来自我哪句话。\n' +
      '3. 单独列一节「可疑遗漏」：凡是我提过、但你觉得与主线无关、太模糊或像执行细节而没纳入的，全部摆出来，写明你当初不纳入的理由，由我裁决。\n' +
      '4. 列完后停下等我逐条核对。我确认或修正完毕后，你再把清单落盘：已有地图就写进 map 正文和对应 ISSUE；只有ISSUE就写进对应ISSUE；都没有就先生成一份快照笔记并告诉我存哪，等建图时搬入。'

    const CFG_KEY = 'dsws.cfg'
    // 功能配置（用户拍板 2026-08-14：外观图标/动作词由设计定死，不提供配置项）
    // v1.4：打开位置 cfg.openIn —— 检测到 dsh-better-sidebar 已装则默认 'sidebar'，否则 'dock'；
    //   localStorage 已有值则尊重用户选择（不覆盖）
    const cfg = (function () {
      const bsInstalled = !!(ctx.get('betterSidebar') && typeof ctx.get('betterSidebar').registerTab === 'function')
      const d = { withWayfinder: true, openIn: bsInstalled ? 'sidebar' : 'dock' }
      try {
        const raw = localStorage.getItem(CFG_KEY)
        if (raw) {
          const saved = JSON.parse(raw)
          if (typeof saved.openIn === 'string') d.openIn = saved.openIn  // 用户已选过 → 尊重
          else d.openIn = bsInstalled ? 'sidebar' : 'dock'              // 首次 → 按安装情况默认
        }
        return Object.assign({ withWayfinder: true, openIn: 'dock' }, d)
      } catch (e) { /* 存储不可用用默认 */ }
      return d
    })()
    const saveCfg = function () { try { localStorage.setItem(CFG_KEY, JSON.stringify(cfg)) } catch (e) {} }
    // 模板存储（T2b 扩展全部动作；T2a 先承载 execute = 旧 custom）
    const TPL_KEY = 'dsws.templates'
    const templates = (function () {
      const d = { diagnose: '', fix: '', discuss: '', execute: '', handoff1: '', handoff2: '', fixate: '' }
      try {
        const raw = localStorage.getItem(TPL_KEY)
        if (raw) return Object.assign(d, JSON.parse(raw))
      } catch (e) { /* 存储不可用用默认 */ }
      return d
    })()
    const saveTemplates = function () { try { localStorage.setItem(TPL_KEY, JSON.stringify(templates)) } catch (e) {} }
    // 迁移：旧 dsws.startCfg（{withWayfinder, custom}）→ cfg.withWayfinder + templates.execute，成功后清旧 key
    const migrateStartCfg = function () {
      try {
        const raw = localStorage.getItem('dsws.startCfg')
        if (!raw) return
        const old = JSON.parse(raw)
        if (old && typeof old === 'object') {
          if (typeof old.withWayfinder === 'boolean') cfg.withWayfinder = old.withWayfinder
          if (typeof old.custom === 'string' && old.custom) templates.execute = old.custom
          saveCfg(); saveTemplates()
        }
        localStorage.removeItem('dsws.startCfg')
      } catch (e) { /* 迁移失败保留旧 key，下次再试 */ }
    }
    migrateStartCfg()

    // ---- v25 · T2b：动作模板引擎（T1 规格 §2-§4）----
    // 占位符全集：{url} {number} {title} {ts} {file}（引导句是普通静态文本，不是占位符）
    const PH = ['url', 'number', 'title', 'ts', 'file']
    // 各模板可用占位符（编辑器 chips 展示）
    const TPL_PH = {
      diagnose: ['url'], fix: ['url'], discuss: ['url'], execute: ['number', 'url', 'title'],
      handoff1: ['ts'], handoff2: ['file'], fixate: [],
    }
    // 强制占位符表（T1 规格 §3）：缺失拒绝保存
    const TPL_REQUIRED = {
      diagnose: ['url'], fix: ['url'], discuss: ['url'], execute: ['url'],
      handoff1: ['ts'], handoff2: ['file'], fixate: [],
    }
    // 默认模板文本（空 = 用默认；T1 规格 §3 默认文本 = 现状代码文本）
    const TPL_DEFAULT = {
      // T4 #9-12：4 个动作按钮 prompt 明确化
      diagnose: '/triage\n{url}\n\n请诊断该 issue 并分流建议：\n1. 复现 / 现象 / 影响范围\n2. 根因推断（多个候选）\n3. 分流建议（修复 / 关闭 / 重设计 / 等）\n\n' + GUIDE_LINE,
      fix: '/wayfinder\n{url}\n\n请修复该 bug：\n1. 先复现\n2. 定位根因\n3. 实施修复\n4. 加测试\n5. 对抗式审查\n\n' + GUIDE_LINE,
      discuss: '/wayfinder\n{url}\n\n请与我就该 issue 进行讨论（grill）：\n1. 目标 / 边界\n2. 风险 / 假设\n3. 选项 / 权衡\n4. 决策\n\n' + GUIDE_LINE,
      execute: '{url}\n\n请执行该 issue：\n1. 读 Description / Notes / 阻塞关系\n2. 制定方案\n3. 实施\n4. 验收\n\n' + GUIDE_LINE,
      handoff1: '/handoff\n\n请把当前会话生成交接文档，写到 .scratch/handoff/{ts}.md（相对当前工作目录），包含三部分：\n' +
        '1. 结论：本次会话已确认的决定与成果；\n2. 未完成事项：下一步要继续的事；\n3. 建议 skill：新会话接手时建议加载的技能。\n\n' + GUIDE_LINE,
      handoff2: '/read .scratch/handoff/{file}\n\n请先阅读这份交接文档并复述确认理解（结论 / 未完成事项 / 建议 skill），然后' + GUIDE_LINE,
      fixate: FIXATE_PROMPT,
    }
    const tplText = (id) => templates[id] || TPL_DEFAULT[id] || ''
    // 渲染：转义 {{x}} → 字面 {x}（先替换哨兵防误替换），再替换已知占位符；未知占位符保留原样（保存层已拦截）
    const renderTemplate = function (id, values) {
      let text = String(tplText(id))
      const esc = []
      text = text.replace(/\{\{([a-zA-Z][a-zA-Z0-9]*)\}\}/g, function (m, name) { esc.push('{' + name + '}'); return '\u0001' + (esc.length - 1) + '\u0001' })
      text = text.replace(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g, function (m, name) {
        return Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : m
      })
      esc.forEach(function (s, i) { text = text.replace('\u0001' + i + '\u0001', s) })
      return text
    }
    // 校验：转义预处理 → 未知占位符检测 → 强制占位符缺失检测（T1 规格 §4 顺序）
    const validateTemplate = function (id, text) {
      const found = []
      const scrubbed = String(text || '').replace(/\{\{[a-zA-Z][a-zA-Z0-9]*\}\}/g, '')
      const re = /\{([a-zA-Z][a-zA-Z0-9]*)\}/g
      let m
      while ((m = re.exec(scrubbed)) !== null) found.push(m[1])
      const unknown = []
      found.forEach(function (n) { if (PH.indexOf(n) < 0 && unknown.indexOf(n) < 0) unknown.push(n) })
      const missing = []
      ;(TPL_REQUIRED[id] || []).forEach(function (n) { if (found.indexOf(n) < 0 && missing.indexOf(n) < 0) missing.push(n) })
      return { ok: unknown.length === 0 && missing.length === 0, unknown: unknown, missing: missing }
    }
    const fixateText = () => tplText('fixate')

    // ============================================================
    // 3. store（v14：按会话隔离；无 sid 时用 shared）
    // ============================================================
    // v24-48：面板默认高度 = 屏幕约 1/2
    // v1.5 T3：面板默认高度固定 1/2（用户拍板彻底移除 panelHeight 配置 —— details 列高度与它无关，配置不生效）
    const DEFAULT_PANEL_H = (function () {
      try { return Math.max(240, Math.round((window.innerHeight || 800) * 0.5)) } catch (e) { return 400 }
    })()
    // #374：主列表偏好（排序/状态过滤）持久化（localStorage 不可用时降级默认值）
    const LIST_PREFS_KEY = 'dsws.listPrefs'
    const listPrefs = (function () {
      const d = { sortKey: 'number', sortDir: 'asc', stateFilter: 'all' }
      try {
        const raw = localStorage.getItem(LIST_PREFS_KEY)
        if (raw) return Object.assign(d, JSON.parse(raw))
      } catch (e) { /* 存储不可用用默认 */ }
      return d
    })()
    const saveListPrefs = function () { try { localStorage.setItem(LIST_PREFS_KEY, JSON.stringify(listPrefs)) } catch (e) {} }
    // #375：label 点击记忆（次数 + 最近点击时间，双键排序）
    const LABEL_CLICKS_KEY = 'dsws.labelClicks'
    const labelClicks = (function () {
      try {
        const raw = localStorage.getItem(LABEL_CLICKS_KEY)
        if (raw) { const o = JSON.parse(raw); return (o && typeof o === 'object') ? o : {} }
      } catch (e) { /* 存储不可用降级纯频次 */ }
      return {}
    })()
    const saveLabelClicks = function () { try { localStorage.setItem(LABEL_CLICKS_KEY, JSON.stringify(labelClicks)) } catch (e) {} }
    const makeStore = () => ({
      open: false, tab: 'list', activeMap: null,
      notice: null, injector: null, tick: 0,
      pos: null, size: { w: 460, h: DEFAULT_PANEL_H },
      // 外观定死（用户拍板：图标/动作词不可配置）
      ui: { icon: 'compass', word: '沉淀' },
      snapshot: null,
      cwd: '', lblFilter: null, skillView: 'list', expLabels: false,
      // #374：状态过滤 + 排序（默认 更新时间↓，与现状一致）
      stateFilter: listPrefs.stateFilter, sortKey: listPrefs.sortKey, sortDir: listPrefs.sortDir,
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
    // v1.5 T1：BUG / 诊断计数（open 且带对应标签，与「可接」同口径）
    const hasLabelOf = function (x, nm) { return (x.labels || []).some(function (l) { return (typeof l === 'string') ? l === nm : l.name === nm }) }
    const bugCount = (st) => openIssuesOf(st).filter(function (x) { return hasLabelOf(x, 'bug') }).length
    const triageCount = (st) => openIssuesOf(st).filter(function (x) { return hasLabelOf(x, 'needs-triage') }).length

    // v19：共享 —— 标签配置色映射（从快照 issues 收集 GitHub label 配置色，动态查询非写死）
    const buildColorOf = function (st) {
      const colorOf = {}
      const issues = (st.snapshot && Array.isArray(st.snapshot.issues)) ? st.snapshot.issues : []
      issues.forEach(function (x) {
        (x.labels || []).forEach(function (l) { if (l.color && !colorOf[l.name]) colorOf[l.name] = l.color })
      })
      return colorOf
    }
    // T9：行级动作主色计算（与 mkRowAction 共享 · 给新会话按钮复用：与执行按钮同 label 主色）
    const isLightHex = function (hex) {
      try {
        const hh = String(hex || '').replace('#', '')
        if (!/^[0-9a-fA-F]{6}$/.test(hh)) return false
        const r = parseInt(hh.slice(0, 2), 16), g = parseInt(hh.slice(2, 4), 16), b = parseInt(hh.slice(4, 6), 16)
        return (299 * r + 587 * g + 114 * b) / 1000 > 160
      } catch (e) { return false }
    }
    const actionColorOf = function (x, colorOf) {
      const has = function (nm) { return (x.labels || []).some(function (l) { return (typeof l === 'string') ? l === nm : l.name === nm }) }
      const bc = function (nm, fb) { const cc = colorOf[nm]; return cc ? '#' + cc : fb }
      if (has('needs-triage')) return bc('needs-triage', '#f59e0b')
      if (has('bug')) return bc('bug', '#f87171')
      if (has('wayfinder:grilling')) return bc('wayfinder:grilling', '#d93f0b')
      return '#c084fc'
    }
    // #361：行级动作注入文本的单一真源（诊断/修复/讨论/执行）—— 新会话打开与行内动作共用
    const rowActionText = function (st, x) {
      const url = 'https://github.com/' + repoStr(st) + '/issues/' + x.number
      const has = function (nm) { return (x.labels || []).some(function (l) { return (typeof l === 'string') ? l === nm : l.name === nm }) }
      if (has('needs-triage')) return renderTemplate('diagnose', { url: url })
      if (has('bug')) return renderTemplate('fix', { url: url })
      if (has('wayfinder:grilling')) return renderTemplate('discuss', { url: url })
      return startText(st, x)
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
          className: 'dsws-btn primary' + (narrow ? ' narrow-icon' : ''),
          onClick: function (e) { e.stopPropagation(); inject(st, text) },
          style: { display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 6px', fontSize: 11, flex: 'none', background: colorHex, borderColor: 'transparent', color: light ? '#140a1e' : '#ffffff' },
          title: label,
        }, [Ic({ n: icon, size: 10 }), narrow ? null : h('span', null, label)])
      }
      // v21：技能命令 + URL + 统一引导句（不再重复灌输技能内部流程）
      // v25 · T2b：诊断/修复/讨论走模板渲染（用户可自定义静态文本，{url} 注入）
      if (has('needs-triage')) return mk('chat', tr('act.diagnose'), rowActionText(st, x), btnColor('needs-triage', '#f59e0b'))
      if (has('bug')) return mk('hammer', tr('act.fix'), rowActionText(st, x), btnColor('bug', '#f87171'))
      if (has('wayfinder:grilling')) return mk('chat', tr('act.discuss'), rowActionText(st, x), btnColor('wayfinder:grilling', '#d93f0b'))
      return mk('play', tr('act.execute'), rowActionText(st, x), '#c084fc')
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
        st.checksError = tr('err.hostUnavailable')
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
          st.checksError = (res && res.error) ? String(res.error).slice(0, 160) : tr('err.statusEmpty')
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

    // #370：blockerNames 只列「仍 OPEN」的阻塞者（GitHub 依赖边在阻塞者关闭后仍保留，需按状态过滤）
    const openBlockers = (t, m) => t.blockedBy.filter(function (b) {
      const bt = m.tickets.find(function (x) { return x.number === b })
      return bt !== undefined && bt.state === 'OPEN'
    })
    const blockerNames = (t, m) => openBlockers(t, m).map(function (b) {
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
    // ============================================================
    // 4. 配置广播（v25-50：配置保存后同步所有会话 store 的面板尺寸；外观定死不广播）
    // ============================================================
    const broadcastCfg = function () {
      const applyTo = function (st) {
        if (!st) return
        st.size = { w: st.size ? st.size.w : 460, h: Math.max(240, Math.round((window.innerHeight || 800) * 0.5)) }
        emit(st)
      }
      applyTo(shared)
      Object.keys(stores).forEach(function (k) { applyTo(stores[k]) })
    }

    // 快照（#346：面板数据源；force 走 wf.refresh 全量重建；wf.snapshot 侧 5s 缓存）
    const loadSnapshot = function (st, force) {
      // #370 次要观察：force 刷新时跳过 snapLoading 守卫（加载中点击「刷新」不再 no-op）
      if (st.snapLoading && !force) return Promise.resolve()
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        st.snapMode = 'err'
        st.snapError = tr('err.hostUnavailable')
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
          st.snapError = (snap && snap.error) ? String(snap.error).slice(0, 160) : tr('err.snapshotEmpty')
          if (force) flash(st, tr('toast.snapFail', { err: st.snapError }), 'warn')
        }
        emit(st)
      }).catch(function (e) {
        st.snapLoading = false
        st.snapMode = 'err'
        st.snapError = String((e && e.message) || e).slice(0, 160)
        if (force) flash(st, tr('toast.snapFail', { err: st.snapError }), 'warn')
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

    // #376：打开面板即保证新鲜 —— 未就绪/失败 → force 加载（有「加载中」反馈）；
    //   已就绪但过期（>60s）→ 触发加载；已就绪且新鲜（≤60s）→ 直接展示不重复请求（配额友好）。
    //   force 不被 snapLoading 守卫丢弃（#370 已修），加载中打开面板最终也会完成并展示。
    const SNAP_FRESH_MS = 60000
    const snapFresh = function (st) {
      if (!st.snapshot || !st.snapshot.generatedMs) return false
      try { return (Date.now() - st.snapshot.generatedMs) <= SNAP_FRESH_MS } catch (e) { return false }
    }
    // 打开形式（#373 用户拍板 2026-08-14）：仅右侧 details 列（停靠）一种形式。
    //   已移除：① Document PiP 独立小窗（Electron 无法创建 PiP 窗口、曾致桌面卡死 —— 代码不再含 pip 形态）；
    //   ② 停靠/悬浮双模式记忆（PANEL_MODE_KEY）；③ 状态栏「停靠」seg 与右栏「悬浮」按钮。
    //   打开一律走 layout.openDetails()；layout 服务不可用时退回页内悬浮面板（仅兜底，无任何入口按钮）。
    const openPagePanel = function (st) {
      st.open = true
      if (st.snapMode === 'real' && snapFresh(st)) {
        // v1.3.3 #5：数据新鲜直接展示，不 loading 不刷新（用户不再白等）
        emit(st)
      } else if (st.snapMode === 'real') {
        // v1.3.3 #5：数据过期 → 保留旧数据展示 + 后台静默刷新（非 force · 走 5s 缓存），不弹全屏遮罩
        emit(st)
        loadSnapshot(st, false)
      } else {
        // 首开无数据 → 加载态 + 非 force 拉取
        st.snapMode = 'loading'
        emit(st)
        loadSnapshot(st, false)
      }
    }
    // 打开面板：一律右侧停靠（details 列）；layout 服务不可用 → 页内兜底
    const openDockPanel = function (st) {
      const ls = ctx.get('layout')
      if (ls && typeof ls.openDetails === 'function') {
        ls.openDetails()
        if (st.snapMode === 'real' && snapFresh(st)) {
          emit(st)
        } else if (st.snapMode === 'real') {
          emit(st)
          loadSnapshot(st, false)
        } else {
          loadSnapshot(st, false)
        }
        return
      }
      openPagePanel(st)  // layout 服务不可用 → 退回悬浮
    }
    // v1.4：打开位置可选 —— cfg.openIn: 'dock'（details 列，默认）/ 'sidebar'（dsh-better-sidebar tab）
    //   better-sidebar 已装时可用；未装或服务不可用 → 回退 details 列
    // v1.4.1 修复「切侧边栏没反应」：
    //   ① ensureSidebarTab 幂等注册 —— better-sidebar 的 client 可能晚于本模块加载（未声明 inject 依赖），
    //      注册必须可重试；openTab 前 ensure 一次保证已注册（否则 openTab 静默 no-op）。
    //   ② openTab 带 path seed 走「内容型打开」→ 侧边栏面板折叠时自动展开
    //      （类型型打开不展开面板，侧边栏收着就「看不见 = 没反应」）。
    let sidebarTabDisposer = null
    let sidebarTabRetry = null
    const ensureSidebarTab = function () {
      if (sidebarTabDisposer) return true
      try {
        const bs = ctx.get('betterSidebar')
        if (!(bs && typeof bs.registerTab === 'function')) return false
        const WaystationSidebarTab = function (props) {
          const scope = props && props.scope
          const sessionId = scope ? scope.sessionId : undefined
          return h('div', { style: { height: '100%', overflow: 'hidden' } }, h(DetailsDock, { sessionId: sessionId }))
        }
        sidebarTabDisposer = bs.registerTab({
          id: 'waystation:map',
          title: function () { return 'Waystation' },
          icon: function () { return Ic({ n: 'map', size: 14 }) },
          order: 60,
          single: true,
          component: WaystationSidebarTab,
        })
        return true
      } catch (e) { return false }
    }
    const openInSidebar = function (st) {
      const bs = ctx.get('betterSidebar')
      if (bs && typeof bs.openTab === 'function') {
        if (!ensureSidebarTab()) { openDockPanel(st); return }  // 注册失败 → 回退 details 列
        bs.openTab({ type: 'waystation:map', path: 'waystation:map' })  // path seed → 内容型打开 → 自动展开面板
        // 打开 tab 即视为面板已开（数据新鲜直接展示）
        if (st.snapMode === 'real' && snapFresh(st)) { emit(st); return }
        if (st.snapMode === 'real') { emit(st); loadSnapshot(st, false); return }
        loadSnapshot(st, false)
        return
      }
      openDockPanel(st)  // better-sidebar 不可用 → 回退 details 列
    }
    const openPanel = function (st) {
      if (cfg.openIn === 'sidebar') openInSidebar(st)
      else openDockPanel(st)
    }
    const togglePanel = function (st) {
      if (st.open) { st.open = false; emit(st); return }
      openPanel(st)
    }

    const repoStr = (st) => (st.snapshot && st.snapshot.repo)
      ? st.snapshot.repo.owner + '/' + st.snapshot.repo.name
      : 'FeatherHunter/SKILLS'

    // v21：开始 prompt 精简 —— /wayfinder + URL + 统一引导句（技能内部细节自带，不再重复灌输）
    // v25 · T2b：execute 走模板渲染（templates.execute 或默认），前缀开关 = cfg.withWayfinder
    // v1.3.3 #10：前缀去重 —— 模板（含用户自定义旧模板）若已以 /wayfinder 开头则不再重复拼接
    const withWayfinderPrefix = function (body) {
      if (!cfg.withWayfinder) return body
      if (/^\/wayfinder\b/.test(String(body || '').trim())) return body
      return '/wayfinder\n' + body
    }
    const startText = (st, t) => {
      const url = 'https://github.com/' + repoStr(st) + '/issues/' + t.number
      // v1.4（T2 #443）：map 用推进式 prompt（加载技能→分析map→挑下一个issue→执行）；普通 issue 用 execute 模板
      const isMap = (t.labels || []).some(function (l) { return (typeof l === 'string') ? l === 'wayfinder:map' : l.name === 'wayfinder:map' })
      // v1.5 B2：map prompt 嵌入 map 标识（编号/标题/链接），新会话不再「找不到对应 ISSUE」
      if (isMap) return MAP_EXECUTE_PROMPT + '\n\n## 目标 map\n- 编号：#' + String(t.number || '') + '\n- 标题：' + (t.title || '') + '\n- 链接：' + url
      const body = renderTemplate('execute', { number: String(t.number), url: url, title: t.title })
      return withWayfinderPrefix(body)
    }
    const SESSION_TITLE_PREFIX = '[dsh-waystation]'
    const newSessionTitle = (t) => SESSION_TITLE_PREFIX + ' ' + t.title + ' #' + t.number
    // v1.5 T6：新增 wayfinder prompt —— /wayfinder + 仓库信息 + 需求引导（用户拍板：prompt 带仓库信息）
    const newWayfinderText = (st) => '/wayfinder\n请帮我（新增 / 复用 / 直接实现）一个需求：\n仓库：' + 'https://github.com/' + repoStr(st) + '\n需求描述：'

    // v10：沉淀 = 会话级动作 —— 注入「零丢失快照」prompt（默认文本见 §2.5 FIXATE_PROMPT，T2b 可编辑）
    const injectFixate = (st) => { inject(st, fixateText()) }

    // v24-48：交接 —— 第一击自动注入 /handoff 模板（带时间戳文件名 + 引导句）并记忆该时间戳；
    // 第二击优先读「第一击模板里的同一个文件」（模板写什么名就读什么名，不再查目录导致旧文件名）；
    // 仅当未点过第一击（如刷新后）才回退 host 查最新实际文档；+ 复制 + 开新空白会话
    // v25 · T2b（F1 修正）：交接两击走模板渲染；{ts} 第一击注入时生成并记忆；
    //   {file} = 第一击模板渲染后解析出的实际文件名（用户改文件名结构也一致），解析失败兜底 handoffTs + '.md'
    const HANDOFF_READ = '/read .scratch/handoff/latest.md'
    let handoffTs = null  // v24：第一击模板使用的时间戳（第二击优先复用同一文件名）
    let handoffFile = null  // v25 F1：第一击渲染后解析出的实际交接文件名（含用户自定义结构）
    const handoffPrompt = function (ts) {
      return renderTemplate('handoff1', { ts: ts })
    }
    // 从第一击注入文本解析 .scratch/handoff/<name>.md 的实际文件名（T1 规格 §2 发现 1）
    const extractHandoffFile = function (text) {
      const m = String(text || '').match(/\.scratch\/handoff\/([^\s"'`]+\.md)/)
      return m ? m[1] : null
    }
    const handoffReadText = function (file) {
      if (file) return renderTemplate('handoff2', { file: file })
      return HANDOFF_READ + '\n\n请先阅读这份交接文档并复述确认理解（结论 / 未完成事项 / 建议 skill），然后' + GUIDE_LINE
    }
    let pendingDraft = null  // 跨会话预填（新会话 dock 挂载后消费）
    const doHandoff = function (st) {
      if (!st.handoffReady) {
        st.handoffReady = true
        handoffTs = timeStampStr()
        const text = handoffPrompt(handoffTs)
        handoffFile = extractHandoffFile(text) || (handoffTs + '.md')
        inject(st, text)
        flash(st, tr('toast.injectedHandoff'), 'ok')
        return
      }
      const ws = ctx.get('workspaces')
      const cwdArg = st.cwd ? { cwd: st.cwd } : {}
      const finish = function (file, msg) {
        const text = handoffReadText(file)
        pendingDraft = text
        copyText(st, text, msg || tr('toast.copiedHandoff'))
        if (ws && typeof ws.startSession === 'function') {
          ws.startSession()
        } else {
          pendingDraft = null
        }
      }
      // v24：第一击模板指定的时间戳文件名优先（与模板完全一致）
      if (handoffFile) {
        finish(handoffFile, tr('toast.copiedHandoffFile', { file: handoffFile }))
        return
      }
      if (typeof host === 'undefined' || typeof host.call !== 'function') {
        finish(null, tr('toast.copiedHandoffNoLatest'))
        return
      }
      host.call('wf.handoffLatest', cwdArg).then(function (res) {
        const file = (res && res.ok && res.file) ? res.file : null
        if (file) finish(file, tr('toast.copiedHandoffFile', { file: file }))
        else finish(null, tr('toast.handoffNotFound'))
      }).catch(function () {
        finish(null, tr('toast.copiedHandoffFail'))
      })
    }

    // #361：在新会话中打开 ticket —— 同 cwd + 自动命名（[dsh-waystation] <标题> #<号>）+ 预填指令
    //   契约（dsh-client-runtime ISessions）：create({cwd}) → SessionId；scope(sid) → AgentContext；
    //   sessionOf(ctx) → SessionFace.rename(title)；open(sid) 切换。任一步失败降级为当前会话注入 + 提醒。
    const openInNewSession = function (st, x) {
      const text = rowActionText(st, x)
      const sessions = ctx.get('sessions')
      const doFallback = function () {
        inject(st, text)
        flash(st, tr('toast.newSessionManual', { title: newSessionTitle(x) }), 'warn')
      }
      if (!sessions || typeof sessions.create !== 'function' || !st.cwd) { doFallback(); return }
      sessions.create({ cwd: st.cwd }).then(function (sid) {
        // 自动命名（失败不阻塞打开）
        try {
          const scopeCtx = sessions.scope(sid)
          const face = scopeCtx ? sessions.sessionOf(scopeCtx) : undefined
          if (face && typeof face.rename === 'function') face.rename(newSessionTitle(x)).catch(function () { /* 命名失败忽略 */ })
        } catch (e) { /* 命名失败忽略 */ }
        // 预填：新会话 dock 挂载后经 StatusBar 消费 pendingDraft（与交接开新会话同机制）
        pendingDraft = text
        sessions.open(sid)
        flash(st, tr('toast.newSessionOpened'), 'ok')
      }).catch(function () { doFallback() })
    }
    const inject = (st, text) => {
      if (st.injector) { st.injector(text); flash(st, tr('toast.injected'), 'ok') }
      else copyText(st, text, tr('toast.copiedFallback'))
    }
    const copyText = (st, text, okMsg) => {
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { flash(st, okMsg || tr('toast.copied'), 'ok') }).catch(function () { flash(st, tr('toast.copyFailed'), 'warn') })
      } else flash(st, tr('toast.clipboardUnavailable'), 'warn')
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
        h('span', null, tr('type.' + type)),
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
      const bugN = bugCount(s)
      const triageN = triageCount(s)
      const n = readyCount(s)
      const timeStr = timeOf(s.snapshot) || (s.checksUpdatedAt ? s.checksUpdatedAt.slice(5, 16) : '') || '-- --:--'
      const setup = setupCheck(s)
      const amber = s.checksMode === 'real' && setup && setup.level !== 'ok'
      const go = function (tab) { s.tab = tab; openPanel(s) }
      // v14-22：数字区固定两位数等宽（环境 5ch 容 '98/99'；可接/占用 2ch）
      const num = (txt, minW) => h('span', { className: 'dsws-num', style: minW ? { minWidth: minW } : null }, txt)
      const seg = (icon, label, color, onGo, title) => h('span', { className: 'dsws-seg', onClick: function (e) { e.stopPropagation(); onGo() }, title: title || '', style: { display: 'inline-flex', alignItems: 'center', gap: 4, color: color } }, [
        Ic({ n: icon, size: 12 }),
        label,
      ])
      const capsule = h('div', { className: 'dsws-capsule', onClick: function () { openPanel(s) } }, [
        h('span', { className: 'dsws-capsule-word', onClick: function (e) { e.stopPropagation(); togglePanel(s) } }, [
          Icon({ scheme: s.ui.icon, size: 14 }),
          h('span', null, 'Waystation'),
        ]),
        seg('target', [h('span', null, tr('nav.takeable')), num(String(fr), '2ch')], '#4ade80', function () { go('list') }, tr('nav.takeableTitle')),
        seg('alert', [h('span', null, tr('nav.bug')), num(String(bugN), '2ch')], '#f87171', function () { s.stateFilter = 'open'; s.lblFilter = 'bug'; go('list') }, tr('nav.bugTitle')),
        seg('search', [h('span', null, tr('nav.triage')), num(String(triageN), '2ch')], '#f59e0b', function () { s.stateFilter = 'open'; s.lblFilter = 'needs-triage'; go('list') }, tr('nav.triageTitle')),
        seg('note', tr('nav.word'), '#c084fc', function () { injectFixate(s) }, tr('nav.fixateTitle')),
        seg('handoff', s.handoffReady ? tr('nav.handoffReady') : tr('nav.handoff'), '#58a6ff', function () { doHandoff(s) }, s.handoffReady ? tr('nav.handoffReadyTitle') : tr('nav.handoffTitle')),
        // v19-36：环境段移至末尾（更新左侧），用户少点
        seg('dot', [h('span', null, tr('nav.env')), num(envLabel(s))], n < 0 ? '#f87171' : n === 8 ? '#4ade80' : '#f59e0b', function () { go('checks') }, tr('nav.envTitle', { n: n < 0 ? '?' : String(n) })),
        h('span', { className: 'dsws-timebtn', onClick: function (e) { e.stopPropagation(); refreshAll(s) }, title: tr('nav.refreshTitle') }, tr('nav.refresh') + ' ' + timeStr),
      ])
      if (!amber) return h('div', { style: { display: 'flex', justifyContent: 'center', padding: '3px 8px 0' } }, [capsule])
      return h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '3px 8px 0' } }, [
        capsule,
        h('div', { className: 'dsws-banner warn', style: { margin: 0, maxWidth: 560, cursor: 'default' } }, [
          Ic({ n: 'alert', size: 13 }),
          h('span', null, tr('banner.setup')),
          h('button', { className: 'dsws-btn', style: { borderColor: 'rgba(245,158,11,.6)' }, onClick: function () { inject(s, '/setup-matt-pocock-skills\n（请选择 GitHub Issues 作为 issue tracker）') } }, tr('banner.setupBtn')),
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
            // T2 #3：编号前置
            h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)', fontSize: 11, flex: 'none' } }, '#' + t.number),
            TypeChip({ type: t.type }),
            h('span', { className: 'dsws-tt-wrap', style: { flex: 1 }, title: t.title }, t.title),
          ]),
          h('div', { className: 'dsws-tt-sub', style: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' } }, [
            t.claimedBy ? subItem('person', '#58a6ff', tr('map.subClaimed', { who: t.claimedBy })) : null,
            // #370：被阻塞 chip 只显示仍 OPEN 的阻塞者（与 compute/主列表/按钮抑制口径一致）
            blocked ? subItem('lock', '#f0883e', tr('map.subBlocked', { who: blockerNames(t, g.m) })) : null,
            t.state === 'CLOSED' ? subItem('check', '#3fb950', tr('map.subClosed')) : null,
          ]),
        ]),
        t.state === 'OPEN' ? h('div', { style: { display: 'flex', gap: 4, alignItems: 'center', flex: 'none' } }, [
          blocked ? null : mkRowAction(st, t, false, colorOf),
          // #361 能力保留（同 cwd + 自动命名 + 预填指令）；#394：去 ghost/icon-only，与 nav.handoff 解耦
          //   marginLeft:4 与左侧 mkRowAction 形成隐式分组（动作组 vs 辅助组）
          h('button', { className: 'dsws-btn primary', onClick: function (e) { e.stopPropagation(); openInNewSession(st, t) }, title: tr('list.newSessionLabel'), style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 6px', fontSize: 11, flex: 'none', marginLeft: 4, background: actionColorOf(t, colorOf), borderColor: 'transparent', color: isLightHex(actionColorOf(t, colorOf)) ? '#140a1e' : '#ffffff' } }, [Ic({ n: 'external-link', size: 10 }), h('span', null, tr('list.newSessionLabel'))]),
          h('a', { className: 'dsws-btn ghost', title: tr('list.openInGithubTitle', { n: t.number }), href: 'https://github.com/' + repoStr(st) + '/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '3px 6px' } }, Ic({ n: 'link', size: 12 })),
        ]) : h('a', { className: 'dsws-btn ghost', href: 'https://github.com/' + repoStr(st) + '/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none' } }, tr('act.view')),
      ])
    }

    // ---- 5.4 地图详情（v1.4 · T2 #443：漏斗分层 + 战争迷雾 + 72px 仪式环 + 四态动作，D1-D8 规格）----
    //   层 = blockedBy DAG 最长路径深度（T1 #442 已算 stats.levels + 每票 t.level）
    const MapDetail = ({ st, g }) => {
      const m = g.m
      const colorOf = buildColorOf(st)
      const tickets = m.tickets || []
      const levels = (m.stats && m.stats.levels) || []
      const totalLayers = levels.length
      // 当前层 = 第一个含 open 票的层（无 open 全 done → 最后一层）
      const curLevel = (function () {
        for (let i = 0; i < levels.length; i++) { if (levels[i].open > 0) return i }
        return Math.max(0, levels.length - 1)
      })()
      const passedLayers = levels.filter(function (l, i) { return i < curLevel }).length
      const byLevel = {}
      tickets.forEach(function (t) { const lv = (typeof t.level === 'number') ? t.level : 0; (byLevel[lv] = byLevel[lv] || []).push(t) })
      // 迷雾：fog 票（Not yet specified）+ 被阻塞且其阻塞者 open 的票（半雾）；D7 视觉遮蔽
      const isFog = function (t) {
        if (t.state !== 'OPEN') return false
        const blk = (t.blockedBy || []).map(function (b) { return tickets.find(function (x) { return x.number === b }) }).filter(Boolean)
        return blk.some(function (b) { return b.state === 'OPEN' })
      }
      const fogTitles = (m.fog || []).map(function (f) { return String(f).trim() })
      const isFogTitle = function (t) { return fogTitles.some(function (f) { return f && t.title && t.title.indexOf(f) >= 0 }) }
      // v1.4：同层内排序 —— 可执行（open 且非迷雾）最左 → open 被阻塞 → 已关闭靠右（一眼看到当前能做什么）
      Object.keys(byLevel).forEach(function (lv) {
        byLevel[lv].sort(function (a, b) {
          const rank = function (t) {
            if (t.state === 'OPEN') return isFog(t) || isFogTitle(t) ? 1 : 0
            return 2
          }
          return rank(a) - rank(b) || a.number - b.number
        })
      })
      // 迷雾点击去雾状态（st 上按 map 存）
      st.reveal = st.reveal || {}
      const nodeCls = function (t) {
        let cls = 'dsws-node'
        if (t.state === 'CLOSED') cls += ' done'
        else if (t.level === curLevel) cls += ' now'
        const fog = isFog(t) || isFogTitle(t)
        if (fog) { cls += ' fog'; if (st.reveal[m.number] && st.reveal[m.number][t.number]) cls += ' revealed' }
        return cls
      }
      const toggleReveal = function (t) {
        st.reveal[m.number] = st.reveal[m.number] || {}
        st.reveal[m.number][t.number] = !(st.reveal[m.number][t.number])
        emit(st)
      }
      const gateState = function (layerIndex) {
        // 闸门：该层全 closed → open(绿✓)；层含 open 且在其之前层全 closed → open；否则 lock
        const lv = levels[layerIndex]
        if (!lv) return 'open'
        if (lv.closed === lv.total && lv.total > 0) return 'open'
        const prevAllClosed = levels.slice(0, layerIndex).every(function (p) { return p.closed === p.total })
        return prevAllClosed ? 'open' : 'lock'
      }
      const node = function (t) {
        const blocked = isFog(t)
        const acts = (t.state === 'OPEN' && !blocked) ? h('div', { className: 'acts' }, [
          mkRowAction(st, t, false, colorOf),
          h('a', { className: 'dsws-btn ghost', title: tr('list.openInGithubTitle', { n: t.number }), href: 'https://github.com/' + repoStr(st) + '/issues/' + t.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '2px 4px' } }, Ic({ n: 'link', size: 11 })),
        ]) : null
        // v1.4 修复：图标名必须用 Ic 支持的（search/hammer/chat/gear），原 mag/bolt/wrench 不存在 → 节点图标空白
        const ic = t.type === 'research' ? 'search' : t.type === 'prototype' ? 'hammer' : t.type === 'grilling' ? 'chat' : 'gear'
        return h('div', {
          key: t.number,
          className: nodeCls(t),
          onClick: (isFog(t) || isFogTitle(t)) ? function (e) { e.stopPropagation(); toggleReveal(t) } : undefined,
        }, [
          h('div', { className: 'row1' }, [
            h('span', { className: 'icbox' }, Ic({ n: ic, size: 12 })),
            h('div', { style: { flex: 1, minWidth: 0 } }, [
              h('div', { className: 'meta' }, [
                h('span', { className: 'no' }, '#' + t.number),
                TypeChip({ type: t.type }),
              ]),
              h('div', { className: 'tt', title: t.title }, t.title),
              h('div', { className: 'sub', style: { fontSize: 8, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginTop: 1, display: 'flex', gap: 5, flexWrap: 'wrap' } }, [
                t.state === 'CLOSED' ? h('span', { style: { color: '#3fb950', display: 'inline-flex', alignItems: 'center', gap: 2 } }, [Ic({ n: 'check', size: 8 }), h('span', null, tr('map.subClosed'))]) : null,
                t.claimedBy ? h('span', { style: { color: '#58a6ff', display: 'inline-flex', alignItems: 'center', gap: 2 } }, [Ic({ n: 'person', size: 8 }), h('span', null, t.claimedBy)]) : null,
                blocked ? h('span', { style: { color: '#f0883e', display: 'inline-flex', alignItems: 'center', gap: 2 } }, [Ic({ n: 'lock', size: 8 }), h('span', null, tr('map.subBlocked', { who: blockerNames(t, m) }))]) : null,
              ]),
            ]),
          ]),
          acts,
          (isFog(t) || isFogTitle(t)) ? h('svg', { className: 'qmark', viewBox: '0 0 24 24' }, [h('path', { d: 'M9.5 9a2.5 2.5 0 1 1 3.7 2.2c-.9.4-1.2 1-1.2 1.8' }), h('circle', { cx: '12', cy: '18', r: '.6' })]) : null,
        ])
      }
      const layerBlock = function (layerIndex) {
        const lv = levels[layerIndex]
        if (!lv) return null
        const layerTickets = byLevel[layerIndex] || []
        const single = layerTickets.length === 1
        const gate = gateState(layerIndex)
        return [
          h('div', { className: 'dsws-layerTag' }, [
            h('span', null, tr('map.layer', { n: layerIndex + 1 }) + ' · ' + lv.open + ' open'),
            h('span', { className: 'sp' }),
          ]),
          h('div', { className: 'dsws-layer' }, layerTickets.map(function (t) { return node(t) })),
          h('div', { className: 'dsws-gate' }, [
            h('span', { className: 'g ' + gate }, Ic({ n: gate === 'open' ? 'check' : 'lock', size: 12 })),
          ]),
        ]
      }
      // 完成态：全 closed → 进度条全绿 + 环满圈
      const allClosed = m.stats && m.stats.total > 0 && m.stats.closed === m.stats.total
      const ringPct = allClosed ? 1 : (totalLayers ? Math.min(1, (passedLayers + 1) / totalLayers) : 0)
      const C = 2 * Math.PI * 31
      const ringOff = C * (1 - ringPct)
      return h('div', null, [
        // 顶部操作行：返回 + map chip + 执行/完成
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 } }, [
          h('button', { className: 'dsws-btn', onClick: function () { st.activeMap = null; emit(st) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
            Ic({ n: 'back', size: 12 }),
            h('span', null, tr('list.back')),
          ]),
          h('span', { className: 'dsws-chip dsws-chip-m' }, [Ic({ n: 'map', size: 11 }), h('span', null, 'wayfinder:map')]),
          h('span', { style: { flex: 1 } }),
          (m.stats && m.stats.total > 0 && m.stats.closed === m.stats.total)
            ? h('button', { className: 'dsws-btn primary', title: tr('map.doneTitle'), onClick: function () {
                const text = COMPLETE_PROMPT
                  .split('{n}').join(String(m.number || ''))
                  .split('{total}').join(String(m.stats.total))
                  .split('{closed}').join(String(m.stats.closed))
                inject(st, text)
              }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', fontSize: 11, background: '#3fb950', borderColor: 'transparent', color: '#0c1a10', fontWeight: 600 } }, [
                Ic({ n: 'check', size: 10 }),
                h('span', null, tr('act.done')),
              ])
            : h('button', { className: 'dsws-btn primary', title: tr('map.executeTitle'), onClick: function () {
                // v1.4：map 推进式执行（startText 检测 wayfinder:map → MAP_EXECUTE_PROMPT）
                inject(st, startText(st, m))
              }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', fontSize: 11 } }, [
                Ic({ n: 'play', size: 10 }),
                h('span', null, tr('act.execute')),
              ]),
          // v1.5 B2（O5）：详情页「在新会话打开」—— 与 执行/完成 同语义，开新会话推进该 map
          h('button', { className: 'dsws-btn ghost', title: tr('map.newSessionTitle'), onClick: function () { openInNewSession(st, m) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', fontSize: 11, flex: 'none' } }, [
            Ic({ n: 'external-link', size: 10 }),
            h('span', null, tr('list.newSessionLabel')),
          ]),
        ]),
        h('div', { className: 'dsws-mtitle dsws-tt-wrap', title: m.title }, m.title),
        m.error ? h('div', { style: { color: '#f87171', fontSize: 11, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'alert', size: 11 }), h('span', null, String((m.error && m.error.error) || tr('list.loadFail')).slice(0, 160))]) : null,
        // D2：分段静态进度条 = 地图层缩略图（无动画，唯一真相源）
        (levels.length > 0) ? h('div', { className: 'dsws-layers' }, [
          h('div', { className: 'row1' }, [
            h('span', { className: 'cap' }, tr('map.progressCap')),
            h('div', { className: 'segs' }, levels.map(function (l, i) {
              const segCls = i < curLevel ? 'seg past' : (i === curLevel ? 'seg curr' : 'seg future')
              return h('div', { key: i, className: segCls, title: tr('map.layer', { n: i + 1 }) })
            })),
          ]),
          h('div', { className: 'row2' }, [
            h('span', { className: 'cur' }, [Ic({ n: 'play', size: 9 }), h('span', null, tr('map.curLayer', { n: curLevel + 1 }))]),
            h('span', { className: 'pos' }, tr('map.layersPassed', { n: passedLayers, t: totalLayers })),
          ]),
        ]) : null,
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#4ade80', margin: '4px 0 2px' } }, [Ic({ n: 'target', size: 12 }), h('span', { className: 'dsws-ellip', title: m.destination }, m.destination || tr('list.noDest'))]),
        m.notes ? h('div', { style: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', marginBottom: 4 } }, [Ic({ n: 'note', size: 11 }), h('span', { className: 'dsws-ellip', title: m.notes }, m.notes)]) : null,
        // 漏斗分层主体
        h('div', { style: { marginTop: 2 } }, [
          h('div', { className: 'dsws-start' }, [
            h('span', { className: 'cap' }, tr('map.startCap')),
          ]),
          levels.map(function (l, i) { return layerBlock(i) }),
          // D3：Destination 72px 仪式环（环心旗帜，无数字）
          h('div', { className: 'dsws-dest' }, [
            h('div', { className: 'ring' }, [
              h('svg', { width: 72, height: 72, viewBox: '0 0 72 72' }, [
                h('circle', { className: 'track', cx: 36, cy: 36, r: 31 }),
                h('circle', { className: 'prog', cx: 36, cy: 36, r: 31, strokeDasharray: String(C), strokeDashoffset: String(ringOff) }),
              ]),
              h('div', { className: 'core' }, h('svg', { viewBox: '0 0 24 24' }, [h('path', { d: 'M5 3v18' }), h('path', { d: 'M5 4c4-2 6 2 12 0v9c-6 2-8-2-12 0' })])),
            ]),
            h('div', { className: 'title' }, tr('map.destCap')),
            h('div', { className: 'acts' }, [
              // v1.4：底部按钮与顶部同语义 —— 完成态「完成」（COMPLETE_PROMPT 同列表）/ 未完成「执行」（execute 模板）
              (m.stats && m.stats.total > 0 && m.stats.closed === m.stats.total)
                ? h('button', { className: 'dsws-btn primary', title: tr('map.doneTitle'), onClick: function () {
                    const text = COMPLETE_PROMPT
                      .split('{n}').join(String(m.number || ''))
                      .split('{total}').join(String(m.stats.total))
                      .split('{closed}').join(String(m.stats.closed))
                    inject(st, text)
                  }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 12px', fontSize: 11, background: '#3fb950', borderColor: 'transparent', color: '#0c1a10', fontWeight: 700 } }, [
                    Ic({ n: 'check', size: 11 }),
                    h('span', null, tr('act.done')),
                  ])
                : h('button', { className: 'dsws-btn primary', title: tr('map.executeTitle'), onClick: function () {
                    // v1.4：map 推进式执行（startText 检测 wayfinder:map → MAP_EXECUTE_PROMPT）
                    inject(st, startText(st, m))
                  }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 12px', fontSize: 11, background: '#4ade80', borderColor: 'transparent', color: '#04120a', fontWeight: 700 } }, [
                    Ic({ n: 'play', size: 11 }),
                    h('span', null, tr('act.execute')),
                  ]),
              h('a', { className: 'dsws-btn ghost', href: 'https://github.com/' + repoStr(st) + '/issues/' + m.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 10px', fontSize: 11 } }, [Ic({ n: 'link', size: 11 }), h('span', null, tr('map.archive'))]),
            ]),
          ]),
        ]),
        // 折叠块：Decisions / Fog / Out of scope（保留信息展示）
        h('details', { style: { marginTop: 10, marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, tr('map.decisions', { n: m.decisions.length })),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.decisions.map(function (d, i) {
            return h('div', { key: i, className: 'dsws-ellip', title: d.title + ' ' + d.gist }, '· ' + d.title)
          })),
        ]),
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, tr('map.fog', { n: m.fog.length })),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.fog.map(function (f, i) { return h('div', { key: i, className: 'dsws-ellip', title: f }, '· ' + f) })),
        ]),
        h('details', { style: { marginBottom: 4 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', cursor: 'pointer' } }, tr('map.outOfScope', { n: m.outOfScope.length })),
          h('div', { style: { fontSize: 12, paddingLeft: 8 } }, m.outOfScope.map(function (o, i) { return h('div', { key: i, className: 'dsws-ellip', title: o }, '· ' + o) })),
        ]),
      ])
    }

    // ---- 5.5 主列表（v14：三选一动作 / map 行突出 + 开始执行 / 已关闭折叠行 / chips 深边框 / 窄屏双栏）----
    // v1.3.3 UI：行2 标签贪心折叠 —— 渲染后测量可用宽度，逐个放标签，放不下的隐藏进 +N（单行不换行）
    const fitAllTags = function () {
      if (typeof document === 'undefined') return
      document.querySelectorAll('.dsws-tags').forEach(function (tags) {
        const more = tags.querySelector('.dsws-more')
        if (!more) return
        const chips = Array.prototype.slice.call(tags.querySelectorAll('.dsws-chip:not(.dsws-more):not(.dsws-blocked)'))
        chips.forEach(function (c) { c.style.display = 'inline-flex' })
        more.style.display = 'inline-flex'
        const avail = tags.clientWidth
        const moreW = more.offsetWidth
        const gap = 3
        const room = avail - moreW - gap
        let used = 0, shown = 0
        chips.forEach(function (c, i) {
          const w = c.offsetWidth
          if (used + w <= room || i === 0) { c.style.display = 'inline-flex'; used += w + gap; shown++ }
          else c.style.display = 'none'
        })
        const hidden = chips.length - shown
        more.textContent = '+' + hidden
        more.style.display = hidden > 0 ? 'inline-flex' : 'none'
      })
    }
    // v1.3.3 UI：+N 弹窗 —— fixed 定位，基准 = 面板容器 rect（左右 clamp 不越界，上下自动翻转避让）
    const showPop = function (trig, host, labels, title) {
      if (typeof document === 'undefined') return
      const old = document.getElementById('dsws-pop')
      if (old && old.parentNode) old.parentNode.removeChild(old)
      const pop = document.createElement('div')
      pop.id = 'dsws-pop'
      pop.className = 'dsws-pop'
      const pt = document.createElement('div'); pt.className = 'pt'
      pt.textContent = tr('list.tagsCount', { n: labels.length })
      const pl = document.createElement('div'); pl.className = 'pl'
      labels.forEach(function (l) {
        const s = document.createElement('span')
        s.className = 'dsws-chip'
        s.style.background = hexA(l.color, 0.18) || 'rgba(188,140,255,.16)'
        s.style.color = l.color ? '#' + l.color : '#bc8cff'
        s.style.border = '1px solid ' + (darken(l.color, 0.16) || 'rgba(188,140,255,.6)')
        s.textContent = l.name
        pl.appendChild(s)
      })
      const ptitle = document.createElement('div'); ptitle.className = 'ptitle'
      ptitle.innerHTML = '<b>' + tr('list.popTitle') + '：</b>' + String(title || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      pop.appendChild(pt); pop.appendChild(pl); pop.appendChild(ptitle)
      document.body.appendChild(pop)
      const pr = host ? host.getBoundingClientRect() : { left: 8, right: window.innerWidth - 8, top: 8, bottom: window.innerHeight - 8 }
      const pad = 8
      const maxW = Math.max(120, pr.right - pr.left - pad * 2)
      pop.style.maxWidth = maxW + 'px'
      pop.style.display = 'block'
      const r = trig.getBoundingClientRect()
      const pw = pop.offsetWidth, ph = pop.offsetHeight
      let left = Math.max(pr.left + pad, Math.min(r.left, pr.right - pw - pad))
      let top = r.bottom + 10, flip = false
      if (top + ph > window.innerHeight - 8) { top = r.top - ph - 10; flip = true }
      if (top < 8) { top = r.bottom + 10; flip = false }
      if (top < pr.top + pad && !flip) { top = pr.top + pad }
      pop.style.left = left + 'px'
      pop.style.top = top + 'px'
      const caret = document.createElement('div'); caret.className = 'caret'
      const cx = r.left + r.width / 2 - left
      caret.style.left = Math.max(6, Math.min(cx - 5, pw - 16)) + 'px'
      caret.style.top = flip ? 'auto' : '-6px'
      caret.style.bottom = flip ? '-6px' : 'auto'
      if (flip) {
        caret.style.borderLeft = 'none'; caret.style.borderTop = 'none'
        caret.style.borderRight = '1px solid var(--dsw-alias-border-l2,#3a3f4a)'; caret.style.borderBottom = '1px solid var(--dsw-alias-border-l2,#3a3f4a)'
        caret.style.transform = 'rotate(225deg)'
      } else {
        caret.style.borderLeft = '1px solid var(--dsw-alias-border-l2,#3a3f4a)'; caret.style.borderTop = '1px solid var(--dsw-alias-border-l2,#3a3f4a)'
        caret.style.borderRight = 'none'; caret.style.borderBottom = 'none'
        caret.style.transform = 'rotate(45deg)'
      }
      pop.appendChild(caret)
      const close = function () { if (pop.parentNode) pop.parentNode.removeChild(pop); document.removeEventListener('mousedown', onDoc, true); document.removeEventListener('scroll', onScroll, true) }
      const onDoc = function (ev) { if (pop.contains(ev.target)) return; close() }
      const onScroll = function () { close() }
      document.addEventListener('mousedown', onDoc, true)
      document.addEventListener('scroll', onScroll, true)
      pop._close = close
    }
    const ListTab = ({ st, narrow }) => {
      // v1.3.3 UI：每次渲染后执行贪心折叠（含窗口/列宽变化后的重渲染）
      React.useLayoutEffect(function () { fitAllTags() })
      const issues = (st.snapshot && Array.isArray(st.snapshot.issues)) ? st.snapshot.issues : []
      const openIssues = issues.filter(function (x) { return x.state !== 'CLOSED' })
      const closedIssues = issues.filter(function (x) { return x.state === 'CLOSED' })
      // #374：多维排序 —— map 行恒置顶，map 组与普通组各自按所选维度排序；默认 更新时间↓（与现状一致）
      const sortIssues = function (arr) {
        const dir = st.sortDir === 'asc' ? 1 : -1
        return arr.slice().sort(function (a, b) {
          let c
          if (st.sortKey === 'number') { c = a.number - b.number; if (c !== 0) return dir * c }
          else if (st.sortKey === 'title') {
            c = String(a.title).toLowerCase().localeCompare(String(b.title).toLowerCase())
            if (c !== 0) return dir * c
          } else {
            c = String(a[st.sortKey] || '').localeCompare(String(b[st.sortKey] || ''))
            if (c !== 0) return dir * c
          }
          return a.number - b.number  // 同键兜底：编号升序（稳定）
        })
      }
      const isMapIssue = function (x) { return (x.labels || []).some(function (l) { return l.name === 'wayfinder:map' }) }
      const sortedMaps = sortIssues(openIssues.filter(isMapIssue))
      const sortedOpen = sortIssues(openIssues.filter(function (x) { return !isMapIssue(x) }))
      const closedSorted = sortIssues(closedIssues)
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
      // #375：全量 label（快照 labels 字段优先；旧快照无该字段降级 issue 统计）；配色并入 label 列表色
      const snapLabels = (st.snapshot && Array.isArray(st.snapshot.labels)) ? st.snapshot.labels : null
      if (snapLabels) snapLabels.forEach(function (l) { if (l.color && !colorOf[l.name]) colorOf[l.name] = l.color })
      const labelNames = snapLabels ? snapLabels.map(function (l) { return l.name }) : tagNames.slice()
      // 点击记忆双键排序：次数降序 → 最近点击降序 → 出现频次降序 → 名称序
      const sortedLabels = labelNames.slice().sort(function (a, b) {
        const ca = labelClicks[a], cb = labelClicks[b]
        const na = ca ? ca.n : 0, nb = cb ? cb.n : 0
        if (na !== nb) return nb - na
        const ta = ca ? ca.ts : 0, tb = cb ? cb.ts : 0
        if (ta !== tb) return tb - ta
        const fa = stat[a] || 0, fb = stat[b] || 0
        if (fa !== fb) return fb - fa
        return String(a).localeCompare(String(b))
      })
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
      // #374：状态过滤（全部/Open/阻塞/已关闭）与 label 过滤叠加
      // v1.3.3 T3：blocked 过滤真正实现 —— open 且存在 open 阻塞者（blockOf 命中）
      const showOpen = st.stateFilter !== 'closed'
      const showClosedList = st.stateFilter === 'closed'
      const byLabel = function (x) { return (x.labels || []).some(function (l) { return l.name === st.lblFilter }) }
      const openRows = sortedMaps.concat(sortedOpen)
      const openFiltered = st.lblFilter ? openRows.filter(byLabel) : openRows
      // v1.3.3 #6：阻塞 = 被占用口径（isOccupied：有 assignee 或存在 open 阻塞者）——与 KPI「占用 N」一致，
      //   用户点「阻塞」应筛出全部被占用项（此前 blockOf 只覆盖 map 子票的 blockedBy，漏掉 assignee 占用的）
      const filteredOpen = showOpen ? (st.stateFilter === 'blocked' ? openFiltered.filter(function (x) { return isOccupied(st, x) }) : openFiltered) : []
      const filteredClosed = showClosedList ? (st.lblFilter ? closedSorted.filter(byLabel) : closedSorted) : []
      const has = function (x, nm) { return (x.labels || []).some(function (l) { return l.name === nm }) }
      const findMap = function (num) { return (st.snapshot && st.snapshot.maps || []).find(function (m) { return m.number === num }) }
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
          // #375：点选即记点击记忆（次数 + 最近点击时间，双键排序）
          onClick: function (e) {
            e.stopPropagation()
            st.lblFilter = isAll ? null : ((st.lblFilter === nm) ? null : nm)
            if (!isAll) {
              const c = labelClicks[nm] || { n: 0, ts: 0 }
              labelClicks[nm] = { n: c.n + 1, ts: Date.now() }
              saveLabelClicks()
            }
            emit(st)
          },
          style: {
            cursor: 'pointer', marginRight: 4, marginBottom: 3, fontSize: 10,
            background: isAll ? 'rgba(255,255,255,.08)' : (hexA(c, 0.18) || 'rgba(188,140,255,.16)'),
            color: isAll ? 'var(--dsw-alias-label-secondary,#a1a1aa)' : (c ? '#' + c : '#bc8cff'),
            border: '1px solid ' + (on ? selColor : borderColor),
          },
        }, nm)
      }
      const copyUrl = function (x) { copyText(st, 'https://github.com/' + repoStr(st) + '/issues/' + x.number, tr('toast.copiedLink', { n: x.number })) }
      // v14-4：行级动作按 label 四选一（诊断/修复/讨论/执行），全部预填输入框；
      // v19：共享 mkRowAction（列表与 map 详情同逻辑，按钮色动态取 label 配置色）；v14-3 按钮 80%；v14-19 窄屏折叠为纯图标
      // v1.3.3 UI 定稿（用户逐版确认）：两行结构 · 卡片风（C）· 编号/map 竖排（idcol）·
      //   行1 = 编号(上)+map徽章(下) 竖排 + 标题(占满,限2行) + 迷你圆环进度(右上)；
      //   行2 = 标签单行贪心折叠（宽多窄少,最少1个,放不下进 +N 弹窗）+ 按钮组（执行/完成/新会话常显,复制/外链 hover）
      //   +N 弹窗：fixed 定位,基准=面板容器,clamp 左右不越界,内容完整可见（用户验收 A 方案）
      const ringOf = function (stats) {
        const total = stats.total || 0, closed = stats.closed || 0
        const pct = total ? Math.round(closed / total * 100) : 0
        const C = 2 * Math.PI * 7
        const off = C * (1 - pct / 100)
        const color = pct >= 100 ? '#4ade80' : '#bc8cff'
        return h('span', { className: 'dsws-ring' }, [
          h('svg', { width: 18, height: 18, viewBox: '0 0 18 18' }, [
            h('circle', { cx: 9, cy: 9, r: 7, fill: 'none', stroke: 'rgba(255,255,255,.12)', strokeWidth: 2.4 }),
            h('circle', { cx: 9, cy: 9, r: 7, fill: 'none', stroke: color, strokeWidth: 2.4, strokeLinecap: 'round', strokeDasharray: String(C), strokeDashoffset: String(off) }),
          ]),
          h('span', { className: 'dsws-ring-txt', style: { color: color } }, closed + '/' + total),
        ])
      }
      const issueRow = function (x, isOpen, narrow) {
        const isMap = has(x, 'wayfinder:map')
        const mapObj = isMap ? findMap(x.number) : null
        // v15-26：被阻塞判定（open 阻塞者）→ 隐藏动作按钮 + 红色「被阻塞」标签（点击跳所属 map 详情）
        const blk = blockOf[x.number]
        const blocked = !!(blk && blk.by && blk.by.length)
        // v1.3.3 #8：map 行完成态 —— 子票全关（total>0 且 closed===total）→ 主按钮切「完成」（绿），注入收尾确认 prompt
        const mapDone = !!(isMap && mapObj && mapObj.stats && mapObj.stats.total > 0 && mapObj.stats.closed === mapObj.stats.total)
        // v1.3.3 UI：全部标签渲染（渲染后贪心折叠，放不下的隐藏进 +N；+N 弹窗显示全部）
        const labels = x.labels || []
        const allNames = labels.map(function (l) { return l.name }).join('、')
        const openPop = function (e) {
          e.stopPropagation()
          const trig = e.currentTarget
          const host = trig.closest('.dsws-panel') || trig.closest('[data-dsws-host]')
          showPop(trig, host, labels, x.title)
        }
        return h('div', {
          key: x.number,
          className: 'dsws-aggrow',
          onClick: function () { if (isMap && mapObj) { st.activeMap = x.number; emit(st) } },
          title: (isMap && mapObj) ? tr('list.mapTitle') : undefined,
          style: isMap ? { cursor: 'pointer', borderLeft: '3px solid #c084fc', background: 'rgba(188,140,255,.07)' } : undefined,
        }, [
          // 行1：idcol 竖排（编号上 map 徽章下）+ 标题 + 圆环进度
          h('div', { style: { display: 'flex', alignItems: 'flex-start', gap: 6, width: '100%' } }, [
            h('span', { className: 'dsws-idcol' }, [
              isMap ? h('span', { className: 'dsws-chip dsws-chip-m', style: { fontSize: 11, fontWeight: 600, lineHeight: 1.7, padding: '0 8px' } }, [Ic({ n: 'map', size: 11 }), h('span', null, tr('list.mapChip'))]) : null,
              h('span', { style: { color: 'var(--dsw-alias-label-caption,#8b8b95)', fontSize: 11, lineHeight: 1.6 } }, '#' + x.number),
            ]),
            h('span', { className: 'dsws-tt-wrap', style: { flex: 1, fontWeight: isMap ? 600 : undefined, color: isOpen ? undefined : 'var(--dsw-alias-label-secondary,#a1a1aa)' }, title: x.title }, x.title),
            (isMap && mapObj && mapObj.stats) ? ringOf(mapObj.stats) : null,
            !isOpen ? h('span', { className: 'dsws-chip', style: { fontSize: 10, marginRight: 0, flex: 'none', background: 'rgba(139,139,149,.12)', color: '#8b8b95', border: '1px solid rgba(139,139,149,.35)' } }, [Ic({ n: 'check', size: 9 }), h('span', null, tr('map.subClosed'))]) : null,
          ]),
          // 行2：标签贪心折叠（单行不换行）+ 按钮组（常显）
          h('div', { style: { marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, width: '100%' } }, [
            h('div', { className: 'dsws-tags', 'data-dsws-labels': JSON.stringify(labels.map(function (l) { return l.name })) }, [
              labels.map(function (l, i) {
                return h('span', { key: i, className: 'dsws-chip', style: { fontSize: 10, background: hexA(l.color, 0.18) || 'rgba(188,140,255,.16)', color: l.color ? '#' + l.color : '#bc8cff', border: '1px solid ' + (darken(l.color, 0.16) || 'rgba(188,140,255,.6)') } }, l.name)
              }),
              labels.length > 0 ? h('span', { key: 'more', className: 'dsws-chip dsws-more', onClick: openPop, title: tr('list.tagsTitle', { names: allNames }) }, '+0') : null,
              blocked ? h('span', { key: 'blk', className: 'dsws-chip dsws-blocked', onClick: function (e) { e.stopPropagation(); openBlocked(blk) }, title: tr('list.blockedTitle', { by: blk.by.map(function (b) { return '#' + b }).join('、') }), style: { fontSize: 10, background: 'rgba(248,113,113,.16)', color: '#f87171', border: '1px solid rgba(248,113,113,.55)', cursor: 'pointer' } }, [Ic({ n: 'lock', size: 10 }), h('span', null, tr('list.blocked'))]) : null,
            ]),
            h('div', { style: { display: 'flex', alignItems: 'center', gap: 3, flex: 'none', marginLeft: 'auto' } }, [
              isOpen && !blocked ? h('div', { style: { display: 'flex', gap: 3, alignItems: 'center', flex: 'none' } }, [
                mapDone
                  ? h('button', { className: 'dsws-btn primary' + (narrow ? ' narrow-icon' : ''), title: tr('map.doneTitle'), onClick: function (e) {
                      e.stopPropagation()
                      const text = COMPLETE_PROMPT
                        .split('{n}').join(String(x.number || ''))
                        .split('{total}').join(String(mapObj.stats.total))
                        .split('{closed}').join(String(mapObj.stats.closed))
                      inject(st, text)
                    }, style: { display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 6px', fontSize: 11, flex: 'none', background: '#3fb950', borderColor: 'transparent', color: '#0c1a10', fontWeight: 600 } }, [Ic({ n: 'check', size: 10 }), narrow ? null : h('span', null, tr('act.done'))])
                  : mkRowAction(st, x, narrow, colorOf),
                h('button', { className: 'dsws-btn primary' + (narrow ? ' narrow-icon' : ''), onClick: function (e) { e.stopPropagation(); openInNewSession(st, x) }, title: tr('list.newSessionLabel'), style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 6px', fontSize: 11, flex: 'none', marginLeft: 4, background: mapDone ? '#3fb950' : actionColorOf(x, colorOf), borderColor: 'transparent', color: mapDone ? '#0c1a10' : (isLightHex(actionColorOf(x, colorOf)) ? '#140a1e' : '#ffffff') } }, [Ic({ n: 'external-link', size: 10 }), narrow ? null : h('span', null, tr('list.newSessionLabel'))]),
              ]) : null,
              isOpen ? h('div', { className: 'dsws-aux', style: { display: 'flex', gap: 2, alignItems: 'center', flex: 'none' } }, [
                // v1.3.3：复制/外链图标增大 11 → 13
                h('button', { className: 'dsws-btn ghost', onClick: function (e) { e.stopPropagation(); copyUrl(x) }, title: tr('list.copyLinkTitle'), style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '2px 4px', flex: 'none' } }, Ic({ n: 'clipboard', size: 13 })),
                h('a', { className: 'dsws-btn ghost', title: tr('list.openInGithubTitle', { n: x.number }), href: 'https://github.com/' + repoStr(st) + '/issues/' + x.number, target: '_blank', rel: 'noreferrer', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', padding: '2px 4px', flex: 'none' } }, Ic({ n: 'link', size: 13 })),
              ]) : null,
            ]),
          ]),
        ])
      }
      const kpi = (num, lab, icon, color) => h('div', { style: { display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, [Ic({ n: icon, size: 11, color: color }), h('span', null, String(num) + ' ' + lab)])
      return h('div', null, [
        // KPI 行 + 环境提示（v18-30：可接/占用 = 列表 open issue 口径）
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4, flexWrap: 'wrap', position: 'relative' } }, [
          kpi(frontierCount(st), tr('list.kpi.takeable'), 'target', '#4ade80'),
          kpi(occCount(st), tr('list.kpi.occupied'), 'lock', '#f0883e'),
          kpi(closedIssues.length, tr('list.kpi.closed'), 'check', '#52525b'),
          h('span', { style: { flex: 1 } }),
          // T2 #2：刷新按钮已上移至 OverlayPanel tabs 行（L1932）
        ]),
        nBad > 0 ? h('div', { className: 'dsws-banner bad', onClick: function () { st.tab = 'checks'; emit(st) } }, [
          Ic({ n: 'alert', size: 13 }),
          h('span', null, tr('list.envWarn', { n: nBad })),
        ]) : null,
        // #374/#375：状态过滤 + 排序 + label 过滤 chips（全部小号紧凑同排，窄屏换行不增高；展开态点选 label 不收起）
        h('div', { style: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0, marginBottom: 6 } }, [
          ['all', 'open', 'closed', 'blocked'].map(function (k) {
            const on = st.stateFilter === k
            return h('span', { key: 'stf-' + k, className: 'dsws-chip', onClick: function (e) {
              e.stopPropagation(); st.stateFilter = k; listPrefs.stateFilter = k; saveListPrefs(); emit(st)
            }, style: { cursor: 'pointer', marginRight: 4, marginBottom: 3, fontSize: 10, background: on ? 'rgba(188,140,255,.18)' : 'rgba(255,255,255,.06)', color: on ? '#c084fc' : 'var(--dsw-alias-label-secondary,#a1a1aa)', border: '1px solid ' + (on ? 'rgba(188,140,255,.6)' : 'rgba(255,255,255,.15)') } }, tr('list.state.' + k))
          }),
          h('span', { style: { width: 1, height: 12, background: 'var(--dsw-alias-border-l1,#2a2d35)', margin: '0 4px 3px', flex: 'none' } }),
          ['updatedAt', 'createdAt', 'number', 'title'].map(function (k) {
            const on = st.sortKey === k
            const arrow = on ? (st.sortDir === 'asc' ? '↑' : '↓') : ''
            return h('span', { key: 'srt-' + k, className: 'dsws-chip', onClick: function (e) {
              e.stopPropagation()
              if (st.sortKey === k) { st.sortDir = st.sortDir === 'asc' ? 'desc' : 'asc' }
              else { st.sortKey = k; st.sortDir = (k === 'title') ? 'asc' : 'desc' }
              listPrefs.sortKey = st.sortKey; listPrefs.sortDir = st.sortDir; saveListPrefs(); emit(st)
            }, style: { cursor: 'pointer', marginRight: 4, marginBottom: 3, fontSize: 10, background: on ? 'rgba(88,166,255,.16)' : 'rgba(255,255,255,.06)', color: on ? '#58a6ff' : 'var(--dsw-alias-label-secondary,#a1a1aa)', border: '1px solid ' + (on ? 'rgba(88,166,255,.55)' : 'rgba(255,255,255,.15)') } }, tr('list.sort.' + k) + arrow)
          }),
          h('span', { style: { width: 1, height: 12, background: 'var(--dsw-alias-border-l1,#2a2d35)', margin: '0 4px 3px', flex: 'none' } }),
          chip(tr('list.all'), false, st.lblFilter === null, true),
          // #405：filter row 默认可见数 9 → 4（与 per-row 一致）；+N 触发条件 + 数字同步
          (st.expLabels ? sortedLabels : sortedLabels.slice(0, 4)).map(function (nm) { return chip(nm, true, st.lblFilter === nm, false) }),
          (!st.expLabels && sortedLabels.length > 4) ? h('span', { key: 'lbl-more', className: 'dsws-chip', onClick: function (e) { e.stopPropagation(); st.expLabels = true; emit(st) }, title: tr('list.tagsTitle', { names: sortedLabels.join('、') }), style: { fontSize: 10, marginRight: 4, marginBottom: 3, background: 'rgba(188,140,255,.1)', color: '#bc8cff', border: '1px dashed rgba(188,140,255,.55)', cursor: 'pointer' } }, '+' + (sortedLabels.length - 4)) : null,
          st.expLabels ? h('span', { key: 'lbl-less', className: 'dsws-chip', onClick: function (e) { e.stopPropagation(); st.expLabels = false; emit(st) }, title: tr('list.tagsCollapseTitle'), style: { fontSize: 10, marginRight: 4, marginBottom: 3, background: 'rgba(255,255,255,.06)', color: 'var(--dsw-alias-label-caption,#8b8b95)', border: '1px dashed rgba(255,255,255,.3)', cursor: 'pointer' } }, tr('list.collapse')) : null,
        ]),
        // T3 #5：加载遮罩（替代单行文本，全屏遮罩 + 转圈 + 禁点）
        // v1.3.3 修复：刷新中（refreshing）只显示全面板刷新遮罩，不叠加本加载遮罩（用户实测双 loading 叠加）
        st.snapMode === 'loading' && !st.refreshing ? h('div', { className: 'dsws-loading-shade', style: { position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(2px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, zIndex: 5, pointerEvents: 'auto' } }, [
          h('div', { className: 'dsws-spinner' }),
          h('span', { style: { fontSize: 12, color: '#e6edf3' } }, tr('list.loading')),
        ]) : null,
        st.snapMode === 'err' ? h('div', { style: { color: '#f87171', fontSize: 12, padding: '14px 0', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 } }, [Ic({ n: 'alert', size: 12 }), h('span', null, tr('list.errFull', { err: st.snapError }))]) : null,
        // #374：状态过滤渲染 —— open 主体 / closed 列表 / 「全部」态保留已关闭折叠行
        showOpen ? (filteredOpen.length === 0 ? h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', padding: '14px 0', textAlign: 'center' } }, tr('list.none')) : filteredOpen.map(function (x) { return issueRow(x, true, narrow) })) : null,
        showClosedList ? (filteredClosed.length === 0 ? h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', padding: '14px 0', textAlign: 'center' } }, tr('list.none')) : filteredClosed.map(function (x) { return issueRow(x, false, narrow) })) : null,
        // v14-4⑤：列表底部「已关闭 (N)」折叠行（仅「全部」状态显示；默认收起，只占一行，展开可见）
        (st.stateFilter === 'all' && closedIssues.length) ? h('details', { style: { marginTop: 8 } }, [
          h('summary', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, padding: '4px 2px', userSelect: 'none' } }, [
            Ic({ n: 'check', size: 11 }),
            h('span', null, tr('list.closedN', { n: closedIssues.length })),
          ]),
          h('div', null, closedSorted.map(function (x) { return issueRow(x, false, narrow) })),
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
        return h('div', { key: sk.name, title: tr('skilldesc.' + sk.name), onClick: function () { inject(st, '/' + sk.name) }, style: { position: 'absolute', left: x - 15, top: y - 15, width: 30, height: 30, borderRadius: '50%', border: filled ? '2px solid #4ade80' : '2px solid #52525b', background: filled ? 'rgba(74,222,128,.15)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9.5, cursor: 'pointer', color: filled ? '#4ade80' : '#8b8b95', lineHeight: 1.2, textAlign: 'center' } }, sk.name.length > 4 ? sk.name.slice(0, 4) + '…' : sk.name)
      })
      return h('div', null, [
        h('div', { style: { position: 'relative', width: 220, height: 220, margin: '0 auto 6px' } }, [
          h('div', { onClick: function () { inject(st, '/' + center) }, title: tr('skill.centerTitle', { skill: center }), style: { position: 'absolute', left: cx - 30, top: cy - 30, width: 60, height: 60, borderRadius: '50%', background: 'rgba(188,140,255,.18)', border: '2px solid #c084fc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#c084fc', cursor: 'pointer', textAlign: 'center', lineHeight: 1.3 } }, '/' + center),
          nodes,
        ]),
        h('div', { style: { fontSize: 11, color: 'var(--dsw-alias-label-caption,#8b8b95)', textAlign: 'center', marginBottom: 8 } }, tr('skill.centerRing')),
        h('div', { className: 'dsws-grp' }, [Ic({ n: 'compass', size: 12 }), h('span', null, tr('skill.all'))]),
        list.map(function (sk) {
          const on = rec.indexOf(sk.name) >= 0
          return h('div', { key: sk.name, className: 'dsws-skill', style: on ? { background: 'rgba(188,140,255,.12)', borderRadius: 6 } : null }, [
            Dot({ level: sk.level }),
            h('div', { className: 'dsws-tt' }, [
              h('div', { className: 'dsws-tt-name', style: on ? { color: '#c084fc' } : null }, [h('span', null, '/' + sk.name), on ? Ic({ n: 'star', size: 11, color: '#c084fc' }) : null]),
              h('div', { className: 'dsws-tt-sub dsws-ellip', title: tr('skilldesc.' + sk.name) }, tr('skilldesc.' + sk.name)),
            ]),
            h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + sk.name) } }, tr('act.load')),
          ])
        }),
      ])
    }

    const SkillsTab = ({ st }) => {
      const groups = compute(st)
      let rec = []
      let recTitle = tr('skill.generic')
      if (st.activeMap !== null) {
        const g = groups.find(function (x) { return x.m.number === st.activeMap })
        if (g && /research/.test(g.m.notes)) rec = ['research']
        if (g && /grill/.test(g.m.notes)) rec = ['grilling', 'domain-modeling']
        recTitle = tr('skill.notes', { m: g.m.title })
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
          h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + sk.name) } }, tr('act.load')),
        ])
      })
      const head = h('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 } }, [
        h('div', { className: 'dsws-grp', style: { margin: 0 } }, [Ic({ n: 'compass', size: 12 }), h('span', null, recTitle)]),
        h('span', { style: { flex: 1 } }),
        h('span', { className: 'dsws-seg' + (st.skillView === 'list' ? ' on' : ''), onClick: function () { st.skillView = 'list'; emit(st) }, style: { fontSize: 11 } }, tr('skill.list')),
        h('span', { className: 'dsws-seg' + (st.skillView === 'ring' ? ' on' : ''), onClick: function () { st.skillView = 'ring'; emit(st) }, style: { fontSize: 11 } }, tr('skill.ring')),
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
      // #373：hint 支持两种形态 —— URL（可打开/复制）或 /命令（「用 /xxx 处理」按钮，保留兼容）
      const actBtn = (c) => {
        const hint = c.hint || ''
        if (/^https?:\/\//i.test(hint)) {
          return h('div', { style: { display: 'flex', gap: 6, alignItems: 'center' } }, [
            h('a', { href: hint, target: '_blank', rel: 'noreferrer', className: 'dsws-btn', style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'link', size: 11 }), h('span', null, tr('env.openUrl'))]),
            h('button', { className: 'dsws-btn', onClick: function () { copyText(st, hint, tr('toast.copied')) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'clipboard', size: 11 }), h('span', null, tr('env.copyUrl'))]),
          ])
        }
        const m = hint.match(/\/([a-z0-9-]+)/i)
        if (!m) return null
        return h('button', { className: 'dsws-btn', onClick: function () { inject(st, '/' + m[1]) } }, tr('skill.treat', { s: m[1] }))
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
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 4 } }, [Ic({ n: 'gear', size: 12 }), h('span', null, tr('env.title', { n: envLabel(st) }))]),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', disabled: st.checking, onClick: function () { refreshAll(st) }, style: { fontSize: 11, padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
            Ic({ n: 'refresh', size: 11 }),
            h('span', null, st.checking ? tr('env.checking') : tr('env.recheck')),
          ]),
        ]),
        st.checksMode === 'err' ? h('div', { className: 'dsws-banner bad', style: { cursor: 'default' } }, [Ic({ n: 'alert', size: 13 }), h('span', null, tr('env.failFull', { err: st.checksError }))]) : null,
        st.checksMode === 'loading' ? h('div', { style: { color: 'var(--dsw-alias-label-secondary,#a1a1aa)', fontSize: 12, marginBottom: 6 } }, tr('env.detecting')) : null,
        bad.length ? h('div', { className: 'dsws-banner bad', style: { cursor: 'default' } }, [Ic({ n: 'alert', size: 13 }), h('span', null, tr('env.missingBanner', { n: bad.length }))]) : null,
        grp(tr('env.missing'), '#f87171', bad),
        grp(tr('env.partial'), '#f59e0b', warn),
        grp(tr('env.ready'), '#4ade80', ok),
      ])
    }

    // ---- 5.8b 右侧停靠（details 槽位 · 三视图完整内容；开合/拖拽/宽度记忆由壳管理）----
    // 契约：details 槽 = 壳右侧第三列（AppFrame grid），scope session；关闭 = ctx.layout.closeDetails()
    //   （占位者 props 亦注入 closeDetails）；宽度 300-520px 可拖拽；关闭时子树不卸载（状态保留）。
    const DetailsDock = (props) => {
      const s = useStore(props && props.sessionId)
      const layoutSvc = ctx.get('layout')
      const dockRef = React.useRef(null)
      const [dw, setDw] = React.useState(460)
      // 列宽感知：details 列 300-520px；窄于 380 时动作按钮折叠为纯图标（与悬浮面板同阈值）
      React.useEffect(function () {
        if (!dockRef.current) return
        const el = dockRef.current
        const ro = new ResizeObserver(function (entries) {
          try { setDw(entries[0].contentRect.width) } catch (e) { /* 忽略 */ }
        })
        ro.observe(el)
        return function () { try { ro.disconnect() } catch (e) { /* 忽略 */ } }
      }, [])
      // 初始数据（与状态栏同款：快照 + 环境检查）；壳保持子树常挂载，后续刷新走「更新」/停靠段
      React.useEffect(function () { loadSnapshot(s, false); loadChecks(s, false) }, [])
      const closeDock = function () {
        if (props && typeof props.closeDetails === 'function') props.closeDetails()
        else if (layoutSvc && typeof layoutSvc.closeDetails === 'function') layoutSvc.closeDetails()
      }
      const groups = compute(s)
      const active = s.activeMap !== null ? groups.find(function (x) { return x.m.number === s.activeMap }) : null
      const narrow = dw < 380
      const tabBtn = (id, icon, label) => h('button', { className: 'dsws-tab' + (s.tab === id ? ' on' : ''), onClick: function () { s.tab = id; emit(s) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
        Ic({ n: icon, size: 12 }),
        h('span', null, label),
      ])
      return h('div', { ref: dockRef, 'data-dsws-host': '1', className: narrow ? 'dsws-narrow' : undefined, style: { position: 'relative', display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'var(--dsw-font-family)', fontSize: 12, color: 'var(--dsw-alias-label-primary,#e6edf3)', background: 'var(--dsw-alias-bg-layer-1,#10131a)' } }, [
        // 头部（标题 + 关闭）：横线不放在这行，下移到标签行下方与对话/轨迹对齐
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 6, padding: '10px 12px 6px', flex: 'none' } }, [
          Icon({ scheme: 'compass', size: 15 }),
          h('span', { style: { fontWeight: 600, fontSize: 13, flex: 'none' } }, 'Waystation'),
          // v1.5 T7：仓库身份组件 —— 当前检测到的 git 仓库（owner/name），点击打开 GitHub
          (s.snapshot && s.snapshot.repo) ? h('a', { href: 'https://github.com/' + s.snapshot.repo.owner + '/' + s.snapshot.repo.name, target: '_blank', rel: 'noreferrer', title: tr('panel.repoTitle'), style: { textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', border: '1px solid var(--dsw-alias-border-l1,#2a2d35)', borderRadius: 6, padding: '1px 7px', maxWidth: narrow ? 90 : 170, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 'none' } }, [
            Ic({ n: 'link', size: 10 }),
            h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis' } }, s.snapshot.repo.owner + '/' + s.snapshot.repo.name),
          ]) : null,
          h('span', { style: { flex: 1 } }),
          // v1.5 T6：「新增 wayfinder」按钮（所有视图可见）—— 注入 /wayfinder + 仓库信息 + 需求引导
          h('button', { className: 'dsws-btn ghost', title: tr('panel.newWayfinderTitle'), onClick: function () { inject(s, newWayfinderText(s)) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', fontSize: 11, flex: 'none', color: '#c084fc' } }, [
            Ic({ n: 'map', size: 11 }),
            h('span', null, tr('panel.newWayfinder')),
          ]),
          h('button', { className: 'dsws-btn ghost', title: tr('panel.closeTitle'), onClick: closeDock, style: { display: 'inline-flex', alignItems: 'center', padding: '2px 6px', fontSize: 11 } }, Ic({ n: 'x', size: 12 })),
        ]),
        // 标签行下沿 = 与对话/轨迹一致的横线；右侧：刷新按钮 + 版本号（v1.3.3）
        h('div', { className: 'dsws-tabs', style: { padding: '0 12px 7px', borderBottom: '1px solid var(--dsw-alias-border-l1,#2a2d35)', flex: 'none', display: 'flex', alignItems: 'center', gap: 4 } }, [
          tabBtn('list', 'list', tr('panel.tabList')),
          tabBtn('skills', 'compass', tr('panel.tabSkills')),
          tabBtn('checks', 'gear', tr('panel.tabChecks')),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn', title: tr('list.refresh'), onClick: function () { refreshAll(s) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', fontSize: 11, flex: 'none' } }, [Ic({ n: 'refresh', size: 11 }), h('span', null, tr('list.refresh'))]),
          h('span', { style: { fontSize: 9, color: 'var(--dsw-alias-label-caption,#8b8b95)', flex: 'none', fontVariantNumeric: 'tabular-nums' } }, DSW_VERSION),
        ]),
        h('div', { className: 'dsws-body', style: { flex: 1, overflowY: 'auto', padding: '10px 12px' } }, [
          s.tab === 'list' ? (active ? h(MapDetail, { st: s, g: active }) : h(ListTab, { st: s, narrow: narrow })) : null,
          s.tab === 'skills' ? h(SkillsTab, { st: s }) : null,
          s.tab === 'checks' ? h(ChecksTab, { st: s }) : null,
        ]),
        // v26：刷新遮罩（与悬浮面板同款；期间禁点）
        s.refreshing ? h('div', { className: 'dsws-shade' }, [
          h('div', { className: 'dsws-spinner' }),
          h('span', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, tr('panel.refreshing')),
        ]) : null,
        s.notice ? h('div', { className: 'dsws-note', style: { display: 'flex', alignItems: 'center', gap: 6 } }, [
          Ic({ n: noticeIcon(s.notice.kind), size: 13, color: NOTICE_COLOR[s.notice.kind] || '#4ade80' }),
          h('span', null, s.notice.text),
        ]) : null,
      ])
    }

    // ---- 5.8 主面板（可拖动 · 8 向缩放 · 三视图 · v14 跟随当前会话 + 刷新遮罩）----
    const OverlayPanel = (props) => {
      const cur = props.useSessions((x) => x.current)
      const s = useStore(cur)
      const panelRef = React.useRef(null)
      // #376：加载由 openPanel 统一分派（未就绪/过期 force，新鲜直接展示）；此处不再重复加载
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
            h('span', { className: 'dsws-ellip', title: repoStr(s) }, s.snapMode === 'err' ? tr('panel.snapErr') : s.snapMode === 'loading' ? tr('panel.loading') : repoStr(s)),
          ]),
          h('span', { style: { flex: 1 } }),
          h('button', { className: 'dsws-btn ghost', title: tr('panel.closeTitle'), onClick: function () { s.open = false; emit(s) }, style: { display: 'inline-flex', alignItems: 'center' } }, Ic({ n: 'x', size: 12 })),
        ]),
                h('div', { className: 'dsws-tabs', style: { display: 'flex', alignItems: 'center', gap: 4 } }, [
          tabBtn('list', 'list', tr('panel.tabList')),
          tabBtn('skills', 'compass', tr('panel.tabSkills')),
          tabBtn('checks', 'gear', tr('panel.tabChecks')),
          h('span', { style: { flex: 1 } }),
          // T2 #2：刷新按钮上移至 tabs 行 · 紧贴环境检查右边（用户需求：列表 / 技能 / 环境检查 / 刷新）
          h('button', { className: 'dsws-btn', title: tr('list.refresh'), onClick: function () { refreshAll(s) }, style: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', fontSize: 11, flex: 'none' } }, [Ic({ n: 'refresh', size: 11 }), h('span', null, tr('list.refresh'))]),
          h('span', { style: { fontSize: 9, color: 'var(--dsw-alias-label-caption,#8b8b95)', flex: 'none', fontVariantNumeric: 'tabular-nums' } }, DSW_VERSION),
        ]),
        h('div', { className: 'dsws-body', onMouseDown: onBodyDown }, [
          s.tab === 'list' ? (active ? h(MapDetail, { st: s, g: active }) : h(ListTab, { st: s, narrow: narrow })) : null,
          s.tab === 'skills' ? h(SkillsTab, { st: s }) : null,
          s.tab === 'checks' ? h(ChecksTab, { st: s }) : null,
        ]),
        h('div', { className: 'dsws-rz dsws-rz-n', onMouseDown: onResizeDown('n'), title: tr('rz.n') }),
        h('div', { className: 'dsws-rz dsws-rz-s', onMouseDown: onResizeDown('s'), title: tr('rz.s') }),
        h('div', { className: 'dsws-rz dsws-rz-e', onMouseDown: onResizeDown('e'), title: tr('rz.e') }),
        h('div', { className: 'dsws-rz dsws-rz-w', onMouseDown: onResizeDown('w'), title: tr('rz.w') }),
        h('div', { className: 'dsws-rz dsws-rz-ne', onMouseDown: onResizeDown('ne'), title: tr('rz.ne') }),
        h('div', { className: 'dsws-rz dsws-rz-nw', onMouseDown: onResizeDown('nw'), title: tr('rz.nw') }),
        h('div', { className: 'dsws-rz dsws-rz-se', onMouseDown: onResizeDown('se'), title: tr('rz.se') }),
        h('div', { className: 'dsws-rz dsws-rz-sw', onMouseDown: onResizeDown('sw'), title: tr('rz.sw') }),
        // v14-17：手动刷新遮罩（期间禁点）
        s.refreshing ? h('div', { className: 'dsws-shade' }, [
          h('div', { className: 'dsws-spinner' }),
          h('span', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)' } }, tr('panel.refreshing')),
        ]) : null,
        s.notice ? h('div', { className: 'dsws-note', style: { display: 'flex', alignItems: 'center', gap: 6 } }, [
          Ic({ n: noticeIcon(s.notice.kind), size: 13, color: NOTICE_COLOR[s.notice.kind] || '#4ade80' }),
          h('span', null, s.notice.text),
        ]) : null,
      ])
    }

    // ---- 5.9 配置页（v25 · settings.plugins.tab「Waystation」：功能配置 + 动作模板编辑器）----
    // 开始模板（前缀开关 + execute 模板）/ 动作模板编辑器（其余 6 动作）
    // T3：模板名/描述在渲染时 tr('tpl.name.*')/tr('tpl.desc.*')（此处保留中文静态表供默认文案参考）
    const TPL_NAMES = {
      diagnose: '诊断', fix: '修复', discuss: '讨论', handoff1: '交接第一击', handoff2: '交接第二击', fixate: '沉淀',
    }
    const TPL_DESC = {
      diagnose: 'needs-triage 票的行级动作',
      fix: 'bug 票的行级动作',
      discuss: 'wayfinder:grilling 票的行级动作',
      handoff1: '生成交接文档（含时间戳，两击文件名一致）',
      handoff2: '读取交接文档',
      fixate: '零丢失快照 prompt',
    }
    const TPL_EDIT_IDS = ['diagnose', 'fix', 'discuss', 'handoff1', 'handoff2', 'fixate']  // execute 在「开始模板」节
    const PREVIEW_VALUES = { url: 'https://github.com/FeatherHunter/SKILLS/issues/365', number: '365', title: tr('cfg.previewTitle'), ts: '20260814-172113', file: '20260814-172113.md' }
    const SettingsPage = (props) => {
      const [openIn, setOpenIn] = React.useState(cfg.openIn || 'dock')
      const [openInNote, setOpenInNote] = React.useState(false)
      const [wf, setWf] = React.useState(cfg.withWayfinder)
      const [tpls, setTpls] = React.useState(function () {
        const o = {}
        o.execute = templates.execute || ''
        TPL_EDIT_IDS.forEach(function (id) { o[id] = templates[id] || '' })
        return o
      })
      const [saved, setSaved] = React.useState(false)
      const [errs, setErrs] = React.useState([])
      const [resetNote, setResetNote] = React.useState(null)
      const taRefs = React.useRef({})
      // v1.4.1：打开位置即时生效 —— seg 点击即写入 cfg + localStorage + 广播（无需滚到底部点保存全部）
      const pickOpenIn = function (v) {
        setOpenIn(v)
        cfg.openIn = v
        saveCfg()
        broadcastCfg()
        setOpenInNote(true)
        if (timer !== undefined) timer.timeout(function () { setOpenInNote(false) }, 2600)
      }
      // v1.3.3 T1：模板 textarea 自适应高度（内容全展开 · 无内层滚动 · 最外层滑动）
      const autoGrowTa = function (el) {
        if (!el) return
        el.style.height = 'auto'
        el.style.height = (el.scrollHeight + 2) + 'px'
      }
      // 校验全部 7 个模板（生效文本 = 自定义 || 默认）
      const validateAll = function (executeText) {
        const errList = []
        const check = function (id, text) {
          const v = validateTemplate(id, text || TPL_DEFAULT[id] || '')
          if (!v.ok) {
            const bits = []
            if (v.missing.length) bits.push(tr('tpl.missing', { list: v.missing.map(function (n) { return '{' + n + '}' }).join('、') }))
            if (v.unknown.length) bits.push(tr('tpl.unknown', { list: v.unknown.map(function (n) { return '{' + n + '}' }).join('、') }))
            errList.push('「' + tr('tpl.name.' + id) + '」' + bits.join('；'))
          }
        }
        check('execute', executeText)
        TPL_EDIT_IDS.forEach(function (id) { check(id, tpls[id]) })
        return errList
      }
      const save = function () {
        const errList = validateAll(custom)
        if (errList.length) { setErrs(errList); return }
        setErrs([])
        cfg.openIn = openIn
        cfg.withWayfinder = wf
        templates.execute = custom
        TPL_EDIT_IDS.forEach(function (id) { templates[id] = tpls[id] })
        saveCfg(); saveTemplates(); broadcastCfg()
        setSaved(true)
        if (timer !== undefined) timer.timeout(function () { setSaved(false) }, 2000)
      }
      const setTpl = function (id, val) { setTpls(function (p) { const o = Object.assign({}, p); o[id] = val; return o }) }
      const resetExecute = function () { setTpl('execute', ''); setErrs([]) }
      const resetTpl = function (id) { setTpl(id, ''); setErrs([]) }
      // 页面级恢复全部默认（T1 规格 §5：清空 = 注入时走内置默认文本）
      const resetAll = function () {
        const o = {}
        o.execute = ''
        TPL_EDIT_IDS.forEach(function (id) { o[id] = '' })
        setTpls(o)
        setWf(true)
        setErrs([])
      }
      // 点击占位符 chip 在光标处插入
      const insertPh = function (id, name) {
        const ta = taRefs.current[id]
        const cur = tpls[id] || ''
        if (!ta) { setTpl(id, cur + '{' + name + '}'); return }
        const start = (ta.selectionStart != null) ? ta.selectionStart : cur.length
        const end = (ta.selectionEnd != null) ? ta.selectionEnd : cur.length
        const next = cur.slice(0, start) + '{' + name + '}' + cur.slice(end)
        setTpl(id, next)
        const pos = start + name.length + 2
        setTimeout(function () { try { ta.focus(); ta.setSelectionRange(pos, pos) } catch (e) { /* 忽略 */ } }, 0)
      }
      const chip = function (id, n, req) {
        return h('span', { key: n, className: 'dsws-cfg-chip' + (req ? ' req' : ''), title: req ? tr('cfg.chipReq') : tr('cfg.chipInsert'), onClick: function () { insertPh(id, n) } }, [
          h('span', null, '{' + n + '}'),
          req ? h('span', { className: 'must' }, tr('cfg.must')) : null,
        ])
      }
      const tplCard = function (id) {
        const val = tpls[id] || ''
        const preview = renderTemplate(id, PREVIEW_VALUES)
        const req = (TPL_REQUIRED[id] || []).slice()
        return h('div', { key: id, className: 'dsws-cfg-card' }, [
          h('div', { className: 'dsws-cfg-card-head' }, [
            h('span', { className: 'dsws-cfg-card-name' }, tr('tpl.name.' + id)),
            h('span', { style: { flex: 1 } }),
            h('button', { className: 'dsws-cfg-btn', onClick: function () { resetTpl(id) } }, tr('cfg.reset')),
          ]),
          h('div', { className: 'dsws-cfg-card-desc' }, tr('tpl.desc.' + id)),
          h('div', { className: 'dsws-cfg-chips' }, (TPL_PH[id] || []).map(function (n) { return chip(id, n, req.indexOf(n) >= 0) })),
          h('textarea', { ref: function (el) { taRefs.current[id] = el; autoGrowTa(el) }, className: 'dsws-cfg-ta', placeholder: TPL_DEFAULT[id] || '', value: val, onChange: function (e) { setTpl(id, e.target.value); autoGrowTa(e.target) } }),
          h('div', { className: 'dsws-cfg-preview' }, [h('span', { className: 'pv-label' }, tr('cfg.preview')), preview]),
        ])
      }
      const custom = tpls.execute || ''
      return h('div', { className: 'dsws-cfg' }, [
        h('div', { className: 'dsws-cfg-head' }, [
          Icon({ scheme: 'compass', size: 20 }),
          h('span', { className: 't' }, 'DSH-Waystation'),
          h('span', { className: 's', style: { color: saved ? 'var(--dsw-alias-state-success-primary,#4ade80)' : 'var(--dsw-alias-label-caption,#8b8b95)' } }, [
            Ic({ n: saved ? 'check' : 'dot', size: 12 }),
            h('span', null, saved ? tr('cfg.saved') : tr('cfg.status')),
          ]),
        ]),
        h('div', { className: 'dsws-cfg-sub' }, tr('cfg.sub')),
        // v1.4：打开位置（details 列 / better-sidebar）—— better-sidebar 未装时仅显示 dock 选项
        h('div', { className: 'dsws-cfg-group' }, [
          h('div', { className: 'dsws-cfg-gtitle' }, [Ic({ n: 'map', size: 13 }), h('span', null, tr('cfg.openIn'))]),
          h('div', { className: 'dsws-cfg-gdesc' }, tr('cfg.openInDesc')),
          h('div', { className: 'dsws-cfg-row' }, [
            h('span', { className: 'dsws-cfg-label' }, tr('cfg.openInLabel')),
            h('div', { className: 'dsws-cfg-seg' }, [
              h('button', { key: 'dock', className: openIn === 'dock' ? 'on' : '', onClick: function () { pickOpenIn('dock') } }, tr('cfg.openInDock')),
              (function () { try { return !!ctx.get('betterSidebar') } catch (e) { return false } })()
                ? h('button', { key: 'sidebar', className: openIn === 'sidebar' ? 'on' : '', onClick: function () { pickOpenIn('sidebar') } }, tr('cfg.openInSidebar'))
                : null,
            ]),
            openInNote ? h('div', { style: { fontSize: 11, color: '#4ade80', marginTop: 6 } }, tr('cfg.openInHint')) : null,
          ]),
        ]),
        // 1.5 面板宽度重置（#398 拆票 A · 与 #397 协调 · 等 layoutSvc.resetDetails API；缺失时友好提示不让 UI 崩溃）
        h('div', { className: 'dsws-cfg-group' }, [
          h('div', { className: 'dsws-cfg-gtitle' }, [Ic({ n: 'refresh', size: 13 }), h('span', null, tr('cfg.panelWidth'))]),
          h('div', { className: 'dsws-cfg-gdesc' }, tr('cfg.resetPanelWidthDesc')),
          h('div', { className: 'dsws-cfg-row' }, [
            h('button', { className: 'dsws-cfg-btn', onClick: function () {
              const ls = ctx.get('layout')
              if (ls && typeof ls.resetDetails === 'function') {
                try { ls.resetDetails(); setResetNote({ kind: 'ok', text: tr('toast.resetPanelWidthDone') }) }
                catch (e) { setResetNote({ kind: 'warn', text: tr('toast.resetPanelWidthFail') }) }
              } else {
                setResetNote({ kind: 'warn', text: tr('toast.resetPanelWidthFail') })
              }
              if (timer !== undefined) timer.timeout(function () { setResetNote(null) }, 2800)
            } }, tr('cfg.resetPanelWidth')),
            resetNote ? h('span', { style: { marginLeft: 10, fontSize: 11, color: resetNote.kind === 'ok' ? '#4ade80' : '#fbbf24' } }, resetNote.text) : null,
          ]),
        ]),
        // 2. 开始模板（execute 唯一编辑点；id 供动作模板编辑器锚点跳转）
        h('div', { id: 'dsws-cfg-exec-group', className: 'dsws-cfg-group' }, [
          h('div', { className: 'dsws-cfg-gtitle' }, [Ic({ n: 'play', size: 13 }), h('span', null, tr('cfg.startTpl'))]),
          h('div', { className: 'dsws-cfg-gdesc' }, tr('cfg.startTplDesc')),
          h('div', { className: 'dsws-cfg-row' }, [
            h('label', { className: 'dsws-cfg-sw' }, [
              h('input', { type: 'checkbox', checked: wf, onChange: function (e) { setWf(e.target.checked) } }),
              h('span', { className: 'tr' }),
              h('span', null, tr('cfg.withPrefix')),
            ]),
          ]),
          h('textarea', { ref: function (el) { taRefs.current.execute = el; autoGrowTa(el) }, className: 'dsws-cfg-ta', placeholder: TPL_DEFAULT.execute || '', value: custom, onChange: function (e) { setTpl('execute', e.target.value); autoGrowTa(e.target) } }),
          h('div', { className: 'dsws-cfg-chips' }, [
            (TPL_PH.execute || []).map(function (n) { return chip('execute', n, (TPL_REQUIRED.execute || []).indexOf(n) >= 0) }),
            h('button', { className: 'dsws-cfg-btn', style: { marginLeft: 'auto' }, onClick: resetExecute }, tr('cfg.reset')),
          ]),
          h('div', { className: 'dsws-cfg-preview' }, [h('span', { className: 'pv-label' }, tr('cfg.preview')), renderTemplate('execute', PREVIEW_VALUES)]),
        ]),
        // 3. 动作模板编辑器（其余 6 动作 · T1：默认展开可手动折叠）
        h('details', { open: true, className: 'dsws-cfg-group dsws-cfg-details' }, [
          h('summary', { style: { display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, fontWeight: 650, marginBottom: 4, cursor: 'pointer', listStyle: 'none' } }, [Ic({ n: 'note', size: 13 }), h('span', null, tr('cfg.tplEditor'))]),
          h('div', { className: 'dsws-cfg-gdesc' }, [
            h('span', null, tr('cfg.tplEditorDesc')),
            h('a', { href: 'javascript:void(0)', onClick: function () { const el = document.getElementById('dsws-cfg-exec-group'); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }) }, style: { color: '#bc8cff', cursor: 'pointer', flex: 'none', textDecoration: 'none' } }, tr('cfg.execHint')),
          ]),
          TPL_EDIT_IDS.map(tplCard),
        ]),
        // 校验错误提示
        errs.length ? h('div', { className: 'dsws-cfg-err' }, [
          h('div', { className: 't' }, [Ic({ n: 'alert', size: 13 }), h('span', null, tr('cfg.saveRejected'))]),
          errs.map(function (e, i) { return h('div', { key: i }, '· ' + e) }),
        ]) : null,
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 10, alignSelf: 'flex-end' } }, [
          h('button', { className: 'dsws-cfg-btn', onClick: resetAll }, tr('cfg.resetAll')),
          h('button', { className: 'dsws-cfg-save', onClick: save }, [Ic({ n: 'check', size: 13 }), h('span', null, tr('cfg.saveAll'))]),
        ]),
      ])
    }

    // ---- 5.10 Run 卡控制面板（v25：状态展示 + 快捷打开配置页；外观切换已迁入设置页）----
    const RunPanel = (props) => {
      const cur = props.useSessions((x) => x.current)
      const s = useStore(cur)
      return h('div', { style: { border: '1px solid var(--dsw-alias-border-l1,#2a2d35)', borderRadius: 8, padding: '10px 12px', background: 'var(--dsw-alias-bg-layer-1,#10131a)', fontFamily: 'var(--dsw-font-family)', fontSize: 13, color: 'var(--dsw-alias-label-primary,#e6edf3)', lineHeight: 1.6 } }, [
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }, [
          h('strong', null, 'DSH-Waystation'),
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 4, color: '#4ade80', fontSize: 12 } }, [Ic({ n: 'dot', size: 10 }), h('span', null, tr('run.loaded'))]),
        ]),
        h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary,#a1a1aa)', margin: '6px 0' } }, tr('run.desc')),
        h('div', { className: 'dsws-uirow' }, [
          h('button', { className: 'dsws-btn', onClick: function () { openPanel(s) } }, tr('run.openPanel')),
          // v25：设置面板为 shell 组件本地状态、无公开打开 API（已查证）→ 按钮引导路径（偏离记录见 T2a resolution）
          h('button', { className: 'dsws-btn', onClick: function () { flash(s, tr('run.cfgGuide'), 'info') } }, tr('run.openCfg')),
        ]),
      ])
    }

    // ============================================================
    // 6. 插槽注册
    // ============================================================
    slots.inject('shell.overlay', function () {
      return slots.register({ name: 'shell.overlay', id: 'dsws-overlay-v5', order: 10 }, OverlayPanel)
    })
    slots.inject('conversation.input.dock', function () {
      return slots.register({ name: 'conversation.input.dock', id: 'dsh-waystation', order: 40 }, StatusBar)
    })
    slots.inject('tool.view.cordis', function () {
      return slots.register({ name: 'tool.view.cordis', key: 'self' }, RunPanel)
    })
    // v25-50：配置页（设置 → 插件 → Waystation；与 opencode 主题同模式）
    slots.inject('settings.plugins.tab', function () {
      return slots.register({ name: 'settings.plugins.tab', id: 'dsws-settings', order: 40, label: function () { return 'Waystation' } }, SettingsPage)
    })
    // v1.5 T2：设置左侧直达 —— settings.section 左栏条目（与插件页 tab 双入口，复用同一 SettingsPage）
    slots.inject('settings.section', function () {
      return slots.register({ name: 'settings.section', id: 'dsws-settings-section', order: 200, label: function () { return 'Waystation' } }, SettingsPage)
    })
    // 原型：右侧停靠（details 槽位 · 替换内置工具详情面板；single 槽动态注册优先级低 → 胜出）
    // priority: -1 低于内置详情面板的默认 0 → 无冲突且「低者胜出」替换内置面板
    slots.inject('details', function () {
      return slots.register({ name: 'details', id: 'dsws-details', order: 10, priority: -1 }, DetailsDock)
    })

    // v1.4.1：apply 时尽力注册「Waystation」tab；better-sidebar 服务未就绪（加载晚于本模块）→ 定时重试（最多 10 次）
    //   卸载（HMR / 插件禁用）时清理 disposer + 重试定时器
    if (!ensureSidebarTab()) {
      let tries = 0
      sidebarTabRetry = setInterval(function () {
        tries++
        if (ensureSidebarTab() || tries >= 10) { clearInterval(sidebarTabRetry); sidebarTabRetry = null }
      }, 1000)
    }
    ctx.effect(function () {
      return function () {
        try { if (sidebarTabDisposer) sidebarTabDisposer() } catch (e) { /* 忽略 */ }
        sidebarTabDisposer = null
        if (sidebarTabRetry) { clearInterval(sidebarTabRetry); sidebarTabRetry = null }
      }
    }, 'dsh-waystation: better-sidebar tab')

    // #347：加载真数据快照（repo 链接 + 前置检测兜底），失败静默
    loadSnapshot(shared, false)
  },
}
