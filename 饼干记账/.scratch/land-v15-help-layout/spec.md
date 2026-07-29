# Spec: 落地 HELP 页面 v15 布局 + auto-sync 根目录镜像

Status: ready-for-agent
Created: 2026-07-30
Slug: land-v15-help-layout

## Problem Statement

`饼干记账` skill 的 `help` 命令（背后是 `render_help.py` 渲染 `templates/help.html`）当前生成的 HTML 页面有 3 个用户感知层的真问题：

1. **信息冗余** —— 每个 L3 场景的 summary 行下方挂了一串维度小标签（`分类: 餐饮/外卖/午餐`、`时间: 今天`、`账户: (未指定)` 等）。这些信息在 prompt/result 区域已经能完整呈现，summary 行重复只会让卡片高度膨胀、扫读时被噪声干扰。

2. **手机端体验差** —— 移动端（≤600px）一个场景卡 70px 高、标题被挤到 32px 宽（5-6 行换行），首屏只能看到 4-5 条场景。在地铁上根本没法用。

3. **根目录镜像靠人工同步** —— `饼干记账.html`（skill 根目录那份快照）按 `SKILL.md` L10 规定"功能变更必须同步更新"，但 `render_help.py` 自身没有 copy 逻辑，全靠人工记忆。已发生 30KB 漂移（根目录 v2.4，timestamped 文件 v15）。

**用户视角**：打开 `饼干记账.html` 应该跟打开 `饼干记账_HELP_<最新时间戳>.html` 看到的是同一个干净的、移动端可读的、没有维度标签的 v15 布局。

## Solution

把 v15 布局落地到 `templates/help.html`，并在 `render_help.py` 末尾追加 3 行让每次渲染自动同步根目录镜像。

验收接缝（最高 seam，理想数量 = 1）：

> **跑一次 `render_help.py`，检查：**
> 1. `$DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<TS>.html` —— 存在 + 含 v15 标记
> 2. skill 根目录 `饼干记账.html` —— 存在 + 内容与上述 timestamped 文件一致

### 涉及的模块

| 模块 | 改动 |
|---|---|
| `templates/help.html` | 替换 CSS（v15 移动端 grid→flex、`.sc-dim` 维度样式变废）+ 替换 `<script>` 里 `renderScenario` 函数（去掉 `dimBadges` 生成）+ 把 `<!--INJECT-DATA-->` 占位符保留为唯一 |
| `scripts/render_help.py` | 末尾追加 auto-copy 逻辑：把生成的 `html` 同步写到 `SKILL_DIR / "饼干记账.html"`，并 print 一行提示 |
| （不动）`references/scenarios.json` | 数据契约不变；`dimensions` 字段保留供将来用，但 v15 模板不渲染它 |
| （不动）`scripts/html_paths.py` | HELP 路径命名约定已对齐 §12.B，无需改 |
| （不动）`scripts/bill_inject.py` | 跟 help 无关 |
| （不动）`tests/test_render.py` | 现有 4 个 `test_help_html_*` 用例不需要改（它们只验 BOM/唤醒词/文件名，不验 CSS） |

### 第一性原理（约束设计的几条公理）

1. **模板是 single source of truth** —— HTML 的视觉/CSS/JS 只在 `templates/help.html` 一处。改模板 = 改输出。其它地方不存"影分身"。
2. **auto-sync 是 bug 的对偶** —— 当同一信息在两处表达（timestamped + 根目录），手工同步是反模式。系统应该自动同步，否则就是设计缺陷。
3. **版本绑定契约，不绑定实现** —— `v2.4` 是数据契约（`scenarios.json._meta.version`），CSS 重构不影响契约。两个轴正交，不混淆。
4. **最高 seam 优先** —— 验收只看"跑一次 render_help.py 后两份文件长对不对"，不深入到 CSS 选择器或 JS 函数细节。

## User Stories

