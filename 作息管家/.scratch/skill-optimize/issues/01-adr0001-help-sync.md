---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 01
Blocked-by: []
---

# 01 — ADR-0001 落地 · help_render.py 同步作息管家.html

**What to build:** 用户在作息管家根目录打开 `作息管家.html` 永远看到当前所有场景(73 个 + 5 个模块分类),无需手动维护。`help_render.py` 跑一次,根目录作息管家.html 与最新一份 `schedule_html/help/作息管家_HELP_<TS>.html` 内容自动一致。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] help_render.py 新增同步函数,内部复制主输出到作息管家/作息管家.html
- [ ] render() 主流程在渲染完成后调用同步,返回的 data.file_path 包含两个路径(主 + 镜像)
- [ ] 跑 `python scripts/help_render.py` 后,作息管家.html 存在且与 schedule_html/help/作息管家_HELP_<TS>.html 内容完全一致
- [ ] 任何 scenarios.yaml 改动 → 跑 help_render.py → 作息管家.html 自动更新(配合 §05 钩子 #1)
- [ ] pytest 11 个测试全绿
- [ ] commit Tested-By:exempt(纯新增派生步骤 · 行为不变)