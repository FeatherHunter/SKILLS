---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 02
Blocked-by: []
---

# 02 — Q5 Expand · `_naming_path` 接受中文 command 名(保留英文 fallback)

**What to build:** HTML 文件路径生成函数接受中文 command 名(查作息记录 / 查日程 / 复盘 等)输出 `<command_cn>_<YYYYMMDD>_<HHMMSS>.html`,同时保留英文 command 名(record_day / plan_list 等)fallback,确保现有调用方不破。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `_naming_path` 函数新增中文 command 名映射表(如 `查作息记录` ↔ `record_day`)
- [ ] 调用方不传 command 时,默认从已有 cmd_render_record_day 等命令名派生(保持兼容)
- [ ] 显式传中文 command 名时,生成 `<中文>_<TS>.html`
- [ ] 显式传英文 command 名时仍工作(不破现有调用方)
- [ ] pytest 全绿 + 新增 5 用例覆盖中英文
- [ ] commit Tested-By:fresh-agent-v1(中英文参数各 3 个 prompt 验证)