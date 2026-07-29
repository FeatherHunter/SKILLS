# ADR-0003: schedule_cli.py 暂不拆,等 Q5 路径对齐实施时内部分组

`schedule_cli.py`(116KB / 3053 行)暂不拆分为 `record_cli.py` / `plan_cli.py` / `receipt_cli.py`。Q5 路径对齐实施时,在 `schedule_html_render.py` 的路径解析层(`CN_COMMAND_MAP` + `default_output_path` + `record_output_path`)按域分组(为将来拆分打基础),但不立即拆文件。

> 注:`_naming_path` 函数住在 `schedule_html_render.py`(不是 `schedule_cli.py`),因为路径解析属于渲染层而非 CLI 入口层。`schedule_cli.py` 只委托调用 `_naming_path`,本身零路径逻辑。

## 理由

1. Q5 会改 `schedule_html_render.py` 大量 `_naming_path` 调用点(经 `default_output_path` / `record_output_path`),那时候按域分组最自然
2. 用户明确选 Q7 B
3. 单独 commit 拆模块风险大,与 Q5 合并做更经济(避免重复触碰同一文件)
4. §02 5 层 §② 操作层要求"领域模块切得合理",但 §06 附录 B 也允许"B 优先级 · 按需"

## 范围

### Q7 不做的事

- 不新建 `record_cli.py` / `plan_cli.py` / `receipt_cli.py`
- 不移动 `cmd_render_record_*` / `cmd_render_plan_*` 函数到新文件
- 不修改 import 结构

### Q5 实施时的内部分组

在 `schedule_html_render.py` 的 `CN_COMMAND_MAP` 字典 + `default_output_path` / `record_output_path` 函数内,按 record / plan / receipt / help 4 个域加注释分组(2026-07-29 落地完成):

```python
CN_COMMAND_MAP = {
    # === record 域(6) === 报告型:day/range/compare/category/anomaly/detail ===
    "record_day":          "查作息记录",
    ...
    # === plan 域(3) === 过程型:list/preview/review ===
    "plan_list":           "查日程",
    ...
    # === receipt 域(5) === 回执型:record-receipt / record-receipt-edit / plan-receipt×3 ===
    "record_receipt":      "记作息回执",
    ...
}

def default_output_path(meta):
    """ADR-0003 Q7 · 4 域分组(为将来拆模块打基础):
      === record 域 === → 委托 record_output_path()
      === plan 域(3 mode)===> plan/list | plan/query
      === receipt 域 === → 由 record_output_path 处理
      === help 域 === → 由 help_render.py 独立处理
    """
    ...
    # === plan 域(3 mode · ADR-0002 Q5 中文 command 名 · ADR-0003 Q7 分组)===
    if mode == "list-events": ...
    ...
    # === receipt 域(plan-receipt 3 款 · 回执型,与 plan 域共享子目录)===
    if mode == "plan-receipt": ...
```

`_naming_path` 函数本身只接受已解析的中文 command 名(`查作息记录` 等),不做域分发 — 域分发在调用方(`default_output_path` / `record_output_path`)完成。

## 触发重新评估的条件

满足任一即重新评估是否拆分:

1. `schedule_cli.py` 突破 150KB / 4000 行
2. Q5 实施过程中发现 `CN_COMMAND_MAP` + `default_output_path` 内部逻辑已 100% 按域分组清晰,提取成本低
3. 用户明确要求拆分

## 考虑过的替代方案

- Q7 选 A(拆 3 个模块 · record/plan/receipt)— 用户答 B 拒绝
- Q7 选 C(只在内部重构)— 与 B 区别是 Q5 是否顺便分组,选 B 更主动
- Q7 选 D(与 Q5 同步做)— 单 commit 太大,FAT 难定位问题,拒绝

## 后果

1. 116KB 仍然大,但代码已有"内部按域"注释,未来拆分成本低
2. Q5 + Q7 合并在一个 commit,减少 commit 数量
3. `CN_COMMAND_MAP` / `default_output_path` / `record_output_path` 内部清晰 4 域分组,后续维护容易

## Status

`accepted` · 2026-07-28 · Grilling Session Q7 共识 · 2026-07-29 落地完成(commit f092476)
