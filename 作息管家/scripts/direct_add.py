#!/usr/bin/env python3
"""
直接调用 schedule_db.add_record_full 写入记录
"""
import sys
import json
from datetime import datetime

# 添加 scripts 目录到 path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schedule_db import add_record_full

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "2026-05-30"
    json_file = sys.argv[2] if len(sys.argv) > 2 else "/tmp/records_0530_page1.json"

    with open(json_file, 'r', encoding='utf-8') as f:
        records = json.load(f)

    print(f"开始写入 {len(records)} 条记录到 {date_str}...")
    
    success = 0
    errors = []
    
    for i, rec in enumerate(records):
        try:
            # 计算 duration
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
                source_timestamps='AI分析生成',
                analysis_reasoning='按活动切换点切割，细粒度记录'
            )
            success += 1
            print(f"  ✓ [{i+1}/{len(records)}] {rec['time_start']}-{rec['time_end']} {rec['activity']}")
        except Exception as e:
            errors.append(f"[{i+1}] {rec.get('time_start','?')}-{rec.get('time_end','?')}: {e}")
            print(f"  ✗ [{i+1}/{len(records)}] {rec.get('time_start','?')}-{rec.get('time_end','?')} 错误: {e}")

    print(f"\n完成: 成功 {success}/{len(records)} 条")
    if errors:
        print(f"失败 {len(errors)} 条:")
        for e in errors:
            print(f"  - {e}")

if __name__ == '__main__':
    main()