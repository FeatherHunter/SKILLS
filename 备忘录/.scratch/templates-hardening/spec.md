# Spec · templates/ 防御性硬化(grill 决策 R2 落地)

> 来源:grill session R2(2026-07-29,备忘录 templates 对抗式审查)。本 spec 不再 interview,把已经决策清楚的 26 个问题一次性收敛为可执行 spec。issue tracker / TBD 字段已用"-(参考 grill 决议清单)"占位,等 to-tickets 阶段吸走。

## Problem Statement

备忘录 skill 的 `templates/` 目录下,6 个 HTML 模板(memo_query / sync_report / wish_plan / wish_complete / change_category / memo_help)在历史演化中积累了一组被对抗式审查验证的实质问题:引用未定义函数(JS 一点击即崩)、`escapeHTML` 与反序列化不对称(用户写 `<b>` 即静默失败)、全文 substring 搜索把 UUID/ID 当关键字命中导致"永真"过滤、过程型 HTML 的核心「采纳」按钮落在长 fold 之外、`.from{color:#err-soft}` 把"原分类"染色为"危险"造成情绪化认知——以及更根源地:**这些模板层 JS Bug 从未被 `tests/` 捕获**,因为测试只覆盖 CLI→JSON→path 渲染管道,不感知浏览器内 JS 行为。

**用户层影响**:跨设备使用备忘录时,搜索结果与用户心智不符、复制单条记录经常"复制失败"、批量排期向导采纳按钮需滚动查找、视觉状态区分弱导致用户错过关键提示。**架构层影响**:模板层 JS 改动无任何静态校验屏障,后续错误会以"用户报告"形式回流,而非被 pre-commit 拦截。

## Solution

用**单一最高 seam**——pre-commit hook + 一份 pytest 文件(`tests/test_template_lint.py`)——同时承载三类静态规则,守住 templates/ 的 11 条总纲原则(§04)不再次溃散。然后把所有 26 个已知问题按 Phase B/C 一次性修,回归到 4 状态 fallback 守护 + 新的 lint 守护之下。

**核心 seam 选择**:不增加 6 个模板各自 inline JS 的可观测性(=得新建 Playwright + 浏览器二进制,违反"纯 Python 仓库"约束),改为 **静态文本扫描**(Python `re` + 简单 AST-like 规则),无缝接入已有 `pytest` 测试栈与 `.githooks/pre-commit`。

## User Stories

