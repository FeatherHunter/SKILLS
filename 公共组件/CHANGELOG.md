# CHANGELOG

> Base Skill 公共组件版本变更记录。**签名变更 = 破坏性变更**（必须全技能同步 + 一次性完成 + 本文件记录）;非破坏性变更（内部实现/样式细节）可独立发布。任何变更先开公共层 ISSUE（总纲 09 §92）。

## v1.6（2026-08-12 · 图表全参数化 · 方向 A 定稿）

**charts.js 四形态全参数化 + 复合形态**（契约 v1.6;与 #288 方向 A 定稿一致;新增参数非破坏性, 既有调用零变更;与 #289/#290 并发, 版本号按落地顺序递增）。

- **折线图 line 全量 16 项**: `height/compact/width` 尺寸三件套 · `color/lineWidth/dashed` 线条 · `smooth` 平滑曲线（Catmull-Rom, 数据点严格在曲线上）· `showDots/dotSize/dotStyle` 数据点 · `area/areaOpacity` 面积渐变 · `labels('edge/all/none/select')` 标签策略 · `showValues/labelRotate` 数值标注 · `yMin/yMax/grid` 坐标 · `format` 数值格式化 · `tooltip` 悬停提示 · `markLine` 阈值线 · `markPoint` 峰谷标注 · `step` 阶梯图 · `animation` 入场动画 · `series` 多序列 + `legend` 图例 · `avgLine` 移动均线 · `highlightLast` 最新点高亮
- **柱状图 bar 对齐 7 项**: format/colors/singleColor/height/compact/labels/showValues/yMin/yMax/grid/tooltip/animation; 修复「柱底参差」根因（绘图区+标签区两段式）
- **环形图 donut 对齐 6 项**: format/colors/size/ringWidth/legend(含手机 bottom)/showPercent/animation
- **进度条 progress 对齐 4 项**: color/gradient/height/showPct/animation
- **复合形态 3 个**: `charts.combo`（柱线组合）/ `charts.sparkline`（迷你趋势, 涨绿跌红）/ `charts.gauge`（仪表盘弧形进度）
- **结构校验（硬行为）**: items 非数组/缺 label/value 非法 → 直接抛错（对齐 Base v1.2 违规报错）; 显式 null = 缺失断点（line 线段断开）
- **坐标唯一性修复**: 容器零 padding + 留白进 viewBox → 数据点与线物理对齐（实测 <0.2px）; vector-effect 防拉伸变形
- **双端自适应**: ≤720px 手机独立 UI（标签两行/图例下沉/高度紧凑/触屏 tooltip）
- 守卫测试 141/141 全绿（+33 项参数断言 + 坐标对齐 + 双端视口 + 结构校验）; 契约 v1.6 + CHANGELOG 同步

## v1.5（2026-08-12 · #289 P2 HELP 参数化落地）

**HELP 参数化正式版**（契约 v1.2 + scene-data-contract v1；新增资产非破坏性，既有接口零变更）。

- **新资产 `assets/help_template.html`（单一真相源）**: V4.16 原型（用户 2026-08-12 认可）收敛为 Base 参数化模板——去手机壳真机全屏、数据全外部注入（`<!--INJECT-DATA-->` 注入 scene-data 契约 JSON）、复制/toast 走 Base 控件、statusBadge 协同 #290
- **新契约 `docs/scene-data-contract.md` + `docs/scene_data.schema.json`（v1）**: 2 级分组（category→subfunction）scenes 契约 + meta_blocks 透传块 + editable_fields 表单字段;机读 schema 守卫测试
- **归一化层实体取消（用户拍板核心思想）**: Base 零翻译、零适配;技能侧重构数据文件对齐契约（「技能侧零改动」红线作废）
- **injector `--help-template` 模式**: `validate_help_data` 契约校验（必填/分组/场景/id 唯一/status 二态）+ 文件名 sanitize（缺省 `help_<技能名>.html` + `..` 穿越拒绝）
- **editable_fields 管线**: 统一 `{name,label,value,hint,required}` → Sheet 参数表单 + Prompt 实时预览 + 空值拦截（复制按钮契约 v2 #123）
- **meta_blocks 设计**: 技能特有元信息（大厨 prompt_rules/methodology、备忘录 dependencies、卡路里 AI 验证协议）→ Base 原样透传（数据字段 · 页面不渲染展示 · 对齐 V4.16 定稿）
- 契约 v1.2 + CHANGELOG 同步;守卫测试 +33（契约 schema 15 + help 模板 18）→ 108/108 全绿
- 示例: `docs/examples/help_example_data.json`（覆盖 meta_blocks/init_banner/待开发/可编辑字段全特性）;浏览器实测 Sheet 参数表单 + 实时预览通过

