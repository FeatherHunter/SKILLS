#!/usr/bin/env python3
"""batch_scenarios.py — 批量导入作息记录（实施 T4 · 域模块自注册）

渐进式注册通道契约（实施 T1）：模块级 COMMANDS 注册表 → CLI 自动发现 dispatch。
不碰 schedule_cli.py 的 49 命令分发；本模块自带注册：

  COMMANDS = {"batch-add": batch_add_main}

命令：
  python scripts/schedule_cli.py batch-add <date> --json @records.json [--dry-run] [--stop-on-error]

校验复用 add 链路（不重复实现，逐条委托）：
  - 必填字段：与 cmd_add_record 同款 field_map 语义（9 字段缺一报错；date 缺省用
    命令行 <date>；source_timestamps / analysis_reasoning 缺省填空串）
  - 时间归一：schedule_db.normalize_time（24:00 → 23:59，对齐 add 链路）
  - duration 省略时按 (end-start) 分钟差计算，负值 +24*60（跨日）
  - category 白名单：add_record_full 内部 validators.validate_category（不在 CLI 层重复校验）
  - 写库：add_record_full(**kwargs) 与单条 add 完全同一入口

幂等性：**不提供**。作息记录无唯一键，重复执行会重复插入；批量导入场景为
一次性 AI 分析结果写入（与 ensure-plan-event 的幂等语义不同，此差异为既定设计）。

输出：stdout 单 JSON（对齐 CLI JSON 契约），逐条进度写 stderr。
"""
import sys
import json

from schedule_db import _normalize_date, normalize_time, add_record_full

USAGE = "batch-add <date> --json @records.json [--dry-run] [--stop-on-error]"

# 缺省为空的字段（空串即合法值，不算缺失）
EMPTY_OK = {"source_timestamps", "analysis_reasoning"}


def _emit(payload):
    """stdout 单 JSON（CLI JSON 契约，ensure_ascii=False + indent=2 对齐 cmd_add_record）"""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _validate_record(rec, date_str):
    """逐条校验（复用 cmd_add_record 的 field_map 语义）→ add_record_full kwargs。

    ValueError 携带该条的具体错误消息，由调用方收集进 data.errors。
    """
    fields = {
        "date": rec.get("date", date_str),
        "time_start": rec.get("time_start"),
        "time_end": rec.get("time_end"),
        "duration_minutes": rec.get("duration_minutes"),
        "activity": rec.get("activity"),
        "category": rec.get("category"),
        "source_contents": rec.get("source_contents"),
        "source_timestamps": rec.get("source_timestamps", ""),
        "analysis_reasoning": rec.get("analysis_reasoning", ""),
    }
    # 日期归一（命令行 <date> 已归一；单条自带 date 也走同一解析器）
    if not fields["date"]:
        raise ValueError("缺少必填字段: date")
    try:
        fields["date"] = _normalize_date(fields["date"])
    except ValueError as e:
        raise ValueError(str(e))
    # 时间归一（24:00 → 23:59，对齐 add 链路）
    for k in ("time_start", "time_end"):
        if fields[k] not in (None, ""):
            fields[k] = normalize_time(fields[k])
    # duration 省略时按 batch_add.py:28-35 算法计算（(end-start) 分钟差，负值 +24*60）
    if fields["duration_minutes"] in (None, ""):
        try:
            t1, t2 = fields["time_start"], fields["time_end"]
            h1, m1 = int(t1.split(":")[0]), int(t1.split(":")[1])
            h2, m2 = int(t2.split(":")[0]), int(t2.split(":")[1])
            duration = (h2 * 60 + m2) - (h1 * 60 + m1)
            if duration < 0:
                duration += 24 * 60
            fields["duration_minutes"] = duration
        except (AttributeError, ValueError, TypeError):
            fields["duration_minutes"] = None
    else:
        try:
            fields["duration_minutes"] = int(fields["duration_minutes"])
        except (TypeError, ValueError):
            raise ValueError(f"duration_minutes 必须是整数: {fields['duration_minutes']!r}")
    # 必填校验（缺一报错，列出缺失字段名；空串合法字段除外）
    missing = [k for k, v in fields.items()
               if v is None or (v == "" and k not in EMPTY_OK)]
    if missing:
        raise ValueError(f"缺少必填字段: {', '.join(missing)}")
    return fields


