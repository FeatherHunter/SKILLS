---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 02
Blocked-by: []
---

# Phase A-1 · Q5+Q6+Q7 — 路径对齐 + 复制 prompt + 内部分组

## 改动前必答 3 问(总纲 §05)

1. **影响文件**:
   - `scripts/schedule_cli.py`(~10 处 `_naming_path` 调用 + ~10 处 `render_*` 子命令)
   - `scripts/schedule_html_render.py`(`default_output_path` 5 处)
   - `scripts/help_render.py`(核对,已知中文)
   - `SKILL.md`(~20 处路径引用)
   - `作息管家.html`(顶部 stats,Q1+Q2 自动同步)
   - `tests/`(path 期望值 ~5 处)
2. **数据迁移**:无(只改文件名,DB 不变)。`$SKILLS_DB_PATH/schedule_html/` 下旧文件变孤儿,建议提供迁移脚本(可选)
3. **回滚方案**:`git revert`(单 commit 风险大,失败可独立 revert)

## 任务

按 ADR-0002 + ADR-0003 实施 3 个决策:

### Q5 · 路径对齐原则 12.A(ADR-0002)

全部 15 模板文件名统一 `<command_cn>_<YYYYMMDD>_<HHMMSS>.html`(中文 command 名):

| 域 | 旧文件名(英文) | 新文件名(中文) |
|---|---|---|
| record | `record_day_<TS>.html` | `查作息记录_<TS>.html` |
| record | `record_range_<TS>.html` | `查作息区间_<TS>.html` |
| record | `record_compare_<TS>.html` | `查作息对比_<TS>.html` |
| record | `record_category_<TS>.html` | `查作息类别_<TS>.html` |
| record | `record_anomaly_<TS>.html` | `查作息异常_<TS>.html` |
| record | `record_detail_<TS>.html` | `作息详情_<TS>.html` |
| record | `record_receipt_<TS>.html` | `记作息回执_<TS>.html` |
| record | `record_receipt_edit_<TS>.html` | `修正作息回执_<TS>.html` |
| plan | `plan_list_<TS>.html` | `查日程_<TS>.html` |
| plan | `plan_receipt_<TS>.html` | `改日程回执_<TS>.html` |
| plan | `plan_receipt_add_<TS>.html` | `补日程回执_<TS>.html` |
| plan | `plan_receipt_write_<TS>.html` | `写日程回执_<TS>.html` |
| plan | `plan_preview_<TS>.html` | `商量计划预览_<TS>.html` |
| plan | `plan_review_<TS>.html` | `复盘_<TS>.html` |
| help | `作息管家_HELP_<TS>.html` | (不变,已对齐) |

### Q6 · 单工铁律(ADR-0002)

全部 15 模板补"复制 prompt"按钮 + 4 部分结构(场景 / 数据 / 期望 / 来源),超原则 10 字面"过程型 HTML"。

### Q7 · schedule_cli.py 内部分组(ADR-0003)

`_naming_path` 函数内部按 record / plan / receipt / help 4 域加注释分组(为将来拆分打基础,不拆文件)。

## 实施步骤

1. **改 `_naming_path`** — 接受中文 command 参数,内部按域分组
2. **改 `default_output_path`** 5 处 — 调用 `_naming_path` 时传中文 command
3. **改 `cmd_render_*`** 子命令 — 传中文 command 到 `_naming_path`
4. **改 SKILL.md** — 顶部 stats 字段改为从 scenarios.yaml 派生(或 Phase A-3 自动同步)
5. **改 `tests/`** — path 期望值改为中文文件名
6. **跑 pytest baseline** — 11 个测试文件必须全绿
7. **FAT 黑盒测试**(Fresh Agent)— 跨多 CLI 子命令验证路径生成正确

## Tested-By

```
Tested-By: pending-FAT
  - 唤醒词: 查作息 / 查日程 / 修正作息 / 商量计划 / 复盘 / 补计划
  - 人类 prompt: ≥ 3 个口语化/slash/略错 prompt,各唤醒词至少 1 个
  - 结果: pass / pass-after-N-loops
  - 验证项: 
    1. 中文文件名生成正确(查作息记录_<TS>.html 等)
    2. SKILL.md 路径引用与实际生成一致
    3. 全部 15 模板都有"复制 prompt"按钮
    4. pytest baseline 全绿
```

## 预期 commit

```
[作息管家] Phase A-1 · Q5+Q6+Q7 严格执行总纲 §04 原则 12.A + 原则 10

文件清单:
~ scripts/schedule_cli.py                  (~20 处 _naming_path / render_* 调用)
~ scripts/schedule_html_render.py         (default_output_path 5 处)
~ SKILL.md                                 (~20 处路径引用)
~ tests/                                   (path 期望值 ~5 处)

行为变化: HTML 文件名中文化(15 模板) + 全部补复制 prompt + schedule_cli.py 内部分组
向后兼容: ❌(文件名变化,旧路径变孤儿,需提供迁移脚本)

Tested-By: pending-FAT(见上)
```