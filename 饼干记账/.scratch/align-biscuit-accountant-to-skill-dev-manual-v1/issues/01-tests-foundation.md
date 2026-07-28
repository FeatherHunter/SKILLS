# 01 — 建立 `tests/` 测试地基

**What to build:** 端到端可跑的 pytest 环境，给后续 9 类 query_type 回归 / 注入层安全 / FAT 协议提供共享 fixture（临时 SQLite DB 含 30 条 sample_bills 含空数据 / 跨月 / 跨年、临时 HTML_DIR、临时 CLI 子进程 wrapper）。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `tests/conftest.py` 存在，含 3 个 fixture：临时 DB / 临时 HTML_DIR / CLI 子进程 wrapper
- [ ] `python -m pytest tests/` 退出码 0（哪怕只有 1 个 trivial test 验证 conftest 能 import）
- [ ] 不删旧 `scripts/test_db.py` 与 `scripts/run_tests.py`（本 ticket 仅新建，不动旧）
- [ ] `tests/__init__.py` 不强制存在（pytest 不需要）