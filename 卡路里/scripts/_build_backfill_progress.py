#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把 xunji_bridge backfill 输出转成 process_progress.html 所需的 JSON。
"""
import json
import sys
import datetime
from pathlib import Path


def build_progress(backfill_path: str, out_path: str):
    bf = json.loads(Path(backfill_path).read_text(encoding="utf-8-sig"))
    end_date = bf["end_date"]
    days = bf["days"]
    results = bf["results"]
    total_inserted = bf["total_inserted"]
    total_updated = bf["total_updated"]

    # 算总 trains
    total_trains = sum(r.get("trains_count", 0) for r in results)
    skip_count = sum(1 for r in results if r.get("skipped_empty"))
    fail_count = sum(1 for r in results if not r.get("fetch_ok"))

    started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 每日明细
    lines = []
    for r in results:
        d = r["date"]
        tc = r.get("trains_count", 0)
        ins = r.get("inserted", 0)
        upd = r.get("updated", 0)
        if r.get("fetch_ok") and tc > 0:
            lines.append(f"{d}: 拉 {tc} 条训练,新增 {ins},更新 {upd}")
        elif r.get("skipped_empty"):
            lines.append(f"{d}: 跳过(无训练)")
        else:
            err = (r.get("errors") or ["unknown"])[0]
            lines.append(f"{d}: 失败 — {err}")

    detail = "\n".join(lines)

    progress = {
        "summary": {
            "process_name": f"回写训记 {end_date} (近 {days} 天)",
            "process_type": "回写训记",
            "total_steps": 1,
            "completed_steps": 1 if fail_count == 0 else 0,
            "failed_steps": fail_count,
            "started_at": started_at,
            "finished_at": started_at,
        },
        "steps": [
            {
                "step": 1,
                "name": "回写训记",
                "description": f"拉取训记 {days} 天数据,回写到 exercise_log(幂等键:xunji_localid + set_index)",
                "status": "done" if fail_count == 0 else "failed",
                "started_at": started_at,
                "finished_at": started_at,
                "result": (
                    f"✅ 拉取 {total_trains} 条训练记录,共新增 {total_inserted} 条 / "
                    f"更新 {total_updated} 条 / 跳过 {skip_count} 天(无训练)"
                ),
                "detail": detail,
            }
        ],
    }

    Path(out_path).write_text(
        json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✅ 已生成 process_progress JSON: {out_path}")
    return out_path


if __name__ == "__main__":
    bf = sys.argv[1]
    out = sys.argv[2]
    build_progress(bf, out)
