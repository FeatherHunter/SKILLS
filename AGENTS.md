# AGENTS

本仓库（`FeatherHunter/SKILLS`）的根级 AI 协作入口。技能子目录各自维护 `AGENTS.md`，本文件只描述**仓库级别**的约定。

## 项目结构

跨技能集装仓库，根目录并排放置多个独立技能（`备忘录/`、`卡路里/`、`居家管家/`、`私家大厨/`、`饼干记账/`、`智剪工坊/`、`作息管家/`、`SKILL开发总纲/` 等）。每个技能是一个独立产品，各自维护 `AGENTS.md`、`CONTEXT.md`、`docs/adr/` 和 `.scratch/<feature>/` 工作目录。

## 跨技能规范（任何技能的设计/规划/开发必读）

### 🔴 数据库隔离红线（最高优先级 · 2026-08-10 用户核心要求）

**在本仓库目录下进行的所有开发，一律禁止触碰生产环境的数据库文件。** 范围覆盖：

- 编写/运行 **test 脚本**（pytest / 单测 / 集成测试）
- 开发过程中 **自己做的任何验证、自测、手工跑 CLI**（含 debug、演示、造数据、查数据）

**生产数据库** = 各技能无环境变量覆盖时 CLI 实际读写的那份真实数据文件，包括但不限于：

- `SKILLS_DB_PATH` 未设置时回退的默认路径（如 `D:/.db/`、`~/.local/share/schedule-guardian/db/`）
- 技能目录内的真实 `*.db`（如 `卡路里/scripts/*.py` 模块级 `DB_PATH` 指向的 `calorie_data.db`）
- 其它用户真实数据的落盘位置

**测试只能使用临时 DB**，且必须显式隔离，用后即弃：

- 优先：测试内 `monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))` 或 monkeypatch 模块 `DB_PATH`（参考 `作息管家/tests/conftest.py`、`卡路里/tests/conftest.py` 既有隔离契约）
- 手工自测：把 `SKILLS_DB_PATH` 指向临时目录后运行，或在临时路径新建 `.db` 文件
- 任何涉及 DB 读写的脚本/自测执行前，先确认当前进程解析到的 DB 路径指向临时文件；执行后清理临时 DB

**违反即事故**：运行任何命令前若无法确认 DB 路径已隔离，禁止执行，先向用户确认。

**`SKILL开发总纲/` = 所有技能的元规范之家**，开发/改造任何技能之前先读其 `README.md`（文件清单索引）。重点：

- `08-HTML交互规范.md`（2026-08-04 新增）—— 跨技能 HTML 交互契约：8 类流程 / 通用骨架 / 4 标准能力 / 按钮语义 / 输出双通道 / 图片接收契约。**设计任何场景 HTML 或交互按钮时必读**。
- `09-SKILL重构优化指导.md`（2026-08-06 新增）—— 重构/优化既有 SKILL 的必读流程：规模分级 / 两条路径 / 14 条军规 / 闭环双门禁 / 偏离记录 / 复盘 / 人类理解对齐考题。配套模板集 `09.1-重构优化可复制模板集.md`。**接到任何「重构/优化 SKILL」任务时必读**。
- `04-可视化与注入.md` —— HTML 模板与注入原则
- `07-HELP与场景完备性.md` —— HELP 契约
- `05-工程仪式.md` —— FAT / Tested-By / hooks
- **跨技能「首次使用」流程对齐**（2026-08-07 新增）—— 各技能的首次使用/初始化流程应跨技能保持一致（参考居家管家 `SM8.yaml` 实证，减少开发成本）；**该原则可能存在特例，应用前与用户确认**。

## Git 与远端

- 远程：`github.com/FeatherHunter/SKILLS`
- 主分支：`main`
- 子模块（独立仓库）：`mcp_excalidraw/`、`superpowers/`、`taste-skill/`、`ui-ux-pro-max-skill/`
- 嵌入式 PAT 见 `docs/agents/issue-tracker.md` 安全备注

## 提交规范

全中文硬规则（详见 `docs/agents/issue-tracker.md` 与子技能各自 `AGENTS.md`）：

```
[技能名] <主题> · <细节(可选)>
Tested-By: exempt(无 fresh agent · 详见 备忘录/docs/adr/0005-d-exemptions-and-rituals.md)
```

❌ 禁用英文类型前缀（`fix:` `docs:` `feat:` `chore:`）与英文括号类型（`fix(...)` 等）。
✅ 每个 commit 必须含 `Tested-By` 行末。
⚠️ **commit 前先查暂存区**（`git status --short` 第一列 = 已暂存）：并行 agent 可能把半成品改动留在暂存区，pre-commit 钩子会跑「暂存区涉及的所有技能」pytest——混入他人未完成改动会连带测试失败导致 commit 被拒（2026-08-11 实测：卡路里半成品挡居家管家 commit）。只提交自己的文件用 `git commit --only <path>`，或先 `git restore --staged <他人路径>`（文件内容不动，仅取消暂存）。

## Agent skills

### Issue tracker

GitHub Issues（`FeatherHunter/SKILLS`），按技能前缀分区：`[备忘录]` / `[卡路里]` / `[居家管家]` / `[私家大厨]` / `[饼干记账]` / `[智剪工坊]` / `[作息管家]` / `[SKILL开发总纲]`。详见 `docs/agents/issue-tracker.md`。

### Triage labels

五状态二分类默认标签（`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` + `bug` / `enhancement`）。详见 `docs/agents/triage-labels.md`。

### Domain docs

单仓库多上下文布局，根 `CONTEXT.md` + 根 `CONTEXT-MAP.md` 索引到各技能子目录的 `CONTEXT.md`。详见 `docs/agents/domain.md`。

### Delivery fidelity（交付保真规范）

解决「AI 交付只有 60%」的六个保真手段（交付前三问自检 / grilling 问边界 / 先交决策清单 / 验收标准进 ticket / verifier 独立审查 / 小步交付+里程碑确认）。任何 agent 交付任何工作前默认遵守：小事至少用手段 1，跨技能/跨会话大任务手段 1-6 全用。详见 `docs/agents/delivery-fidelity.md`。

### Execution framework（执行框架）

用户定制的「执行前 / 执行中 / 执行后」三项工作要求：**执行前**（告诉起点 → 发现盲区 → 采访澄清 → 原型验证 → 执行计划）、**执行中**（记录偏离）、**执行后**（过程复盘 → 确认理解 → AI 反向考验 → 答明白再交付）。任何 agent 执行 wayfinder / map / ticket / 技能任务时默认遵守；**不修改 wayfinder 技能文件**，靠本约定 + `docs/agents/execution-framework.md` + 辅助 SKILL 落实。详见 `docs/agents/execution-framework.md`。