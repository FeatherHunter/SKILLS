#!/usr/bin/env python3
"""
为 2026-06-15 生成每日作息报告
1. 读取 schedule_records
2. 按分类汇总 total_minutes
3. 调用 add_summary() 写入 daily_summary
4. 生成 HTML 报告
"""

import sys
import json
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    get_records_by_date, add_summary, get_daily_summary, get_plan
)

# ============ 配置 ============
TARGET_DATE = "2026-06-15"
SKILL_DIR = Path(__file__).parent.parent
REPORT_PATH = SKILL_DIR / "reports" / f"{TARGET_DATE}.html"

# ============ 1. 读取记录 ============
records = get_records_by_date(TARGET_DATE)
print(f"读取到 {len(records)} 条记录")
print(f"首条: {records[0]['time_start']}")
print(f"末条: {records[-1]['time_end']}")

# ============ 2. 智能分类映射 ============
def refine_category(rec):
    """根据 activity 内容细化分类"""
    orig_cat = rec['category']
    activity = rec['activity']
    
    # 休息分类细化：长睡/午睡→睡眠；短休→休闲
    if orig_cat == '休息':
        # 490min 那种夜间主睡眠 或 长时间躺床 → 睡眠
        if rec['duration_minutes'] >= 60:
            return '睡眠'
        # activity 中含"睡眠"/"睡觉"/"午睡" → 睡眠
        if any(kw in activity for kw in ['睡眠', '睡觉', '午睡', '躺床休息']):
            return '睡眠'
        # 1~2 分钟的临时停顿 → 休闲
        if rec['duration_minutes'] <= 2:
            return '休闲'
        # 其他（5~20min 短休）→ 休闲
        return '休闲'
    
    return orig_cat

# ============ 3. 按细化分类汇总 ============
cat_minutes = defaultdict(int)
cat_records = defaultdict(list)
for r in records:
    final_cat = refine_category(r)
    cat_minutes[final_cat] += r['duration_minutes']
    cat_records[final_cat].append(r)

print()
print("细化后分类汇总:")
for cat, mins in sorted(cat_minutes.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {mins}min = {mins//60}h{mins%60}m")
print(f"  合计: {sum(cat_minutes.values())}min")

# ============ 4. 调用 add_summary 写入 daily_summary ============
print()
print("写入 daily_summary...")
for cat, mins in cat_minutes.items():
    result = add_summary(TARGET_DATE, cat, mins)
    print(f"  ✓ {cat}: {mins}min")

# 验证
print()
print("验证写入结果:")
saved = get_daily_summary(TARGET_DATE)
for item in saved:
    print(f"  {item['category']}: {item['total_minutes']}min")

# ============ 5. 计算时间轴（每小时主分类）============
hours = [None] * 24  # 每小时主分类
for r in records:
    final_cat = refine_category(r)
    try:
        h_start = int(r['time_start'].split(':')[0])
        h_end = int(r['time_end'].split(':')[0]) if r['time_end'] != '23:59' else 23
        # 简化：取每小时首个有效记录
        for h in range(h_start, h_end + 1):
            if h < 24 and hours[h] is None:
                hours[h] = final_cat
    except:
        pass

# 填充空白小时
for i, h in enumerate(hours):
    if h is None:
        hours[i] = '休息'  # 默认

# ============ 6. 准备数据供 HTML 生成 ============
plan = get_plan(TARGET_DATE)

# 找最长睡眠段
sleep_records = [r for r in records if refine_category(r) == '睡眠']
sleep_records.sort(key=lambda x: -x['duration_minutes'])
main_sleep = sleep_records[0] if sleep_records else None

# 工作相关记录
work_records = [r for r in records if refine_category(r) == '工作']

# 通勤相关
commute_records = [r for r in records if refine_category(r) == '通勤']

# 餐饮相关
meal_records = [r for r in records if refine_category(r) == '餐饮']

# 输出 JSON 数据供 HTML 生成
data = {
    'date': TARGET_DATE,
    'total_records': len(records),
    'total_minutes': sum(cat_minutes.values()),
    'total_hours': sum(cat_minutes.values()) / 60,
    'cat_minutes': dict(cat_minutes),
    'hours': hours,
    'main_sleep': main_sleep,
    'sleep_records': sleep_records,
    'work_records': work_records,
    'commute_records': commute_records,
    'meal_records': meal_records,
    'plan': plan,
    'records': [
        {
            'time_start': r['time_start'],
            'time_end': r['time_end'],
            'duration_minutes': r['duration_minutes'],
            'category': refine_category(r),
            'activity': r['activity']
        }
        for r in records
    ]
}

with open('/tmp/report_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print()
print(f"数据已保存到 /tmp/report_data.json")
