# 01 — 落地 v15 template + render_help.py auto-copy

**What to build:** 跑一次 `python3 scripts/render_help.py` 后，输出到 `$DATA_DIR/.../biscuit_accountant_html/饼干记账_HELP_<TS>.html` 的 HTML 是 v15 布局（无 `.sc-dim` 维度标签、场景折叠态名字右边有复制按钮、移动端 flex 单行布局、文字左对齐），同时 skill 根目录的 `饼干记账.html` 被 auto-copy 同步成一致内容。SKILL.md L10 规定的"功能变更必须同步更新"从规则下沉为代码。

**Blocked by:** None — 核心代码改动，可与 02 解耦开始

**Status:** ready-for-agent

- [ ] 从 `D:\2Study\StudyNotes\workspace\biscuit_help_v15_完整版.html` 抽出 `<style>...</style>` 和 `<script>...</script>` 两段
- [ ] 把 v15 文件里 `<script id="payload" type="application/json">...</script>` 替换回 `<!--INJECT-DATA-->` 占位符
- [ ] `templates/help.html` 第 3 行注释保留 `v2.4`（版本号绑定数据契约，不绑定实现）
- [ ] `templates/help.html` 中除头部注释 + 实际 CSS/JS body 外其他部分一致替换为 v15 内容
- [ ] `templates/help.html` 里 `<!--INJECT-DATA-->` 占位符**唯一**存在（1 个，触发 `render_help.py` L124 的 `ValueError` 防御）
- [ ] `templates/help.html` 内的 `renderScenario` 函数不再生成 `dimBadges`（去掉 `Object.entries(dims).map(...)` 整段）
- [ ] 模板里的 `renderScenario` 仍渲染 `<span class="sc-title">`、可选的 `<span class="sc-pending-tag">【待开发】</span>`、`<button class="copy-btn copy-sc">📋 复制</button>` 三个元素
- [ ] `scripts/render_help.py` 末尾（`output_path.write_text(...)` 之后、`if __name__` 之前）追加 3 行：
      ```python
      # 同步一份到 SKILL 根目录(SKILL.md L10 强制要求)
      skill_root_copy = SKILL_DIR / "饼干记账.html"
      skill_root_copy.write_text(html, encoding="utf-8-sig")
      print(f"✓ 已同步: {skill_root_copy}  (SKILL.md L10 镜像)")
      ```
- [ ] 上述 auto-copy 块**不**在 `if args.check:` 分支内（`--check` 是 dry-run，不该写盘）
- [ ] 跑 `python3 scripts/render_help.py --check` 退出码 0，stderr 无异常
- [ ] 跑一次 `python3 scripts/render_help.py`（设 `SKILLS_DB_PATH` 到临时目录避免污染真实 DB）后：
      - `$DATA_DIR/.../biscuit_accountant_html/饼干记账_HELP_<TS>.html` 存在
      - skill 根目录 `饼干记账.html` 存在
      - 两个文件以 UTF-8 BOM (`\ufeff`) 开头
      - 两个文件都不含字符串 `class="sc-dim"`
      - 两个文件都含 `class="sc-title"`
      - 两个文件都含 `class="copy-btn copy-sc"`
      - 两个文件的 payload 部分（`<script id="payload">...</script>`）字节完全一致
- [ ] **不**修改 `references/scenarios.json`（`dimensions` 字段保留，v15 不渲染但未来可能用）
- [ ] **不**修改 `scripts/html_paths.py`（HELP 路径命名约定已对齐 §12.B）
- [ ] **不**修改 `scripts/bill_inject.py`（跟 help 无关）
- [ ] **不**修改 workspace 里 `biscuit_help_v6`-`v14_完整版.html`（保留作设计史）
- [ ] **不**修改 SKILL.md / CONTEXT.md（documentation 留到 03 之后另开 ticket）