## v1.4（2026-08-12 · #290 P2 状态层落地）

**状态层三控件加固**（statusBadge/emptyState/errorReceipt 从「定义」到「对外可靠」; 非破坏性, 签名全部向后兼容）。

- **errorReceipt 去 `window.__hmPayload` 强依赖**: 新增显式 `payload` 参数（优先）+ `data`/`log` 字符串直传（显式优先, 缺省从 payload 生成）+ 兼容全局兜底——**重构票迁移时不再依赖技能侧注入变量名**（卡路里 `__DATA__`/居家 `<script id="payload">` 都接得住）
- **复制按钮零注入面**: 渲染期生成复制文本存 `data-t`, onclick 仅 `copyText(this.dataset.t)`（原实现在点击时实时调 `buildDataText(window.__hmPayload)`, payload 缺失即 JS 报错）
- **错误回执容错**: payload 缺 `scene.snapshot` → 不渲染复制数据/日志按钮, 控件不抛错（错误场景数据常残缺, 不能让控件崩）
- **按钮布局对齐 08 规范**: 修正重试 primary wide 独立一行 + 复制数据/日志 ghost 一行 2 个（补 `.hm-actions` 网格容器, 原实现按钮无容器堆叠）
- **statusBadge 白名单降级**: 非法/未知 status 值降级 `empty`（原实现输出无样式徽章）
- **XSS 面收口**: 三控件全部文本字段经 `esc`; emptyState `action` 明示「受信 HTML 透传, 调用方负责内容安全」（契约 §6.3 明示）
- 契约 v1.4 + CHANGELOG 同步; 守卫测试 +9（非法值降级/XSS 转义/无 payload 容错/按钮布局/字符串直传）→ 15 项三控件测试全绿

## v1.3（2026-08-12 · #288 P2 图表组件落地）

**图表组件 CHARTS-HELPERS 正式版**（契约 v1.3, 与 #287 P2 盘点 + #288 落地一致;新增资产非破坏性, 既有接口零变更）。

- **新资产 `assets/charts.js`（唯一真相源）**: `window.charts` 四接口——`bar(el, items, opt)` / `line(el, items, opt)` / `donut(el, items, opt)` / `progress(el, pct, opt)`;bar/line/progress 从居家管家 CHARTS_JS **零行为变更提取**（接口兼容, 试点模板同调用可跑）, donut 从饼干记账 donutSVG 重构为数据驱动（2026-08-12 新增形态）
- **输入校验 + 空态联动**: items 非数组/空数组 → 渲染 emptyState（window.emptyState 存在则用之, 否则内联兜底）;progress pct 非数兜底 0、超界收敛 0~100
- **语义色走 token A 组**: 默认 `var(--blue,#007aff)` 带 fallback;bar/donut 支持逐项 color 覆盖;donut 内置 10 色 Apple 语义色板
- **纯 CSS+SVG 无外部依赖 · 手机 375px 适配**: 保留居家 @media 断点（柱高 130px/环形 130px）, 柱状图容器内横向滚动不撑破视口
- **自包含**: 本地 esc 兜底（window.esc 不存在时用内联转义）, 可独立注入不依赖 base.js
- **注入器**: `--charts <图表.js>` 参数注入 `<!--CHARTS-HELPERS-->` 占位符（0 或 1, v1.2 已预留;本版补正向测试）
- **SHARED_JS 全家桶核对**（#288 对抗式审查补充）: 居家 `_shared.py` SHARED_JS 中 Base 等价物（esc/toast/copyText/buildDataText/buildLogText/actionBar 等）走 Base、图表走 charts.js、metaHeader/remindersBlock 居家特定留技能侧;居家迁移完成后 SHARED_JS 整体退役（component-contract §2, 属 6 张技能重构票）
- **白名单例外**: 卡路里 weight_volatility_v2 canvas（特殊交互）留技能自营, 走公共层 ISSUE 审批
- 契约 v1.3 文档 + CHANGELOG 同步;守卫测试 +64（注入 4 + Playwright 四接口 17 项）→ 64/64 全绿
- 试点: 居家管家 stats 域同结构演示页走通 CHARTS-HELPERS 注入（四形态 + 375px 视口实测 0 溢出 0 JS 错误）

