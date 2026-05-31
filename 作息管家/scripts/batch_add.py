#!/usr/bin/env python3
"""
批量写入作息记录的脚本
接受 JSON 格式的记录列表，逐条调用 add_record_full
"""
import sys
import json

sys.path.insert(0, str(__file__).rsplit('/', 1)[0] if '/' in __file__ else '.')
from schedule_db import add_record_full

def main():
    if len(sys.argv) < 3:
        print("用法: python3 batch_add.py <日期> <records.json>")
        sys.exit(1)

    date_str = sys.argv[1]
    json_file = sys.argv[2]

    with open(json_file, 'r', encoding='utf-8') as f:
        records = json.load(f)

    success_count = 0
    error_count = 0

    for i, rec in enumerate(records):
        try:
            # 计算 duration_minutes
            t1 = rec['time_start']
            t2 = rec['time_end']
            h1, m1 = int(t1.split(':')[0]), int(t1.split(':')[1])
            h2, m2 = int(t2.split(':')[0]), int(t2.split(':')[1])
            duration = (h2 * 60 + m2) - (h1 * 60 + m1)
            if duration < 0:
                duration += 24 * 60

            add_record_full(
                date=date_str,
                time_start=rec['time_start'],
                time_end=rec['time_end'],
                duration_minutes=duration,
                activity=rec['activity'],
                category=rec['category'],
                source_contents=rec['source_contents'],
                source_timestamps=rec.get('source_timestamps', ''),
                analysis_reasoning=rec.get('analysis_reasoning', '')
            )
            success_count += 1
            print(f"✓ [{i+1}] {rec['time_start']}-{rec['time_end']} {rec['activity']}")
        except Exception as e:
            error_count += 1
            print(f"✗ [{i+1}] {rec.get('time_start','?')}-{rec.get('time_end','?')} 错误: {e}")

    print(f"\n完成: 成功 {success_count} 条, 失败 {error_count} 条")

if __name__ == '__main__':
    main()