1. As a 饼干记账 skill 拥有者，我在手机（≤640px）打开 `饼干记账.html` 看到首屏至少 8 条 L3 场景，so that 我在地铁里能扫读选 prompt。
2. As a skill 拥有者，每个 L3 场景卡片只占一行（折叠态 50px），so that 我一眼能数出"这条要不要展开看 prompt"。
3. As a skill 拥有者，折叠态的场景名字右边有 `📋 复制` 按钮，so that 我一秒钟复制 prompt 走人，不用展开。
4. As a skill 拥有者，展开后的场景卡片**没有**任何复制按钮，so that 视图干净（v12 已确认的视觉契约）。
5. As a skill 拥有者，每个 L3 场景卡片**没有**维度小标签（`分类:` / `时间:` / `账户:` 等），so that summary 行不被噪声信息污染。
6. As a skill 拥有者，prompt 和 result 文字默认**左对齐**，so that 长文本不会居中错位（v15 显式声明）。
7. As a 桌面端用户（≥1280px），L3 场景一行排开（标题 + 复制按钮），so that 我能横向扫读全部 91 个场景。
8. As a skill 拥有者，L2 唤醒词卡片（记支出/记收入/...）**没有**复制按钮，so that 层级清晰——L2 是分类入口，L3 才是可复制的场景。
9. As a skill 拥有者，我跑一次 `python3 scripts/render_help.py`，so that `$DATA_DIR/.../biscuit_accountant_html/` 自动出现新 timestamped HTML，根目录 `饼干记账.html` 自动覆盖成一致内容——不需要 `cp` 手动同步。
10. As a skill 拥有者，我修改 `templates/help.html` 后再跑 `render_help.py`，so that 下次 `help` 命令的输出立刻是新版，无需重启/手动操作。
11. As a 未来维护者，`templates/help.html` 第 3 行注释里的版本号保持 `v2.4`，so that 看到代码的人不会误以为"数据契约变了"。
12. As a 未来维护者，v15 的 9 轮迭代历史（v6→v15）保留在 `D:\2Study\StudyNotes\workspace\biscuit_help_v*_完整版.html`，so that 后续要回看设计决策时有据可查。
13. As a 未来维护者，现有 `tests/test_render.py` 的 4 个 `test_help_html_*` 用例在 v15 落地后**继续通过**，so that 渲染契约没破。
14. As a 未来维护者，v15 落地后 v15 模板的 `<!--INJECT-DATA-->` 占位符**唯一**存在（数量 = 1），so that `render_help.py` L124 那条 `ValueError` 不会误触发。
15. As a Windows 老旧工具用户（记事本/PS 5.1），HTML 输出仍带 UTF-8 BOM，so that 不会出现"打开是乱码"。
16. As a 未来维护者，我不需要修改 `render_help.py` 的 `enrich_scenarios()` / `inject_payload()` / `default_output_path()`，so that 数据流核心路径不动，降低回归风险。
17. As a 未来维护者，auto-copy 写入的 `饼干记账.html` 跟 timestamped 输出**内容一致**（除了路径/时间戳字面量），so that 看到两份文件的逻辑等价。

## Implementation Decisions

### 决策 1：模板是 seam，所有 v15 改动收敛到 `templates/help.html`

- 把 v6→v15 的 9 轮迭代结果（保留在 `D:\2Study\StudyNotes\workspace\biscuit_help_v15_完整版.html`）拆出 `<style>...</style>` 和 `<script>...</script>` 两段
- 替换 `templates/help.html` 的 CSS 和 JS body
- 把 v15 文件里 `<script id="payload" type="application/json">...</script>` 占位符化回 `<!--INJECT-DATA-->`（这样 `render_help.py` 还能注入）

### 决策 2：`renderScenario` 函数去掉 `dimBadges`

v15 模板里 `renderScenario` 改为只渲染 `<span class="sc-title">`、可选的 `<span class="sc-pending-tag">【待开发】</span>`、和 `<button class="copy-btn copy-sc">📋 复制</button>`，**不**再 `Object.entries(dims).map(...)` 生成维度 badge。

### 决策 3：移动端 CSS 用回 flex（v13 的 grid 是为两行 layout 服务的）

v15 删了维度标签后，summary 行只剩 3 个元素（arrow / title / copy），用 `display: flex; flex-wrap: wrap` 即可，不需要 v13 的两行 grid。

### 决策 4：模板头部版本号保持 v2.4

`templates/help.html` 第 3 行的 `v2.4` 注释不动。理由：版本号绑定数据契约（`scenarios.json._meta.version`），CSS/JS 重构不影响契约。如果未来加新字段或改 schema，再 bump 到 v2.5。

### 决策 5：auto-copy 是 3 行代码，附在 `render_help.py` 末尾

```python
# 同步一份到 SKILL 根目录(SKILL.md L10 强制要求)
skill_root_copy = SKILL_DIR / "饼干记账.html"
skill_root_copy.write_text(html, encoding="utf-8-sig")
print(f"✓ 已同步: {skill_root_copy}  (SKILL.md L10 镜像)")
```

放在 `output_path.write_text(html, encoding="utf-8-sig")` 之后，**且**不放在 `if args.check` 分支内（`--check` 是 dry-run，不该写盘）。`--out` 指定路径时**也**执行 auto-copy（因为 output 的是同一份 HTML）。

### 决策 6：保留 v6-v14 历史文件

`D:\2Study\StudyNotes\workspace\biscuit_help_v*_完整版.html` 一律保留（设计史参考），不被 auto-copy 覆盖，也不需要人工归档。

## Testing Decisions

### 验收 seam（最高级，理想 = 1）

