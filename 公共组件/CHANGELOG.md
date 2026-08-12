# CHANGELOG

> Base Skill 公共组件版本变更记录。**签名变更 = 破坏性变更**（必须全技能同步 + 一次性完成 + 本文件记录）;非破坏性变更（内部实现/样式细节）可独立发布。任何变更先开公共层 ISSUE（总纲 09 §92）。

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
