# 停止开发 · 技能本体迁往 ilife 新仓（2026-09-12）

这份夹子是「以后万一要看」用的**索引**：本仓（`FeatherHunter/SKILLS`）里**跨技能 / 公共组件 / 卡路里 / 作息管家 / 私家大厨 / 饼干记账 / 备忘录** 这一批东西**已经停止开发**，相关 GitHub issue 于 2026-09-12 一次性全部关闭，并在每个 issue 上留下指向新仓的说明。

## 新项目地址

> ### https://github.com/FeatherHunter/ilife

在 ilife 仓里，原 SKILLS 的技能被**重构为 TypeScript 项目**（`packages/skill-*`），并在此基础上**开发了 DSH 插件**（`packages/plugin-*-ilife`）—— 插件负责把技能能力注册给 DSH 会话。能力本身没有消失，只是换了家、换了实现方式。

## 一、关闭口径

| 项 | 值 |
|---|---|
| 执行日期 | 2026-09-12 |
| 关闭数量 | **29** |
| 关闭理由 | `not planned`（停止开发，非「已完成」） |
| 新增标签 | `wontfix` |
| 摘除标签 | `ready-for-agent` / `ready-for-human` / `needs-triage` / `needs-info`（留着会与已关闭状态自相矛盾） |
| 保留标签 | `skill:*` 与分类标签（`bug` / `enhancement` / `wayfinder:*`）—— 便于历史检索 |
| 评论 | 每个 issue 一条中文说明，含**新仓地址**、TS 重构 + DSH 插件交代、后续提需求去哪 |

关闭依据（维护者指示 2026-09-12）：「当前项目的所有和 跨技能、公共组件、卡路里、作息管家、私家大厨、饼干记账、备忘录 有关的 ISSUE 都应该关闭，并且强调在 https://github.com/FeatherHunter/ilife 是新的项目的地址，在将 SKILL 重构为 TS 项目基础上还开发了 DSH 插件。因此现在项目中这些东西已经停止开发。」

## 二、被关闭的 29 张票

### 卡路里 · 9 张（`skill:卡路里`）

