# CHANGELOG

> Base Skill 公共组件版本变更记录。**签名变更 = 破坏性变更**（必须全技能同步 + 一次性完成 + 本文件记录）;非破坏性变更（内部实现/样式细节）可独立发布。任何变更先开公共层 ISSUE（总纲 09 §92）。

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
