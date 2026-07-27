# 私家大厨 · 修复路线图（2026-07-27 立）

> **本文件是开工宣言 + 路线图，不是代码改动。** 每 Phase 完工后追加 ✅。
> 跨会话恢复：`git log --grep=fix-roadmap` 找回此文件。
> 分支：`fix/private-chef-p0-review`（从 main 拉出，**仅本路线图用此分支**）

---

## 0 · 来源与背景

- **来源**：2026-07-27 第一性原理审查（含对抗式自查）
- **方法**：以 `SKILL开发总纲V1.0/01-第一性原理.md` 的 5 层骨架 + 6 大特性 + §07 HELP 契约 + 8 反模式 + 改动前 3 问为标尺
- **范围**：私家大厨 SKILL.md (28KB) + 32 个 scripts (13K 行) + 8 features + 4 references + 3 templates + 33KB CHANGELOG
- **改动前 3 问**：
  - Q1 影响文件？ 见下表"修改点"列
  - Q2 数据迁移？ 全部 P0 是文档/契约/测试层，**无 schema 改动、无数据迁移**
  - Q3 回滚？ `git revert` 此路线图 commit 或整个 `fix/private-chef-p0-review` 分支

---

## 1 · 优先级清单（P0 × 4 + P1 × 3）

| # | 优先级 | 钩子 | 一句话诊断 | 修复 ROI |
|---|-------|------|-----------|---------|
| **F1** | 🔴 P0 | §07 HELP 契约 | 无 HELP 唤醒词 / 无场景资产 / 无 HELP HTML | **极高** |
| **F2** | 🔴 P0 | 原则 11 HTML-First | 4 个细分词（食材/步骤/营养/背景）走文字截取，无 section 锚点 | **高** |
| **F4** | 🔴 P0 | §03 铁律 3 | 跨 Skill 路由边界未声明 | **极高** |
| **FAT** | 🔴 P0 | §05 钩子 ⑥ | 从未跑过 Fresh Agent 黑盒测试 | **极高** |
| **F3** | 🟠 P1 | §03 变体管理 | 26/35 唤醒词无变体标注 | **极高** |
| **V2** | 🟠 P1 | 原则 11 | 搜索/历史/统计/派生 4 类榜单应做 HTML | **高** |
| **Test** | 🟠 P1 | §05 + 钩子 ⑥ | 无 tests/、无 pre-commit 注册、无 pytest | **高** |

> **已称赞合规项**（不要动）：详见审查报告 §2 合计 15 项（数据层/规则层/接口层/文档层/HTML 层）。**禁止重构**这些已合格模块，否则改出回归。

---

## 2 · 每项详情

### 🔴 P0-1 · F1 HELP 契约落地

- **违反**：总纲 §07 HELP 唤醒词契约。每个 Skill 必须登记 HELP 唤醒词 + 场景资产 + HELP HTML。**五者一一对应**（唤醒词声明 ↔ 场景资产 ↔ prompt ↔ 底层工作流 ↔ HELP HTML）
- **证据**：`grep -i "HELP\|场景资产\|scenario"` 在 SKILL.md / features / scripts 全部 0 命中
- **参考范式**：`卡路里` v2.4.10 commit `6ec089b`「新增 卡路里HELP 唤醒词 + 唤醒词速查台 HTML」
- **修改点**：
  - 新建 `references/scenarios.yaml`（**唯一事实源**，路径/格式自定但 §07 要求）
  - 新建 `templates/help.html`（4 段式骨架 + 5 状态 fallback）
  - 新建 `scripts/render_help.py`（走 `_assets/injector.py` 风格）
  - `SKILL.md`：加 HELP 唤醒词到 A-H 表之后（如 I 类），HELP **不展示自身**
  - `私家大厨.html`：同步镜像
- **验收**：
  - 唤醒词"私家大厨 HELP"能命中 → 渲染 help.html
  - HELP HTML 不含 HELP 自身词条
  - 场景资产含 7 字段（wake_word/scenario_id/scenario_title/dimensions/prompt/status/result）
  - 每个业务词场景**穷举**（不受 8 ≤ N ≤ 上限约束，按场景维度乘积）
  - `status` 二态：`""` 可用 / `【待开发】` 醒目标注且复制按钮仍可点
- **完成判定**：F1 ✅ → 才算 P0-1 完工

### 🔴 P0-2 · F2 4 细分词 section 锚点

