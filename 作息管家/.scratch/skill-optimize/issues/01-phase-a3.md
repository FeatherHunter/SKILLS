---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 01
Blocked-by: []
---

# Phase A-3 · ADR-0001 落地 — help_render.py 同步作息管家.html

## 改动前必答 3 问(总纲 §05)

1. **影响文件**:`scripts/help_render.py`(~20 行,加 `sync_to_stable_mirror()` 函数 + `render()` 调用)
2. **数据迁移**:无(只加派生步骤,数据流不变)
3. **回滚方案**:`git revert`(单 commit,无破坏性)

## 任务

按 ADR-0001 把作息管家.html 改造为 HELP HTML 脚本直接复制的产物 — 每次跑 `help_render.py` 自动同步根目录作息管家.html。

## 实施细节

1. **新增函数** `sync_to_stable_mirror(out_path: Path) -> Path`
   - 复制 `out_path` 内容到 `作息管家/作息管家.html`(根目录镜像)
   - 确保父目录存在
   - 返回镜像路径
2. **修改** `render(out_path: Path)` 主流程
   - 渲染完成后调用 `sync_to_stable_mirror(out_path)`
   - 返回的 `data.file_path` 包含两个路径(主 + 镜像)
3. **测试**:跑 `python scripts/help_render.py --out /tmp/test.html`,验证:
   - 主输出:`/tmp/test.html` 存在
   - 镜像:`作息管家.html` 存在且内容一致

## 完成后更新

- `作息管家.html` 顶部 stats 自动从 scenarios.yaml 派生(73 场景 + 28 唤醒词数字准确)
- 任何 SKILL.md / scenarios.yaml 改动 → 跑 `help_render.py` → 作息管家.html 自动同步
- 配合总纲 §05 钩子 #1 "HTML 同步硬规则" 完全自洽

## Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 纯新增派生步骤 · 行为不变(reader 看到的 contract 未改)
  - 自检: 帮助中心 HTML 渲染流程不变,仅增加同步派生步骤
  - 验证: 跑 help_render.py 后比对作息管家.html 与 schedule_html/help/作息管家_HELP_<TS>.html 内容一致
```

## 预期 commit

```
[作息管家] Phase A-3 · ADR-0001 落地 · help_render.py 同步作息管家.html

文件清单:
~ scripts/help_render.py       (~20 行,加 sync_to_stable_mirror 函数)

行为变化: 帮助中心 HTML 渲染后自动同步根目录作息管家.html
向后兼容: ✅(派生步骤,不影响原有 render() 流程)

Tested-By: exempt(见上)
```