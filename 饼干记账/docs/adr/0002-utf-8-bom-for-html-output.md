# ADR-0002: HTML 输出文件加 UTF-8 BOM

## Status

accepted — 2026-07-28

## Context

`bill_inject.py` / `render_help.py` 输出的 HTML 文件被 Windows 老旧工具（记事本 / PowerShell 5.1 ISE）按 GBK/cp936 误判打开，导致中文显示为乱码（如 `饼干记账 · 查询视图` → `?? ??`）。

浏览器（Chrome / Edge / Firefox / Safari）认 `<meta charset="UTF-8">`，没有 BOM 也能正确渲染。但本 Skill 的输出 HTML 经常被用户在 Windows 资源管理器双击 → 默认用记事本 / Edge 打开；记事本在 Win10 1903 之前不认 `<meta charset>`，按系统 ANSI（中文 Windows = cp936/GBK）解析 → 乱码。

用户看到乱码后会怀疑 Skill 损坏，而不是工具问题，造成信任损耗。

## Decision

**给所有 HTML 输出文件加 UTF-8 BOM（3 字节 `EF BB BF`）**，使用 Python `encoding="utf-8-sig"` 写入：

- `bill_inject.py` `inject_to_template()` → `output_path.write_text(html, encoding="utf-8-sig")`
- `render_help.py` `main()` → `output_path.write_text(html, encoding="utf-8-sig")`
- `scripts/migrations/add_bills_check_constraints.py` `_backup_bills_csv()` → `open(csv_path, "w", encoding="utf-8-sig", newline="")`（CSV 备份同处理）
- `record_bill.py` 顶部加 `sys.stdout.reconfigure(encoding="utf-8")` 防 cp936 污染 stdout

## Consequences

- **优点**：
  - 记事本 / PowerShell ISE 直接双击打开 HTML 不再乱码
  - Excel 打开 CSV 备份不再乱码
  - 浏览器仍正常渲染（BOM 是可选的，浏览器认 `<meta charset="UTF-8">` 优先）
- **代价**：
  - HTML 文件首 3 字节为 BOM（极小开销，~3 字节/文件）
  - 某些严格 XML 解析器会警告 BOM（本 Skill 输出的是 HTML5，非 XML，无影响）
  - 测试需断言 `bytes[0:3] == b'\xef\xbb\xbf'`（已落地于 `tests/test_render.py::TestBomBytes`）

## Follow-up

- [x] `tests/test_render.py::TestBomBytes::test_summary_html_has_bom` 校验 BOM 字节序列
- [x] `tests/test_render.py::TestNineQueryTypesRender` 9 类 query_type 全部含 BOM
- [x] `tests/test_render.py::TestHelpHtmlRender::test_help_html_has_bom_and_payload` HELP HTML 含 BOM
- [x] `.gitignore` 排除 `*.bak`（一次性备份文件不再进仓）
- [ ] 历史遗留 `.bak.20260723_*` 文件归档到 `backups/`（一次性，不删）
