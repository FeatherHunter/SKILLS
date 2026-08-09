# 作息管家 L 级重构 · 规格 map（wayfinder）

> 本地镜像 = 真相源（09 军规 8）。GitHub 正文与本文件同步维护。
> 创建：2026-08-07 · 来源：handoff-作息管家-L重构-20260807_154024 + grilling Round 1-3

## Destination

作息管家 v1.1.3 L 级重构的**规格定案**：开源清仓处置、跨平台路径、onboarding 三段式、领域第一功能（深度+广度，交互铁律内）四项决策全部闭环；产出「规格阶段 → 实施阶段」交接点（实施 map 起点）。

## Notes

- **领域**：作息管家（record 作息记录 + plan 日程计划 双域）
- **流程**：`SKILL开发总纲V1.0/09` L 级两阶段（规格 map → 实施 map）
- **技能**：grilling / domain-modeling / prototype / research / wayfinder
- **已定决策**（Q1-Q14 人类拍板，勿重问）：
  - 规模 L 级 + 两阶段流程（规格 → 实施）
  - 优先级：可开源（硬约束）→ 零基础用户 → 领域第一（差异化）→ 可交付
  - 平台：Windows + Linux（**无 macOS**）
  - 零基础用户 = 复制即用的完整安装/初始化 prompt
  - 领域第一对标：飞书日历 + Notion Calendar + 滴答清单 + 时光序（复合形态）+ AI 协作差异化；R1 确认「作息记录+日程计划+AI 复盘闭环」四家全空缺
  - Q5 开源清仓**全部处理**；Q6 路径链 env → `D:/.db`(win) → `~/.local/share/schedule-guardian/db`(linux)；Q7 作息管家/ 独立 MIT 子 LICENSE；Q8 三段式 onboarding；Q9 新增「首次使用」唤醒词入 scenarios.yaml；Q10 历史**不清理**、README 不提及；Q12 **不加** CI；Q13 初始化报告对标居家管家 first_use_wizard；Q14 直连脚本收敛为「底层 schedule_db.py + 中间层 schedule_cli.py」两层，batch 收敛为 CLI 子命令，direct_add/batch_add_morning 删除
- **交互铁律 v2**（Q11，所有功能票必过）：所有功能以「HTML + 复制 prompt」为核心。闭环变体：① 一步直达（无过程页，不硬塞）② 多轮过程（过程 HTML → 操作 → 复制 prompt → 继续 → 结果 HTML）③ 多轮变种（允许）；**不引入第三种交互范式**
- **顶层体验输入**（2026-08-08 用户口述，最高优先级）：`.scratch/skill-levelup/specs/顶层体验描述-2026-08-08.md` —— help 层级结构 + 场景命名原则 + 三层评估法（DB→CLI→场景）+ 动 DB 需用户确认 + 记录结果型作息表 HTML
- **协议红线**：gh = `& "D:\0Tools\GitHubCLI\gh.exe"`；issue 标题 `[作息管家]` 前缀 + `skill:作息管家` + 分类 + 状态 label；Git 只 `add`/`commit`（禁 push）；全中文 commit + `Tested-By:` 行末；双门禁 A/B（09.1 T-A/T-B）；偏离记录三问（T-D）；人类参与点：push / 数据层 / 规格口径 / 双浏览器审查 / 考题判定 / 最终交付

## Decisions so far

- [R2 开源准备处置](https://github.com/FeatherHunter/SKILLS/issues/191) — 16 项清仓清单定稿并**人类采纳**（2026-08-07）：删 direct_add/batch_add_morning/plan_*.json；batch_add 收敛为 CLI `batch-add`；路径统一 `get_db_base_dir()` 解析器；白名单迁出 .db/；新增 MIT 子 LICENSE；文档 8 处清理。观察项：`.notes/` 删、`.out-of-scope/README.md` 留、跨技能 pycache 不动、migrate_plan_to_events.py 保留（已走统一路径）。
- [G1 领域第一功能定标](https://github.com/FeatherHunter/SKILLS/issues/193) — **人类 Q1-Q12 全采纳**（2026-08-09）：功能定标清单定稿（6 深度场景：记录/复盘今日/复盘本周/复盘本月/制定次日计划/周视图 + 5 基础覆盖 + 跨场景约定：复盘→计划衔接引导、缺数据提示补齐、健康分全粒度、场景独立呈现、daily_summary 待评估）。清单见 `.scratch/skill-levelup/issues/G1-功能定标清单.md`。G2 解封需 R3。顶层体验（每晚工作流/记录结果 HTML/场景原则）已作为最高优先级输入吸收。
- [R3 onboarding 三段式设计](https://github.com/FeatherHunter/SKILLS/issues/192) — **人类确认**（2026-08-09）：复制即装 prompt + 首次使用 6 步 + 初始化报告原型全认可；**飞书强引导**（配合飞书效果最好，拒绝才跳过）。原型资产 `.scratch/skill-levelup/r3/`（README 草案 / 首次使用工作流 / first_use_wizard.html）。落地归实施阶段。
- [G2 场景枚举定标](https://github.com/FeatherHunter/SKILLS/issues/194) — **人类确认**（2026-08-09）：81 场景清单（73 现有 + 8 新增/强化），「复盘 start-end」保留独立场景并**更名「复盘区间」**；批量导入独立场景；完整盘点已跑。清单见 `.scratch/skill-levelup/issues/G2-场景枚举定标.md`。

## ✅ 规格 map 全部闭环（2026-08-09）

R2 / G1 / R3 / G2 四票全部关闭，规格阶段决策全部定案。下一步：建**实施 map**（09 两阶段流程第 2 阶段）。

## Not yet specified

- 深度功能具体清单（G1 定标：复盘叙事增强 / 健康分 / AI 洞察等做哪些、做到什么程度）
- 广度功能具体清单（G1：周视图 / NLP 日期解析等挑哪几个）
- onboarding 三段式具体内容（R3：README 结构 / 复制即装 prompt 措辞 / 首次使用工作流步骤 / 初始化报告形态）
- 场景枚举完整清单（G2：73 → 74+，含「首次使用」场景 + G1 新功能场景）
- 文档 5 处绝对路径的具体改法（R2 出清单）
- 实施阶段拆分（实施 map，规格闭环后）

## Out of scope

- macOS 支持（Q2 拍板）
- GitHub Actions / CI（Q12 拍板）
- git 历史清洗（Q10 拍板：历史不清理；README 不提及，避免此地无银）
- 在线服务 / 桌面 App / 第三种交互范式（交互铁律 v2）
- 其他技能的历史数据与目录清理（本 effort 只处理作息管家）

## Child tickets（本地附录 · GitHub 父子关系为准）

| # | 票名 | 类型 | 状态 | 阻塞 |
|---|---|---|---|---|
| #191 | [R2 开源准备处置](https://github.com/FeatherHunter/SKILLS/issues/191) | wayfinder:research | ✅ closed | — |
| #192 | [R3 onboarding 三段式设计](https://github.com/FeatherHunter/SKILLS/issues/192) | wayfinder:prototype | ✅ closed（飞书强引导确认） | — |
| #193 | [G1 领域第一功能定标](https://github.com/FeatherHunter/SKILLS/issues/193) | wayfinder:grilling | ✅ closed（功能定标清单） | — |
| #194 | [G2 场景枚举定标](https://github.com/FeatherHunter/SKILLS/issues/194) | wayfinder:task | ✅ closed（81 场景清单） | — |

**规格 map 全部闭环（2026-08-09）**——无 open 票。下一步：建实施 map（09 两阶段第 2 阶段）。