1. As a 备忘录用户,我希望在搜索框输入 "心愿" 时只匹配内容的 "心愿" 二字,不被 UUID/ID 巧合污染,以便结果符合预期
2. As a 备忘录用户,我希望点 "复制" 按钮后 100% 可复制成功(包含我粘贴代码片段备忘),以便我不会反复看到"复制失败"灰色提示
3. As a 备忘录用户,我希望批量排期向导的"采纳"按钮无须滚到 fold 之外,就能完成采纳动作,以便我能快速完成多选后排期
4. As a 备忘录用户(批量改分类场景),我希望看到 "原分类 → 新分类" 时不被红色恐惧暗示干扰,以便我做平静的批量决策
5. As a 备忘录用户,我希望在同步报告里第一屏就看出"完成 / 排期 / 跳过"三块状态分布,以便 3 秒内做出后续动作判断
6. As a 备忘录用户(键盘 / 屏幕阅读器用户),我希望搜索框能被屏幕阅读器读出 "在结果内搜索",以便我能用键盘 + a11y 使用过滤
7. As a 备忘录用户,当我浏览 HELP 长目录时,希望有回到顶部按钮,以便不必手动滚回
8. As a 备忘录开发维护者,我希望在 CI/pre-commit 阶段就拦住"模板 JS 引用未定义函数"这一类错误,以便错误不流向用户
9. As a 备忘录开发维护者,我希望"escape / unescape 对称"的检查是自动的,以便修复 L60 这类反序列化不对称 bug 后不再次回潮
10. As a 备忘录开发维护者,我希望"隐藏复制按钮 = 单工铁律违反"是 CI 拦得住的,以便新人提交时不会写出违反总纲 §04 原则 10 的代码
11. As a 备忘录开发维护者,我希望搜索框"全文 substring vs 字段级"的语义选择有 CONTEXT.md 留痕,以便未来有人重写时不偏离意图
12. As a 备忘录开发维护者,我希望 templates 下 6 个文件的命名(镜像 / 渲染产物)有清晰术语区分,以便 SKILL.md 引用时不会错类
13. As a 备忘录开发维护者,我希望回归测试在每次 templates/ 改动后自动跑,以便不引入回归
14. As a 备忘录开发者,我希望 process 型 HTML 的"采纳"按钮由 static 浮动到我一眼能看到的位置,以便我采纳后不必再找上一份回执去比对
15. As a 备忘录用户,当 wish_plan 生成的 prompt 超长时,我希望看到完整 prompt(不被 340px 截断),以便我能完整复制 AI 指令
16. As a 备忘录用户,我希望 memo_help 的标题文案始终一致(eyebrow / h1 / title 三处统一),以免视觉与品牌出现错位
17. As a 备忘录用户,我在 memo_query 看到长列表(>50 条)时,希望有 "首 50 条 / 全部" 的展示模式切换,以便我不被海量记录刷屏
18. As a 备忘录用户,我在 wish_complete 给所有勾选心愿批量套同一打卡内容时,希望知道哪些已被覆盖、哪些保留原值,以便我没把握时不会误覆盖
19. As a 备忘录用户,在 wish_plan 切换 checkbox 时,希望"已勾选=line-through"是视觉明显的(而非"未勾选 line-through"这种反心智),以免误读操作方向
20. As a 备忘录开发者,看到 sync_report 的 KPI 顶条颜色(完成 / 排期 / 跳过)时,希望快速区分三档,以便在低亮度屏也能一眼读出差异
21. As a 备忘录用户,在 sync_report 第一屏里我希望看到状态结论 + 一行话概要,而不是滚动去看变化明细,以便我先形成结论再看细节
22. As a 备忘录开发者,看到 templates/ 时希望能区分"哪些是 SKILL.md 的 HTML 镜像(memo_help)、哪些是渲染产物(其余 5 个)",以便引用 SKILL.md §HTML 时不混类
23. As a 备忘录开发者,我希望"复制按钮存在且有反馈"是 templates 层 lint 必查项,以便任何新模板违反单工铁律时立即被拦截
24. As a 备忘录开发者,我希望 escapeHTML 函数做 5 个 entity,反序列化也解 5 个 entity 是 lint 必查的对称性,以便 L60 这种反序列化缺陷不再回潮

## Implementation Decisions

### 决策 1 · 静态扫描基础设施
- **seam**:`tests/test_template_lint.py` 一个文件 + 一个 `tools/template_lint.py`(供 lint 自检与 CLI 单独调用)— 整体跑在已有 pytest 栈中,pre-commit 自动触发
- **三类规则**:
  - **规则 1 · 引用未定义函数**:扫描 inline `<script>`,提取所有调用函数名,对照文件中所有 `function name(...)` 定义,报警未定义引用。`memo_query` L61 `copyText` 不存在属此类
  - **规则 2 · escape/unescape 对称**:扫描同模板内 `esc(`/`escapeHTML(` 与 `.replace(/&[#\w]+;/g, ...)`,检查反序列化 entity 集合 ≥ 转义 entity 集合,否则报警。`memo_query` L60 反解 2 entity 而 esc 输出 5,属此类
  - **规则 3 · HTML 单工铁律**:扫描模板 `.copy-btn`/`.copy` 选择器及对应 `onclick=`/`.addEventListener('click'`,检查所有"交互按钮"是否有对应的复制 fallback(`document.execCommand` fallback 或 alert 或 toast),否则报警。"采纳"按钮不暴露则属此类
- **不动模板本体内的 `esc()` 函数名**(避免侵入式重命名,规则用 regex 检测行为而非依赖函数名)