- **违反**：原则 11 HTML-First。`recipe_view.html` grep "查看食材/ingredients_only" **0 命中**，模板无锚点。SKILL.md 第 138-150 行写"AI 从全量截取对应 section 给用户"= 实质文字答
- **证据**：`grep "查看食材\|查看步骤\|查看营养\|查看背景\|ingredients_only"` 在 recipe_view.html 与 recipe_render.py 各 0 命中
- **修改点**：
  - `templates/recipe_view.html`：在食材/步骤/营养/背景 4 个 section 加 `id="section-ingredients"` `id="section-steps"` `id="section-nutrition"` `id="section-background"`
  - `features/view.md`：加"细分词路由表"——4 个细分词 → HTML URL anchor 跳转
  - `SKILL.md` 第 138-150 行：改"截取 section"为"调 recipe_render.py render + URL anchor 跳转"
- **验收**：
  - 用户说"查看食材 宫保虾球" → AI 必须调 recipe_render.py + 拼 `#section-ingredients`
  - HTML 用 `<media>` 标签发文件，不用文字描述食材清单
- **风险**：URL anchor 需浏览器支持，跨平台 iframe 可能失效 → **降级方案**：4 个细分词合并为 1 个"查看食谱"+ tabs UI

### 🔴 P0-3 · F4 跨 Skill 路由声明

- **违反**：§03 铁律 3（跨 Skill 路由声明）+ SKILL.md "管什么/不管什么"边界
- **证据**：SKILL.md 末尾"与其他技能联动"段写"采购时联动卡路里"，但**无"哪个词路由到哪个 skill"**具体声明
- **修改点**：
  - `SKILL.md`：在"管什么/不管什么"段后，新增"跨 Skill 路由表"段：
    - 「采购清单」→ 私有；用户说"卡路里统计」 → 走卡路里
    - 「查营养」 → 走卡路里
    - 「记体重」 → 走卡路里
    - 「炊具借用」 → 走居家管家
- **验收**：grep 跨 Skill 路由词在 SKILL.md 第 30-50 行范围内命中至少 3 处

### 🔴 P0-4 · FAT Fresh Agent 黑盒测试协议

- **违反**：§05 钩子 ⑥（每个 commit 都通过 FAT）+ git log 30 个 commit 中**无私家大厨 FAT 痕迹**
- **证据**：`git log --grep="FAT\|Fresh\|黑盒" -- 私家大厨` 0 命中；同仓库卡路里/饼干记账都已做
- **参考**：总纲 `05-工程仪式.md §FAT 协议` 9 步
- **修改点**：
  - 写 35 唤醒词 × 3 变体语料矩阵（每个核心词 3 个人类口语化 prompt）
  - 跑 9 步协议（fresh agent + capture + 对比 + pass/fail）
  - 失败 → 改 SKILL.md（不改代码），循环 ≤ 3 次
  - 改完后 commit 加 `Tested-By: fresh-agent-v1` 段
- **验收**：至少 5 个核心词（开始做菜/查看食谱/搜索食谱/录入食谱/采购清单）各 3 个口语 prompt 全 pass

### 🟠 P1-1 · F3 变体管理

- **违反**：§03 变体管理（每个核心词配 2-3 个变体，3 方向：同义/口语/模糊）
- **证据**：SKILL.md 35 唤醒词，仅 D 类有 9 个口语化入口；其余 26 个无变体
- **修改点**：`SKILL.md` 唤醒词表加"变体方向"列（不写具体话避免硬编码过期）：
  - `搜索食谱`：同义=查询/找一下，口语=帮我搜一下，模糊=啥菜有排骨
  - 类推覆盖 26 个
- **验收**：35 个词中至少 30 个有变体方向标注

### 🟠 P1-2 · V2 4 类榜单 HTML

- **违反**：原则 11 + §04 原则 0 决策矩阵（榜单/时间线/状态徽章/综合仪表盘 = 必做 HTML）
- **证据**："搜索/历史/统计/派生" 4 类当前全文字答
- **修改点**：复用总纲 `_assets/template_skeleton.html` 4 段式骨架，新增 4 模板：
  - `templates/search_results.html`（单卡列表 / 网格）
  - `templates/history_timeline.html`（时间线 / 卡片栈）
  - `templates/stats_dashboard.html`（仪表盘 / 4-6 KPI 卡）
  - `templates/relation_graph.html`（树状 / 网络图）
  - 对应 4 个渲染器 `scripts/render_*.py`
  - 4 个对应 CLI `search_manager.py` / `history_stats_manager.py` / `relation_graph_manager.py`