def batch_add_main(args):
    """batch-add <date> --json @records.json [--dry-run] [--stop-on-error]"""
    # === 1. 解析参数（对齐 cmd_add_record 的 --json @file | 内联 约定）===
    date_str = None
    json_payload = None
    dry_run = False
    stop_on_error = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            if i + 1 >= len(args):
                _emit({"status": "error", "message": "--json 后需跟文件名(@file)或 JSON 字符串"})
                return
            v = args[i + 1]
            try:
                if v.startswith("@"):
                    # utf-8-sig:兼容 Windows 工具链(记事本/PowerShell)带 BOM 的 UTF-8,
                    # 无 BOM 的 UTF-8 亦正常读取
                    with open(v[1:], encoding="utf-8-sig") as f:
                        json_payload = json.load(f)
                else:
                    json_payload = json.loads(v)
            except Exception as e:
                _emit({"status": "error", "message": f"JSON 解析失败: {e}"})
                return
            i += 2
            continue
        if a == "--dry-run":
            dry_run = True
        elif a == "--stop-on-error":
            stop_on_error = True
        elif a.startswith("--"):
            _emit({"status": "error", "message": f"未知参数: {a}\n用法: {USAGE}"})
            return
        elif date_str is None:
            date_str = a
        i += 1

    if date_str is None or json_payload is None:
        _emit({"status": "error", "message": f"缺必填参数: <date> 与 --json\n用法: {USAGE}"})
        return
    try:
        date_str = _normalize_date(date_str)
    except ValueError as e:
        _emit({"status": "error", "message": f"日期非法: {e}"})
        return
    if not isinstance(json_payload, list):
        _emit({"status": "error", "message": "records 必须是 JSON 数组（每条为对象）"})
        return
    if not json_payload:
        _emit({"status": "error",
               "message": "records 为空数组，无记录可写",
               "data": {"date": date_str, "total": 0, "success": 0, "failed": 0,
                        "ids": [], "errors": []}})
        return

    # === 2. 逐条校验 + 写库（单条失败不打断，收集进 data.errors）===
    ids = []
    errors = []
    for idx, rec in enumerate(json_payload):
        if not isinstance(rec, dict):
            errors.append({"index": idx, "message": "记录必须是对象"})
            if stop_on_error:
                break
            continue
        try:
            kwargs = _validate_record(rec, date_str)
        except ValueError as e:
            errors.append({"index": idx, "message": str(e)})
            if stop_on_error:
                break
            continue
        if dry_run:
            print(f"✓ [{idx + 1}] (DRY-RUN) {kwargs['time_start']}-{kwargs['time_end']} "
                  f"{kwargs['activity']}", file=sys.stderr)
            continue
        try:
            record_id = add_record_full(**kwargs)
            ids.append(record_id)
            print(f"✓ [{idx + 1}] {kwargs['time_start']}-{kwargs['time_end']} "
                  f"{kwargs['activity']}", file=sys.stderr)
        except ValueError as e:
            errors.append({"index": idx, "message": f"写入失败: {e}"})
            if stop_on_error:
                break
        except Exception as e:
            errors.append({"index": idx, "message": f"未知错误: {type(e).__name__}: {e}"})
            if stop_on_error:
                break

    # === 3. 汇总（status：全成 ok / 部分 partial / 全败或参数错 error）===
    total = len(json_payload)
    failed = len(errors)
    success = total - failed if dry_run else len(ids)
    if failed == 0:
        status = "ok"
    elif success > 0:
        status = "partial"
    else:
        status = "error"

    stopped = stop_on_error and failed > 0 and (success + failed) < total
    mode = "校验通过（DRY-RUN，未写库）" if dry_run else "批量写入完成"
    if status == "error":
        message = f"✗ {mode}: {failed}/{total} 条全部失败，见 data.errors"
    elif failed:
        message = f"✓ {mode}: 成功 {success}/{total} 条（失败 {failed} 条，见 data.errors）"
    else:
        message = f"✓ {mode}: 成功 {success}/{total} 条"
    if stopped:
        message += "（--stop-on-error 遇错即停，剩余未处理）"

    _emit({
        "status": status,
        "data": {
            "date": date_str,
            "total": total,
            "success": success,
            "failed": failed,
            "ids": ids,
            "errors": errors,
        },
        "message": message,
    })


# 渐进式注册通道（实施 T1 契约）：模块级 COMMANDS 注册表 → CLI 自动发现 dispatch
COMMANDS = {"batch-add": batch_add_main}