> 跑一次 `python3 scripts/render_help.py`，然后：
> 1. 读 `$DATA_DIR/.../biscuit_accountant_html/饼干记账_HELP_<TS>.html` —— 含 `<!--INJECT-DATA-->` 已被替换的 `<script id="payload">`、BOM 开头
> 2. 读 skill 根目录 `饼干记账.html` —— 与上者内容等价（按字节或忽略时间戳字面量后）
> 3. 在两个文件里都不应再出现 `sc-dim` 这个 class 名（v15 删了维度标签）
> 4. 4 条 HELP 唤醒词（`饼干记账 HELP` / `饼干记账 帮助` / `查帮助` / `能做什么`）都还在 payload 里

### 用现有 seam 扩展测试

`tests/test_render.py` 的 `class TestHelpHtmlRender` 是黄金 seam——4 个 `test_help_html_*` 已经跑通了 BOM / 唤醒词 / 文件名验证。**扩展**这 4 个用例或追加 2 个新用例：

- `test_help_html_no_sc_dim` —— 验证渲染输出不含 `class="sc-dim"`
- `test_help_html_root_mirror_synced` —— 验证根目录 `饼干记账.html` 被 auto-copy 覆盖（与 timestamped 文件内容一致）

### 不测什么

- **不**测 CSS 像素级匹配（视觉回归）—— 那是 Playwright 截图比对的工作，超出本 spec 范围。v6→v15 的视觉验证已在 workspace 里有 `_debug/v15_*.png` 截图归档。
- **不**测具体的颜色 / 字号 / padding 数值 —— v15 调好的 CSS 在 workspace 截图里已确认，无需在 CI 里复测。
- **不**测 `render_help.py` 的边界（空 scenarios.json / 异常路径）—— 已有 `test_summary_on_empty_db` 等覆盖。

### 已知问题（不阻塞落地）

- 现有 4 个 `test_help_html_*` 用例依赖 fixture 临时 DB 路径隔离，**auto-copy 写根目录的 `饼干记账.html` 不在 fixture 隔离范围内**。新加的 `test_help_html_root_mirror_synced` 用例**必须**在 setup 里备份原 `饼干记账.html`、teardown 里恢复——避免污染真实 skill 根目录。

## Out of Scope

- 修改 `references/scenarios.json` 的 schema（`dimensions` 字段保留，v15 不渲染但未来可能用）
- 增加 / 删除场景
- 修改 `SKILL.md` 内容（除了验证 auto-copy 注释跟 L10 一致外，不动）
- 把 `render_help.py` 重构成 class / 加 CLI 子命令
- 把 v15 的 CSS 拆成外部 `.css` 文件（保持单文件 HTML 离线可看的特性）
- 改 `html_paths.py` 的 HELP 文件名约定（已对齐 §12.B）
- 删 v6-v14 的 workspace 旧文件（保留作设计史）
- 给 v15 加新的视觉回归测试（CI 化是另一个 spec 的事）
- 改 `tests/conftest.py` 的 fixture 体系

## Further Notes

### 1. 设计决策出处

v15 不是凭空产生的，是 v6→v15 共 9 轮迭代的结果。设计记录在 `D:\2Study\StudyNotes\workspace\biscuit_help_v11_设计说明.md`（5.2KB，含问题回顾 / 迭代过程 / 真凶分析 / 权衡代价）。后续要回看决策，**先读那份说明**，胜过读代码注释。

### 2. 为什么 auto-copy 在 grill 阶段才被发现

`SKILL.md` L10 写"必须同步更新"，但**没说怎么同步**——隐含"人工"。grill session 把"应该"翻成"自动"是这次的一个 side win：把规则从文档下沉到代码，从根上避免再忘记。

### 3. v15 删了维度标签，但没删 `.sc-dim` CSS

`.sc-dim` 样式在 v15 模板里仍是孤儿 CSS（没 DOM 使用）。可作为后续 cleanup，但本 spec 不要求做——避免无意义的 diff，落地后单独提 ticket。

### 4. v15 的 mobile CSS 演化轨迹

v12: 复制按钮从 sc-content 上移到 summary（inline `onclick` + `[open]` 时 `display: none`）
v13: 移动端 summary 用 grid 强制两行（title + dims）
v15: 删 dims 后回到 flex（grid 没必要了）

v13 的 grid 代码**仍会**出现在 v15 模板里——因为 v15 是覆盖式落地，v13 的 grid CSS 被 v15 的 flex 覆盖。模板里不会留 v13 残留。

### 5. 关于 from-first-principles 的几行备注

`grill-with-docs` session 的核心价值不是问出答案，是逼出"我以为是 A，其实是 B"的几条事实修正（本 spec 里最关键的一条：根目录 `饼干记账.html` 不是脚本自动同步的，是 CONTEXT.md 写明的手工同步）。代码就是事实，文档也是事实，认知假设不算。落地前要分清这三者。
