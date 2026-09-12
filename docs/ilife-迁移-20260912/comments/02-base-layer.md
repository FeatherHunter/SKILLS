## ⛔ 停止开发 · 跨技能公共层已转交新仓 ilife

本 issue 关闭。**本仓的「公共组件」跨技能公共层已经停止开发**。

### 新项目地址：https://github.com/FeatherHunter/ilife

原来的「公共组件」（占位符注入管线 `<!--INJECT-DATA-->` / `<!--SHARED-HELPERS-->` ＋ toast / copyText / 守卫组 / actionBar 等 P0-P1 组件）解决的是「多个技能各自渲染 HTML、前端公共部分没法共享」的问题，做法是往技能 HTML 里注入占位符替换。

这件事在 ilife 里换了形态：技能被**重构为 TypeScript 项目**，公共部分成为真正可复用的 TS 包（例如 `packages/base-render` 持有共享 help 模板并生成 `helpShell.ts`），不再依赖字符串占位符替换；同时 ilife 在此基础上**开发了 DSH 插件**（`packages/plugin-*-ilife`）把技能能力注册给 DSH 会话。TS 包路线比注入式更硬、更可测，因此旧的注入式公共层不再演进。

所以对本 issue 的处理口径是：

- 本仓 `公共组件/` 目录：**冻结**，不再接受新组件、新契约与修复。
- 本 issue 描述的缺陷／需求：**不会在本仓实施**。如果这条仍然需要，请到 [ilife 仓 issue 列表](https://github.com/FeatherHunter/ilife/issues) 重新提出。
- 迁移样板：`饼干记账/ilife-新仓落地-20260911/README.md` —— 其中记录了共享 help 模板在 ilife 侧如何生成 `helpShell.ts`，以及「生成物不许手改」的硬约束。

> 关闭依据（维护者指示 2026-09-12）：跨技能／公共组件／卡路里／作息管家／私家大厨／饼干记账／备忘录 相关的 issue 全部关闭，并向读者强调新项目地址。