- **验收**：用户说"查看统计 宫保虾球" → AI 调 stats 渲染器 → 输出 `$CHEF_OUTPUT_DIR/stats/宫保虾球_<ts>.html`

### 🟠 P1-3 · Test 自动化套件

- **违反**：§05 + 钩子 ⑥ + 总纲 §02 §05 测试模板（`tests/test_validators.py` 等）
- **证据**：`ls tests/` → No such file or directory；`.githooks/pre-commit` case 列表只含居家管家/卡路里/备忘录
- **修改点**：
  - 建 `tests/` 目录
  - `tests/conftest.py`（共享 fixture）
  - `tests/test_validators.py`（41KB validators.py 的单元测试，至少覆盖 9 个新校验函数）
  - `tests/test_payloads.py`（recipe_import.py 的 JSON 路径）
  - `tests/test_render.py`（recipe_render / cooking_render / shopping_render 三渲染器 smoke test）
  - `pytest.ini`（testpaths = tests）
  - `.githooks/pre-commit`：case 列表加 `私家大厨/*`
- **验收**：`cd 私家大厨 && python -m pytest tests/ -v` 至少 10 个用例全 pass

---

## 3 · 已称赞合规项（**不要动**）

详见审查报告 §2，合计 15 项：
- 数据层 G1/G2、WAL/重试/上下文管理器、`.bak.YYYYMMDD_HHMMSS` 备份
- 规则层 G3-G7、L1 NOT NULL、占位符黑名单、错误信息、字段推算边界
- 接口层 G8-G10、cli_formatter、subprocess 列表、how_to_fix 回执
- 文档层 G11/G12、确认词、软删除
- HTML 层 G13-G15、单工复制、命名、Jinja2 autoescape

**约束**：本路线图阶段**禁止触碰**以上模块。如发现需要改 → 新建独立 Task，**不许混在 P0/P1 commit**。

---

## 4 · 进度跟踪

- [x] P0-1 F1 HELP 契约落地 ✅ 38f0773 + 8aa904a + d8745d3 + 6900680 + 5dd3f9f(Phase 1.5→1.4→1.3→1.2→1.1)
- [x] P0-2 F2 4 细分词(方向修正:改 SKILL.md 引导 AI 走 HTML,不加锚点)✅ b10aa53
- [x] P0-3 F4 跨 Skill 路由声明 ✅ 34f4494 + cc2a6b2(11 已确定 + 3 已确定边界 + 1 不实现)
- [⚠️] P0-4 FAT Fresh Agent 黑盒测试 · 预演完成 ⚠️ 2e6028f(15 prompt 6 pass 9 fail · 待 fresh agent 真跑验证)
- [ ] P1-1 F3 变体管理
- [ ] P1-2 V2 4 类榜单 HTML
- [ ] P1-3 Test 自动化套件

> 完成后在此行追加 ✅ **和** commit hash：`- [x] P0-1 F1 ✅ abc1234`

### 4.1 · 进度备注

- **2026-07-27** P0-1 完工(5 commit)。总纲同日升级 V3(原则 12 拆 12.A/12.B),render_help.py 命名已对齐 12.B,但 SKILL.md §📌 输出位置章节待补(顺手任务,见 Phase 1.6)。

---

## 5 · 参考 commit（同仓库）

| 目标 | commit hash | 引用 |
|------|-----------|------|
| F1 HELP 落地范式 | `6ec089b` | `[卡路里] v2.4.10 · 新增 卡路里HELP 唤醒词 + 唤醒词速查台 HTML` |
| F3 变体管理范式 | `9a7222d` | `[卡路里] frontmatter 加口语变体(v2.4.13 · AI 路由命中更鲁棒)` |
| FAT 通过样例 | `6314447` | `[饼干记账] v2.3.3: FAT 通过 + P1 跨平台下载目录修复` |
| BUG 修复 + HELP 完善 | `368daf3` | `[饼干记账] v2.3.2 BUG 修复: HELP HTML 数据未注入` |

---

## 6 · 验收清单（完工前自检）

- [ ] 7 项全部 ✅
- [ ] 每个 P0 commit 含 `Tested-By: fresh-agent-v1` 段
- [ ] `git revert` 单个 P0 commit 不影响其他 P0
- [ ] CHANGELOG.md 追加本次路线图版本段
- [ ] `私家大厨.html` 镜像同步