| 票 | 标题 |
|---|---|
| [#1](https://github.com/FeatherHunter/SKILLS/issues/1) | wayfinder 决策地图 · v1.0 重设计 446 场景（11 分类全定稿） |
| [#38](https://github.com/FeatherHunter/SKILLS/issues/38) | 身材照片 10 场景 · 逐场景人工验收（5 层链路 · 开发者引导实测） |
| [#39](https://github.com/FeatherHunter/SKILLS/issues/39) | 身体细节 13 场景全流程人工验收（用户实测 · 2026-08-02） |
| [#40](https://github.com/FeatherHunter/SKILLS/issues/40) | 运动 39 场景人工验收审查（用户逐场景拍板 · AI 辅助协议） |
| [#41](https://github.com/FeatherHunter/SKILLS/issues/41) | 分析 154 场景 · 人工逐场景审查（验收闭环） |
| [#42](https://github.com/FeatherHunter/SKILLS/issues/42) | 健身计划 29 场景人工验收审查（ticket #6 完成态 · 5 层工作流） |
| [#318](https://github.com/FeatherHunter/SKILLS/issues/318) | plan_builder_wizard 周视图 sIdx 未定义 · swap 功能渲染中断 |
| [#323](https://github.com/FeatherHunter/SKILLS/issues/323) | 健身计划「复制数据」按钮内容为空壳（scene.snapshot 未注入） |
| [#377](https://github.com/FeatherHunter/SKILLS/issues/377) | 图表回切 · yTicks + ownScale 采用 |

### 饼干记账 · 1 张（`skill:饼干记账`）

| 票 | 标题 |
|---|---|
| [#163](https://github.com/FeatherHunter/SKILLS/issues/163) | v2.0 实施 · wayfinder 实施地图 |

### 私家大厨 · 7 张（`skill:私家大厨`）

| 票 | 标题 |
|---|---|
| [#200](https://github.com/FeatherHunter/SKILLS/issues/200) | 实施编排 map · v4.0 落地（10 域场景+08 对齐+数据层+开源） |
| [#215](https://github.com/FeatherHunter/SKILLS/issues/215) | T14 开源收尾 · 泄漏清理+SKILL.md+HELP+README · v4.0 |
| [#217](https://github.com/FeatherHunter/SKILLS/issues/217) | T4 审查配对 · 首次使用向导 08 门禁 B 人工验收 |
| [#219](https://github.com/FeatherHunter/SKILLS/issues/219) | T9 审查配对 · 采购清单 已有vs需买详情层 门禁 B 人工验收 |
| [#221](https://github.com/FeatherHunter/SKILLS/issues/221) | T7 审查配对 · 搜索筛选 纠错+排除+7字段 门禁 B 人工验收 |
| [#223](https://github.com/FeatherHunter/SKILLS/issues/223) | T8 审查配对 · 做菜域 断点续做+完结闭环 门禁 B 人工验收 |
| [#293](https://github.com/FeatherHunter/SKILLS/issues/293) | Base 重构优化 · 全部 HTML 迁公共组件 |

### 备忘录 · 1 张（`skill:备忘录`）

| 票 | 标题 |
|---|---|
| [#178](https://github.com/FeatherHunter/SKILLS/issues/178) | v1.2.1 开源交付 · 人工验收（README 安装走通 + HELP 双端视口） |

### 作息管家 · 1 张（`skill:作息管家`）

| 票 | 标题 |
|---|---|
| [#296](https://github.com/FeatherHunter/SKILLS/issues/296) | Base 重构优化 · 全部 HTML 迁公共组件 |

### 公共组件（跨技能公共层）· 2 张（`skill:公共组件`）

| 票 | 标题 |
|---|---|
| [#381](https://github.com/FeatherHunter/SKILLS/issues/381) | charts.line smooth 曲线不经过内点 · 数据点飘在曲线外 |
| [#382](https://github.com/FeatherHunter/SKILLS/issues/382) | [跨技能] charts 新参数技能侧回切追踪（v1.18-v1.25 上线后 · 13 模板） |

### 技能互联（跨技能数据契约层）· 8 张（`skill:技能互联`）

| 票 | 标题 |
|---|---|
| [#270](https://github.com/FeatherHunter/SKILLS/issues/270) | wayfinder 决策地图 · 6 技能数据契约层打通 |
| [#277](https://github.com/FeatherHunter/SKILLS/issues/277) | 消费方开发 · 卡路里 |
| [#278](https://github.com/FeatherHunter/SKILLS/issues/278) | 消费方开发 · 饼干记账 |
| [#279](https://github.com/FeatherHunter/SKILLS/issues/279) | 消费方开发 · 作息管家 |
| [#280](https://github.com/FeatherHunter/SKILLS/issues/280) | 消费方开发 · 居家管家 |
| [#281](https://github.com/FeatherHunter/SKILLS/issues/281) | 消费方开发 · 备忘录 |
| [#282](https://github.com/FeatherHunter/SKILLS/issues/282) | 消费方开发 · 私家大厨 |
| [#283](https://github.com/FeatherHunter/SKILLS/issues/283) | 07 · 校验器 v1.1 · 组合表三级引用断言 |

> 注：#1 / #163 / #200 / #270 是 wayfinder 实施地图（父票），关闭后其子票进度条不再推进；子票本身大多是早年已关闭的历史票，本次随图一并收敛。

## 三、明确的边界（**没关**的部分）

按「技能名」划定范围时不在这批里的：

| 票 | 内容 | 为什么留着 |
|---|---|---|
| [#104](https://github.com/FeatherHunter/SKILLS/issues/104) / [#116](https://github.com/FeatherHunter/SKILLS/issues/116) / [#253](https://github.com/FeatherHunter/SKILLS/issues/253) / [#292](https://github.com/FeatherHunter/SKILLS/issues/292) | 居家管家 | **居家管家不在指示的 7 项名单内** |
| [#440](https://github.com/FeatherHunter/SKILLS/issues/440) | dsh-waystation 插件 | DSH 插件生态，与技能本体迁移无关 |

⚠️ **待确认**：本机 DSH 技能目录里已经出现 `skill-home`（居家管家）与其余 5 个 `skill-*` 一起注册，说明**居家管家很可能也已迁往 ilife**，但维护者本次指示的名单里没有它，故未动。#292 更是「居家管家迁公共组件」——若居家管家也停发，这 4 张票应一并关闭。**请维护者裁决。**

## 四、迁移样板（想照抄做法的看这份）

`饼干记账/ilife-新仓落地-20260911/README.md` —— 饼干记账是**第一个在新仓跑通的样板**，内含：

- 8 张子票的结果索引（ilife#143 地图）
- 代码落位：`packages/skill-bill/` ＋ `packages/plugin-bill-ilife/`
- 本机三处 Junction 怎么接、DSH profile 怎么装
- 三个已踩过的坑（生成物不许手改 / SKILL.md frontmatter 缺失会导致整包跳过 / 还原后须 `tsc -b --force`）
- 发版待办清单

## 五、本夹子内容

| 文件 | 用途 |
|---|---|
| `README.md` | 本文件 · 总索引 |
| `plan.json` | 票号 → 模板 → 技能名 的映射表（执行输入） |
| `comments/01-single-skill.md` | 单技能用评论模板（`{{SKILL}}` 占位） |
| `comments/02-base-layer.md` | 公共组件用评论模板 |
| `comments/03-cross-skill.md` | 技能互联用评论模板 |
| `close-issues.ps1` | 执行脚本（`-DryRun` 预演 / `-Only <票号>` 分批 / 幂等，已关闭的自动跳过） |
| `close-log.csv` | 本次执行结果（票号 + 结果 + 标题） |

### 编码踩坑（后来者别再踩）

PowerShell 5.1 在 Windows 上**默认按 ANSI 解析无 BOM 的 `.ps1`，且 `Get-Content` 默认按 ANSI 读文件**。本夹子因此做了两层规整：

1. `close-issues.ps1` 保持**纯 ASCII**（中文全部外置到 `plan.json` 与 `comments/*.md`）；
2. 所有文件读写走 `.NET` 显式 `UTF8Encoding($false)`，并且在写临时文件后**回读比对**，避免把乱码发上 GitHub。

`gh issue close` 只有 `--comment <字符串>`，没有 `--body-file`，所以脚本走「先 `gh issue comment --body-file`，再 `gh issue close --reason "not planned"`」。

## 六、复现/复核命令

```powershell
# 预演（只打印，不写）
.\docs\ilife-迁移-20260912\close-issues.ps1 -DryRun

# 复核本次结果：应只剩居家管家 4 张 + dsh-waystation 1 张
gh issue list --state open --limit 500

# 复核某张票的关闭评论
gh issue view 178 --comments
```
