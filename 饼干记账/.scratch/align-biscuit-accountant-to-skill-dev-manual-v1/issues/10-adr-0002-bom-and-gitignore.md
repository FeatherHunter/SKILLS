# 10 — ADR-0002 归档 HTML BOM 修复 + `.gitignore` 补 `*.bak`

**What to build:** 未来读者在 `docs/adr/0002-utf-8-bom-for-html-output.md` 看到 BOM 决策的原因（Windows 老旧工具按 GBK 误判；浏览器认 `<meta charset="UTF-8">` 但记事本/PowerShell ISE 不认）—— 让这一历史决策可追溯。`.gitignore` 排除 `*.bak` 后仓库不再带历史包袱。

**Blocked by:** None — 决策已发生，归档是记录

**Status:** ready-for-agent

- [ ] `docs/adr/0002-utf-8-bom-for-html-output.md` 存在，含 Status / Context / Decision / Consequences 四段
- [ ] `.gitignore` 加 `*.bak`
- [ ] 旧 `.bak.20260723_*` 两个文件归档到 `backups/` 目录而非删除（一次性）
- [ ] 不修改 `bill_inject.py` / `render_help.py` / `record_bill.py` 的 BOM 实现（已在 spec §Implementation Decisions #10 落地）