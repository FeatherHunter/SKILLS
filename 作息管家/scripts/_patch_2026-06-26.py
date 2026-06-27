#!/usr/bin/env python3
"""补 2026-06-26 18:01~18:09 的 gap 记录"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full

# 补 18:01~18:09 的 gap 记录：用户在家准备出门（餐饮讨论收尾后准备出门看电影）
add_record_full(
    date='2026-06-26',
    time_start='18:01',
    time_end='18:09',
    duration_minutes=8,
    activity='热量讨论收尾+准备出门看电影',
    category='通勤',
    source_contents='[18:01] 24 25 26（前5后5推断：17:50~18:01是三天热量平均统计，18:01后无消息直到18:09出门，结合上下文判断为热量讨论收尾+准备出门）',
    source_timestamps='18:01:00',
    analysis_reasoning='用户在17:50~18:01讨论三天热量平均统计后，18:01给出日期序列"24 25 26"完成统计。18:01~18:09之间无消息，18:09切换到"现在出门去咯 去看电影"。结合上下文（即将出门看电影、刚吃了四个包子）判断这段时间是热量讨论收尾+准备出门阶段，归类为通勤（准备出门）。'
)
print('✓ 已补记录: 18:01~18:09 [通勤] 准备出门')
