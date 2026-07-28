# 01 — env 链解析 + 12.A 自动命名(单 template tracer)

**Status:** resolved
**Resolved:** 2026-07-28

## Answer

Implemented in `scripts/render/__init__.py`:
- New `resolve_output_root()` resolves env chain `$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > fallback
- New `_fallback_output_root()` mirrors `home_manager.db._fallback_db_dir` strategy (Windows: `D:/.db`, WSL: `/mnt/d/.db`)
- New `_auto_output_path(template_name)` constructs auto-named path: `<root>/home_manager_html/<command_cn>_<YYYYMMDD>_<HHMMSS>.html` using `datetime.now()` (local time per ADR-0001)
- `render_page()` now calls `_auto_output_path()` when `output_path` is None
- `--output <path>` override branch unchanged
- Same-name file overwrite behavior preserved (no `_N` suffix, per SKILL.md §输出位置 declaration)
- Subdir `home_manager_html/` auto-created via `mkdir(parents=True, exist_ok=True)`

Tests added in `tests/test_render.py` (8 new, all green):
- test_12a_autonaming_with_skills_data_dir
- test_env_chain_skills_db_path_fallback
- test_env_chain_priority_data_dir_over_db_path
- test_output_override_bypasses_autonaming
- test_local_time_timestamp_matches_now
- test_overwrite_same_name_file
- test_subdir_autocreate
- test_filename_no_reserved_chars

End-to-end verified: `python home_manager.py search --name 牛奶` produces `D:\.db\home_manager_html\查物品_20260728_145233.html`.

## What to build

(Original ticket body preserved below)

**What to build:** 跑 `python home_manager.py search`(不带 `--output`)后,生成的 HTML 文件落到 env 链解析的根目录下的 `home_manager_html/` 子目录,文件名形如 `查物品_<YYYYMMDD>_<HHMMSS>.html`(本地时间),覆盖旧文件不报错,`--output <path>` 显式 override 仍能写到指定路径绕过自动命名。本 ticket 只需让 `search_results` 这一个 template 走通整条链,command_cn 可硬编码"查物品"先不查映射表。

**Blocked by:** None — can start immediately

- [x] `render_page("search_results.html", ok_payload)` 不传 output_path → 文件落在 `<env_root>/home_manager_html/查物品_<YYYYMMDD>_<HHMMSS>.html`
- [x] env 链优先级:`$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > Skill 自带 fallback(沿用 `home_manager/db.py` 的 fallback:Windows `D:\.db\`,WSL `/mnt/d/.db/`)
- [x] `monkeypatch.setenv("SKILLS_DATA_DIR", tmp_path)` → 输出在 `tmp_path/home_manager_html/`
- [x] unset `SKILLS_DATA_DIR`,`monkeypatch.setenv("SKILLS_DB_PATH", tmp_path)` → 输出在 `tmp_path/home_manager_html/`
- [x] `render_page(..., output_path=str(tmp_path/"custom.html"))` → 写到 custom.html,不触发自动命名,不强制 home_manager_html/ 子目录
- [x] 时间戳用 `datetime.now()`(本地时间,见 ADR-0001),接近测试执行时刻(允许 1 秒误差)
- [x] 时间戳格式正则 `^\d{8}_\d{6}$`
- [x] 子目录不存在时自动 `mkdir(parents=True, exist_ok=True)`,不抛异常
- [x] 同名文件已存在时,`write_text` 直接覆盖,不报错,内容为新版本
- [x] 文件名不含 `/ \ : * ? " < > |`(command_cn "查物品" 自然满足)
- [x] 现有 9 个 test_render.py 测试(都传显式 output_path)继续通过 —— 新逻辑不影响 override 分支
