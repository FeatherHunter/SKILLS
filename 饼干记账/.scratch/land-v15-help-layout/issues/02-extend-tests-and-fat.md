# 02 — 扩展 `tests/test_render.py` 验收 seam + 跑全套 FAT

**What to build:** `pytest tests/test_render.py -k help` 跑 6 个用例全过：4 个老的 `test_help_html_*`（BOM / 4 条唤醒词 / 文件名前缀 / 4 条 HELP 唤醒词）守住既有契约，2 个新增的（`test_help_html_no_sc_dim` 守住"v15 不渲染维度标签"、`test_help_html_root_mirror_synced` 守住"根目录自动同步"）守住 v15 新增契约。auto-copy 写根目录的副作用**不**污染真实 skill 根目录（fixture setup/teardown 备份恢复）。

**Blocked by:** 01 — 落地 v15 template + auto-copy

**Status:** ready-for-agent

- [ ] `tests/test_render.py` 的 `class TestHelpHtmlRender` 加新方法 `test_help_html_no_sc_dim(tmp_db_dir)`：
      - 跑 `_run_render_help(tmp_db_dir)` 拿到 timestamped HTML
      - 读文件内容，断言**不**含 `class="sc-dim"`
      - 断言含 `class="sc-title"`（确保 v15 模板真的渲染了场景卡，而不是被破坏到不渲染）
- [ ] 同 class 加新方法 `test_help_html_root_mirror_synced(tmp_db_dir)`：
      - setup: 备份 skill 根目录的 `饼干记账.html`（如存在）到 `tmp_db_dir / "biscuit_root_backup.html"`
      - 跑 `_run_render_help(tmp_db_dir)`，render_help.py 末尾 auto-copy 会把同一份 html 写到 skill 根目录
      - 断言：skill 根目录 `饼干记账.html` 存在
      - 断言：根目录文件以 UTF-8 BOM 开头
      - 断言：根目录文件不含 `class="sc-dim"`（守住 v15 布局契约同步过去了）
      - 断言：根目录文件跟 timestamped 文件的 payload 段（`<script id="payload">...</script>` 内的 JSON）字节一致
      - teardown: 恢复备份的原 `饼干记账.html`
- [ ] 新增用例的 `_run_render_help` 调用**不**传 `--out` 参数（让 `default_output_path()` 走默认路径，触发 auto-copy 到 SKILL 根目录）
- [ ] 跑 `pytest tests/test_render.py -k help -v`：
      - 6 个用例全部通过（4 老 + 2 新）
      - 没有任何 skip / xfail
- [ ] 跑完整 `pytest tests/test_render.py`（不限于 help），确保 4 个老的 `test_help_html_*` 仍通过（**没**被 v15 改动破坏）
- [ ] **不**删 `_assert_html_well_formed()` 这个 helper（其他用例还在用）
- [ ] **不**改 fixture 体系（`conftest.py`、`tmp_db_dir`）—— 只在新增的 2 个方法内做 setup/teardown
- [ ] 跑完测试后，确认 skill 根目录的 `饼干记账.html` 已被恢复成测试前的状态（setup/teardown 正确）
- [ ] 跑一次手动 FAT（不在 pytest 范围内）：在 `SKILLS_DB_PATH=/tmp/test_db` 下执行 `python3 scripts/render_help.py`，用浏览器（或 Playwright headless 截图）打开 timestamped 输出，肉眼检查 v15 布局（手机视口 + 桌面视口各看一次）—— 把截图保存到 `D:\2Study\StudyNotes\workspace\_debug\v15_landing_<viewport>.png` 作落地证据