### 决策 2 · CONTEXT 术语新增(已落地)
- 新增"渲染产物 (render artifact)":templates/ 下 5 个非镜像 HTML 的统称,与"HTML 镜像"严格分离
- 新增"模板静态扫描 (template lint)":本 spec 决定的基础设施术语
- 新增"搜索意图 (search intent)":grill 决议 R2-4 memo_query 搜索语义沉淀

### 决策 3 · Commit 粒度
- 拆 3 个 commit(单 phase 一笔,可独立 revert):
  - `phase-A` 基础设施(lint + 测试 + 守护)
  - `phase-B` 真 Bug 修复(L61/L60/L50 等 12 项)
  - `phase-C` UI 一致性(「采纳」sticky / 视觉反转 / 颜色克制 / 状态条等 9 项)
- 全中文 commit 信息,遵守 `docs/adr/0003-b-execution-fallback.md`

### 决策 4 · 搜索语义(用户拍板)
- `memo_query.html` 搜索框**仅匹配 `note.content`** 字段
- 同时显式取消对 `id` / `feishu_task_guid` / `created_at` / 其他内部字段的命中
- 锁在 `tests/test_template_lint.py` 加一条 fixture 测试:输入 content 不含搜索词 + id/UUID 含搜索词的样本,断言搜索结果为空

### Phase B · 26 个真 Bug 修复细节(12 项,8 个本轮 spec 收敛到不修或推迟)
- B1 memo_query L61 `copyText` 实现:`navigator.clipboard.writeText(receiptText()).then(...)`,失败 fallback 到 `document.execCommand('copy')` textarea 选区(防 webview 拒绝)
- B2 memo_query L60 反序列化对称:补全 5 entity 反解(`&lt;` `&gt;` `&quot;` `&#39;` `&amp;`)
- B3 memo_query L50 搜索 = content only(决策 4)
- B4 memo_query KPI "有附件" → 后端如未返字段,降级显示 "—" 而非 0(不隐瞒契约破缺)
- B5 memo_query `<input>` 加 `<label for="filter">` + `aria-label` 双重 a11y
- B6 wish_* / change_category 复制 callback 加 `document.execCommand('copy')` textarea fallback
- B7 wish_* / change_category btn 文字 timer 链加 `clearTimeout`
- B8 memo_help `<title>` / eyebrow / h1 三处命名统一为"Memo Help"(eyebrow,英文) / "备忘录 · 使用手册"(h1) / `备忘录 · HELP 使用手册`(browser title)
- B9 memo_help sticky 「回到顶部」按钮(右下,floating,scroll-to-top 平滑)
- B10 wish_plan L53 `onclick=setCat('${esc}')` → 改为 event delegation 模式,避免 HTML attribute context 下 entity 不被 JS 解析
- B11 memo_query 长列表:加 "首 50 条 / 显示全部" 切换(50 是明示阈值,不放无限)

### Phase C · UI 一致性(决策 1-4 之外的克制对齐)
- C1 wish_plan / wish_complete / change_category 「采纳」按钮 → sticky 浮动到底部(viewport-bottom,带 safe-area-inset)
- C2 wish_* checkbox `.off` class 语义反转:line-through 从"未勾"移到"已勾"(.off 改 .on)
- C3 change_category `.from{background:#err-soft}` → 中性灰 `.from{background:var(--bg)}` 加 1px border
- C4 wish_plan `pre#promptOut` 删 `max-height:340px`(防止 AI 提示截断)
- C5 sync_report KPI 顶条 3px → 4px + 状态卡 6px accent bar(左缘条,显著)
- C6 sync_report 状态卡 ok/warn 渐变色相近 → 强化色相(ok 偏绿豆沙,err 偏粉,数量级差异 ≥2)
- C7 6 模板统一 KPI 字号比:数字 22-24px / label 13px / hint 11px(数字与标签比 ≤ 1.8)
- C8 sync_report 信息流重排:KPI 4 卡紧邻状态卡之下,明细区统一在最底部(避免 KPI-详情-KPI 跳动)
- C9 sync_report 命令字段中文化(保留 `--html` 等 CLI 参数原样,command 显示字段改为中文 alias)

