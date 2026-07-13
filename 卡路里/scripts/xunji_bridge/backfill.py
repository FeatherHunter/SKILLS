#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记训练记录 → 卡路里 exercise_log 回写。

收编自:C:\\Users\\辰辰洋洋\\.mavis\\agents\\mavis\\workspace\\xunji_backfill.py

幂等键:xunji_localid + set_index(同组不会重复写)
推算热量:用 exercise.estimate_calories_from_training(volume, body_weight_kg)
单位转换:用 exercise.convert_load_kg(weight, unit)  (kg/lbs)
部位推断:用 exercise._infer_category(name)

公开 API:
    backfill_range(end_datestr=None, days=1, full_data=True) -> dict
        拉 [end_datestr-days+1, end_datestr] 区间(单日 = days=1)
        统一 API:单日和范围用同一个函数,输出格式永远一致
        返回:{end_date, days, results[], total_inserted, total_updated}

    _backfill_one(datestr, full_data=True) -> dict
        内部 helper,回写单日。外部应通过 backfill_range 调用。
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# 路径 hack(集中在这里,push.py 也用同一份)
_BRIDGE_DIR = Path(__file__).parent
_SCRIPTS_DIR = _BRIDGE_DIR.parent
_ADAPTERS_DIR = _SCRIPTS_DIR / "adapters"
for p in (str(_SCRIPTS_DIR), str(_ADAPTERS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from .fetch import fetch_trains  # noqa: E402
from xunji_adapter import xunji_response_to_rows, upsert_exercise_log  # noqa: E402
from db import find_db_path, DB_FILENAME, get_db  # noqa: E402

# DB 路径(其他模块统一模式):find_db_path 走 SKILLS_DB_PATH → fallback D:/.db
_SKILL_DIR = _SCRIPTS_DIR.parent
DB_PATH = find_db_path(_SKILL_DIR, DB_FILENAME)


def _get_db():
    """本地 calorie_data.db 连接(标准模式,跟其他 14 个模块一致)。"""
    return get_db(DB_PATH)


def _get_latest_body_weight_kg() -> Optional[float]:
    """从 weight_log 取最新一条体重的 kg 值(没有则 None)。

    用于更准的热量推算(METs 公式需要体重);backfill 不阻塞,失败返 None。
    """
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute('''
            SELECT weight FROM weight_log
            ORDER BY date DESC, id DESC LIMIT 1
        ''')
        row = c.fetchone()
        conn.close()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass
    return None


def _backfill_one(datestr: str, full_data: bool = True) -> dict:
    """回写某天的训记数据到 exercise_log。

    Args:
        datestr:    YYYY-MM-DD
        full_data:  是否用 include_full_data=True(回写需要拿到 done 标记)

    Returns:
        {
            "date": str,
            "fetch_ok": bool,
            "trains_count": int,
            "inserted": int,
            "updated": int,
            "skipped_empty": bool,
            "body_weight_kg": Optional[float],  # 用于热量推算的体重
            "errors": list[str],                # 行级 SQL 错误(如果有)
            "err": Optional[str],               # fetch 错误信息
        }
    """
    # datestr 为空时默认今天
    if not datestr:
        datestr = date.today().isoformat()
    resp = fetch_trains(datestr, full_data=full_data)

    if resp.get("err"):
        # 新错误格式(来自 errors.py):err dict 已经结构化,直接透传 + 加 err 顶层字段
        return {
            "date": datestr,
            "fetch_ok": False,
            "trains_count": 0,
            "inserted": 0,
            "updated": 0,
            "skipped_empty": True,
            "body_weight_kg": None,
            "errors": [],
            **resp,  # 透传 err_type / message / code / raw_body / attempts
        }

    trains = (resp.get("res", {}) or {}).get("trains", []) or []
    body_weight_kg = _get_latest_body_weight_kg()
    rows = xunji_response_to_rows(
        {"res": resp.get("res", {})},
        body_weight_kg=body_weight_kg,
    )

    if not rows:
        return {
            "date": datestr,
            "fetch_ok": True,
            "trains_count": len(trains),
            "inserted": 0,
            "updated": 0,
            "skipped_empty": True,
            "body_weight_kg": body_weight_kg,
            "errors": [],
            "err": None,
        }

    # 写库 + 显式事务(失败回滚)
    conn = _get_db()
    try:
        result = upsert_exercise_log(conn, rows)
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {
            "date": datestr,
            "fetch_ok": True,
            "trains_count": len(trains),
            "inserted": 0,
            "updated": 0,
            "skipped_empty": False,
            "body_weight_kg": body_weight_kg,
            "errors": [str(e)],
            "err": f"DB 写入失败(已回滚):{e}",
        }
    finally:
        conn.close()

    return {
        "date": datestr,
        "fetch_ok": True,
        "trains_count": len(trains),
        "inserted": result["inserted"],
        "updated": result["updated"],
        "skipped_empty": False,
        "body_weight_kg": body_weight_kg,
        "errors": result["errors"],
        "err": None,
    }


def backfill_range(end_datestr: Optional[str] = None, days: int = 1, full_data: bool = True) -> dict:
    """回写 [end_datestr - days + 1, end_datestr] 区间(默认今天+昨天)。

    Args:
        end_datestr: 区间结束日(默认今天)
        days:        区间天数(默认 2)
        full_data:   是否用 include_full_data=True

    Returns:
        {
            "end_date": str,
            "days": int,
            "results": [_backfill_one() 输出列表],
            "total_inserted": int,
            "total_updated": int,
        }
    """
    if end_datestr:
        end = date.fromisoformat(end_datestr)
    else:
        end = date.today()

    results = []
    total_ins = 0
    total_upd = 0
    for i in range(days):
        d = (end - timedelta(days=i)).isoformat()
        r = _backfill_one(d, full_data=full_data)
        results.append(r)
        total_ins += r.get("inserted", 0)
        total_upd += r.get("updated", 0)

    return {
        "end_date": end.isoformat(),
        "days": days,
        "results": results,
        "total_inserted": total_ins,
        "total_updated": total_upd,
    }
