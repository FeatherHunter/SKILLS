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
                reps = int(s.get('reps', 0))
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
        db_conn: sqlite3.Connection（调用方负责 commit）
        rows: xunji_response_to_rows() 的输出
    """
    c = db_conn.cursor()

    for row in rows:
        c.execute('''
            SELECT id FROM exercise_log
            WHERE xunji_localid = ? AND set_index = ?
        ''', (row['xunji_localid'], row['set_index']))
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