### 撤回项(grill R2 已判为非 Bug,本 spec 不再处理)
- ❌ wish_complete L142 placeholder 渲染 `&#39;` 的"修复"(实测 attribute context 自动 decode,正常)
- ❌ wish_complete badge 颜色(已无冲突)
- ❌ wish_plan footer 核心承诺挖底(改为 hero 区 chip 提示)

### 接口契约
- `tools/template_lint.py` 暴露 3 个函数入口:`lint_undefined_funcs(template_text)` / `lint_escape_asymmetry(template_text)` / `lint_copy_fallback(template_text)`,每个返回 `list[(line_no, severity, message)]`
- `tests/test_template_lint.py` 暴露一个公共 fixture:`templates_dir()`,被 6 个测试类复用

## Testing Decisions

### 什么是"好测试"(本 spec 范畴)
- **只测外部行为**:静态扫描的"报错触发"是可见输出,不要测实现细节(tokenization 算法用哪个库)
- **不测 模板的渲染结果**(渲染测试由 `tests/test_render.py` 覆盖,本 spec 仅补 lint 维度)
- **回归测试不重复**:`test_template_lint.py` 每个 bug 写一个 fixture 钉死,体现"今时今日此 bug 不能复活"

### 测试模块清单
- `tests/test_template_lint.py`(新建)
  - `TestUndefinedFuncs`:parse fixtures(6 个模板各一)+ 用户已有 fixture:`test_memo_query_copytext_undefined` 等
  - `TestEscapeAsymmetry`:扫描 `esc(`/`escapeHTML(` 调用,断言反序列化 regex 覆盖 ≥ 5 entity
  - `TestCopyFallback`:扫描 `<button>` 节点 + 对应 handler,断言无 handler 的按钮报警
- `tests/test_render.py`(既有,Phase B/C 改动后回跑)
- `tests/test_4_state_fallback.py`(既有,Phase C 状态卡收敛后回跑)

### Prior Art
- `tests/test_render.py` 已有的 placeholder & 注入测试 = 现成的"模板无污染 / 注入器稳定"测试范式,直接复用 `[name]_template_path` fixture 模式
- `tests/test_4_state_fallback.py` 已有的"显式 success / empty / missing_data / error 标记" = lint 测试的违例检测思路可借鉴

## Out of Scope

- HTML 渲染性能的浏览器层压测(本 spec 不入 Playwright)
- ESLint / Node 工具链引入(保持 Python 纯栈)
- templates/ 6 个文件的视觉设计风格统一(Apple 风已有,本 spec 只修具体问题)
- 数据后端契约的扩展(同步报告等只展示现有 payload,不新增字段)
- 用户在浏览器之外的场景(LINE / Telegram 等)复用 templates(本 spec 仅覆盖 webview + 浏览器)

## Further Notes

### ADR 候选(to-spec 阶段决策)
- **决策 1**(模板静态扫描基础设施)— 三条件成立:hard to reverse(git 不可回退)✓ / surprising without context(新人会问"为什么") ✓ / real trade-off(选 ESLint/slimit/纯 regex 三选一)✓ → **建议 to-tickets 阶段建 `0006-template-lint-infrastructure.md`**
- 决策 2-4 不需 ADR,已沉淀为 CONTEXT.md 3 个术语

### 与已有 ADR 的关系
- `0001-version-sot.md` 本 spec 不动版本号,继续单文件版演
- `0003-b-execution-fallback.md` 本 spec 所有 commit 全中文 + Tested-By 守护行
- `0004-a-structure-files.md` 本 spec 的 `tools/` 与 `tests/` 落在 memo_cli 既有根约定之内
- `0005-d-exemptions-and-rituals.md` 本 spec 的 Tested-By = `pytest tests/ -q`(由 pre-commit 自动跑,可豁免)

### Grill 收尾输入到 to-tickets
本 spec 的 Phase A/B/C 是 3 段连续执行(每段一笔 commit),由 to-tickets 拆为 30+ vertical-slice tickets,每 ticket 配:
- 1 个 spec.md 引用段
- 1 个 verify.md 守护段
- 1 个 acceptance checklist(含测试调用点)
