#!/usr/bin/env python3
"""训记 API 适配器：训记训练记录 ↔ exercise_log 表

职责：
  1. 训记 GET 响应 → exercise_log 行列表
  2. 去重：xunji_localid + set_index 做幂等键
  3. load_kg 单位转换（lbs → kg）
  4. 热量推算（使用 exercise.py 的公式）
"""

import json
from exercise import estimate_calories_from_training, convert_load_kg, _infer_category


def xunji_response_to_rows(resp_json, body_weight_kg=None):
    """训记 API 返回的 trains[] → exercise_log 插入行列表

    Args:
        resp_json: 训记 GET API 返回的完整 JSON
        body_weight_kg: 体重（可选，用于热量估算）

    Returns:
        list[dict]: 每行一个完成的 set
    """
    rows = []
    trains = resp_json.get('res', {}).get('trains', [])

    for train in trains:
        localid = str(train.get('localid', ''))
        title = train.get('title', '')
        datestr = train.get('datestr', '')

        for move in train.get('movements', []):
            name = move.get('name', '')
            difficulty = train.get('difficulty')  # 训记训练级 difficulty

            for s in move.get('sets', []):
                if not s.get('done'):
                    continue  # 只同步完成的组

                load = convert_load_kg(s.get('weight', '0'), s.get('unit', 'kg'))
                # reps 可能是 "12" 或 "12-16"(范围值),范围值取最大值(惯例)
                reps_raw = s.get('reps', 0)
                if isinstance(reps_raw, str) and '-' in reps_raw:
                    try:
                        reps = max(int(x) for x in reps_raw.split('-') if x.strip())
                    except (ValueError, TypeError):
                        reps = 0
                else:
                    try:
                        reps = int(reps_raw)
                    except (ValueError, TypeError):
                        reps = 0
                volume = load * reps

                rows.append({
                    'date': datestr,
                    'exercise_type': name,
                    'reps': reps,
                    'set_index': s.get('index'),
                    'load_kg': load,
                    'calories_burned': estimate_calories_from_training(volume, body_weight_kg),
                    'category': _infer_category(name),
                    'difficulty': difficulty,
                    'xunji_localid': localid,
                    'xunji_title': title,
                })

    return rows


def upsert_exercise_log(db_conn, rows):
    """将训记数据写入 exercise_log，用 xunji_localid + set_index 去重。

    策略：
      - 查 (xunji_localid, set_index) 是否存在
      - 存在 → UPDATE（覆盖 weight/reps/calories，但保留手动填的 note）
      - 不存在 → INSERT

    Args:
        db_conn: sqlite3.Connection(调用方负责 commit/rollback)
        rows: xunji_response_to_rows() 的输出

    Returns:
        {"inserted": int, "updated": int, "total": int, "errors": list[str]}

    Raises:
        任何 SQL 错误向上抛,**已写入的 row 不 commit**(调用方需 rollback 或自行处理)
    """
    c = db_conn.cursor()
    inserted = 0
    updated = 0
    errors = []

    try:
        for row in rows:
            try:
                c.execute('''
                    SELECT id FROM exercise_log
                    WHERE xunji_localid = ? AND exercise_type = ? AND set_index = ?
                ''', (row['xunji_localid'], row['exercise_type'], row['set_index']))
                existing = c.fetchone()

                if existing:
                    c.execute('''
                        UPDATE exercise_log
                        SET exercise_type=?, reps=?, load_kg=?, calories_burned=?,
                            category=?, difficulty=?, xunji_title=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        row['exercise_type'], row['reps'], row['load_kg'],
                        row['calories_burned'], row['category'], row['difficulty'],
                        row['xunji_title'], existing[0],
                    ))
                    updated += 1
                else:
                    c.execute('''
                        INSERT INTO exercise_log
                            (date, exercise_type, reps, set_index, load_kg, calories_burned,
                             category, difficulty, xunji_localid, xunji_title)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['date'], row['exercise_type'], row['reps'], row['set_index'],
                        row['load_kg'], row['calories_burned'], row['category'],
                        row['difficulty'], row['xunji_localid'], row['xunji_title'],
                    ))
                    inserted += 1
            except Exception as e:
                # 单行失败不中断整体,记到 errors(让调用方决定如何处理)
                errors.append(f"localid={row.get('xunji_localid')} set_index={row.get('set_index')}: {e}")
                # 继续下一行(不抛)
    except Exception:
        # 外层捕获 cursor 级别异常(数据库锁定等)
        raise

    return {
        "inserted": inserted,
        "updated": updated,
        "total": inserted + updated,
        "errors": errors,
    }
