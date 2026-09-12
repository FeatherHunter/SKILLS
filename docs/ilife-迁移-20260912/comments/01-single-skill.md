## ⛔ 停止开发 · 已转交新仓 ilife

本 issue 关闭。**「{{SKILL}}」这个技能已经停止开发**，本仓（`FeatherHunter/SKILLS`）不再接受它的新功能、修复与验收推进。

### 新项目地址：https://github.com/FeatherHunter/ilife

在 ilife 仓里，原 SKILLS 的技能已经被**重构为 TypeScript 项目**（`packages/skill-*`），并在此基础上**开发了 DSH 插件**（`packages/plugin-*-ilife`）—— 插件负责把技能能力注册给 DSH 会话。也就是说能力本身没有消失，只是换了家、换了实现方式。

所以对本 issue 的处理口径是：

- 本仓 `{{SKILL}}/` 目录：**冻结**，作为历史资产保留，不再演进。
- 本 issue 描述的需求／缺陷：**不会在本仓实施**。如果这条仍然需要，请到 [ilife 仓 issue 列表](https://github.com/FeatherHunter/ilife/issues) 重新提出。
- 迁移样板（可直接照抄的做法）：`饼干记账/ilife-新仓落地-20260911/README.md` —— skill-bill ＋ dsh-bill-ilife 已在新仓跑通，内含票面索引、代码落位、装机方式与踩坑记录。

> 关闭依据（维护者指示 2026-09-12）：跨技能／公共组件／卡路里／作息管家／私家大厨／饼干记账／备忘录 相关的 issue 全部关闭，并向读者强调新项目地址。
