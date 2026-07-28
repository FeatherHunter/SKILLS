# ADR-0002: 严格执行总纲 §04 原则 12.A(中文 command 名)+ 原则 10(全部 15 模板补复制 prompt)

作息管家所有 HTML 模板统一遵循总纲 §04 原则 12.A — `<command_cn>_<YYYYMMDD>_<HHMMSS>.html` 中文 command 名 + 时间戳格式;同时超字面执行总纲 §04 原则 10 — 全部 15 模板(不只是过程型)补"复制 prompt"按钮。

## 理由

1. §04 原则 12.A 是硬规则,作息管家 record/plan 域至今未对齐(只有 help_center 对齐了)
2. §04 原则 10 字面只要求"过程型 HTML",但 record 域 6 模板已有 AI 钩子卡,扩到全部 15 模板可保持一致性
3. 用户明确指令"严格按总纲"+"全部补"(Q5 + Q6)

## 范围

### Q5 · 路径对齐(总纲 §04 原则 12.A)

15 个 HTML 模板文件名从中英混用 → 全部 `<command_cn>_<YYYYMMDD>_<HHMMSS>.html`:

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
| help | `作息管家_HELP_<TS>.html` | (不变,已对齐 §04 原则 12.B) |

### Q6 · 单工铁律(总纲 §04 原则 10)

15 模板全部补"复制 prompt"按钮 + 4 部分结构(场景 / 数据 / 期望 / 来源),超原则 10 字面"过程型 HTML"。

## 实施

### 改动前必答 3 问(总纲 §05)

1. **影响文件**:
   - `scripts/schedule_cli.py`(~10 处 `_naming_path` 调用 + ~10 处 `render_*` 子命令)
   - `scripts/schedule_html_render.py`(`default_output_path` 5 处)
   - `scripts/help_render.py`(`help_naming_path` 已经中文,仅核对)
   - `SKILL.md`(~20 处路径引用)
   - `作息管家.html` 顶部 stats(Q1+Q2 自动同步,无需手改)
   - `tests/`(path 期望值 ~5 处)
2. **数据迁移**:无(只改文件名,DB 不变)。`$SKILLS_DB_PATH/schedule_html/` 下旧文件变孤儿,建议提供迁移脚本(可选)
3. **回滚方案**:`git revert`(单 commit 风险大,若失败可独立 revert)

### 提交策略

- 单 commit:`[作息管家] Q5+Q6 严格执行总纲 §04 原则 12.A + 原则 10`
- 含 ADR-0002 + ADR-0003 链接
- 含 Tested-By:`pending-FAT`(Q5+Q6 改动跨多个 CLI 子命令,需 Fresh Agent 黑盒测试)

## 考虑过的替代方案

- Q5 选 B(分 4 个 batch)— 用户答 A 拒绝
- Q5 选 C(仅改 command 名,不动时间戳)— 用户答 A 拒绝
- Q5 选 D(暂不做)— 用户答 A 拒绝
- Q6 选 B(只补过程型)— 用户答 A 拒绝(超字面)

## 后果

1. 15 模板全部统一中文 command 名(与卡路里 / 饼干记账对齐)
2. 全部 15 模板有复制 prompt,流程型 HTML 单工铁律 100% 覆盖
3. 旧文件名变孤儿,需用户手动清理或跑迁移脚本
4. 改动量大,需 Fresh Agent 测试验证

## Status

`accepted` · 2026-07-28 · Grilling Session Q5/Q6 共识
