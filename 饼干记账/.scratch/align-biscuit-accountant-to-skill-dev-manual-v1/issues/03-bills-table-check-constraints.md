# 03 — 给 `bills` 表加 SQLite CHECK 约束（defense-in-depth）

**What to build:** 直接 SQL 写入（绕过 CLI 的 argparse / validators 校验）也无法保存「金额 0 / 非法币种 / 账本为空」的脏数据 —— SQLite 自己拒绝，保证数据层是最后兜底。

**Blocked by:** 02 — validators.py（确保新 CHECK 与 validators 的语义一致）

**Status:** ready-for-agent

- [ ] 迁移脚本存在，支持 `--dry-run` + `--rollback`
- [ ] `bills` 表含 `CHECK (amount != 0)` / `CHECK (currency IN ('CNY', '人民币'))` / `CHECK (ledger IS NOT NULL AND ledger != '')`
- [ ] `--rollback` 后 CHECK 约束消失
- [ ] `tests/test_render.py` 加 fixture：直接 `INSERT INTO bills VALUES (..., 0, ...)` → 抛 IntegrityError
- [ ] `backups/` 目录有迁移前 CSV 备份