## v1.2（2026-08-11 · #269 试点 Grill 收口 · 用户拍板全量落地）

**领域无关重构 + 控件库扩展**（契约 v1.2, 与 #269 作息管家试点 Grill 决策一致;零消费方窗口, 破坏性变更零成本）。

- **snapshot 结构化接口（核心）**: buildDataText/buildLogText 从「居家管家字段绑定」重构为**领域无关通用结构**（title/summary/sections）——Base 不认任何技能领域字段, 技能把数据组织成 snapshot 传入, Base 只渲染（用户决策 2: 高于一切, 接口参数要什么技能就传什么）
- **toast 升级通用提示控件**: 4 形态（状态徽章/快捷操作/轻量计数/留空）+ 队列管理（连续不叠加）+ 内置图标库 + 多操作（最多 2）+ 富详情（多行/代码块）+ 无障碍 aria;`toast(msg, detail)` 向后兼容, 增强为可选第三参
- **复制按钮控件化**: 复制数据/复制日志 = Base 控件（文本可配/内容使用方定/参数校验）;增强: 复制前预览 + 格式选择（text/json/csv）+ 敏感字段脱敏 + 导出文件
- **结构校验违规直接报错**: snapshot 缺 title/非数组/节缺 heading → 渲染失败（硬拦截, 用户拍板「违规直接报错」）
- **新控件 P0+P1**: formPrompt（参数表单+实时预览+空值拦截）/ selectList（勾选+批量+计数联动）/ confirm（危险确认）/ foldBox / statusBadge / emptyState / errorReceipt
- **injector 加 SHARED-CSS 注入**: 修 v1.1 只注入 JS 缺口, base.css 唯一真相源进单文件 HTML
- 契约 v1.2 文档 + CHANGELOG 同步

## v1.1（2026-08-11 · 定稿入库）

**首个正式版**（契约 v1.1, 与 T4 #264 决策一致）。

- 形态: 资产目录 + 注入占位符（形态 A）;单一真相源（`assets/`）, 技能原实现迁移后退役
- P0+P1 组件入库: base.js 13 函数（守卫组/copyText v2/toast + metaHeader/remindersBlock/buildDataText/buildLogText/actionBar）
- base.css: token A 组 12 变量 + 按钮样式（≤3 色按功能/ghost 独立行/手机适配）
- injector.py: 硬拦截（INJECT-DATA/SHARED 恰 1）+ `--strict-payload` 信封校验 + `<!--NO-SHARED-->` 豁免通道 + CHARTS 可选
- 守卫测试 17 项（硬拦截反例/豁免/payload 校验/CLI 端到端）
- **跨技能硬编码修正**: buildDataText 技能名 / buildLogText 版本号参数化（消除「居家管家」写死）
- 两份契约入库: component-contract.md / help-template-contract.md（v1.1）

## 历史

- v1.0（2026-08-11 · 原型）: 注入器原型 + base.js 提取（居家管家基准）——原型验证用, 非正式版
