#!/usr/bin/env python3
"""
作息管家 - Block 数量校验模块
提供同步粒度校验的函数

get_required_block_count: 获取该时间区间最少需要的 block 数量
validate_record_count: 验证 block 数量是否达标，不达标返回提示词
"""

import sys
from pathlib import Path
from datetime import datetime

# ============ 时间转换工具（从 schedule_db 复制）============
def _time_str_to_ts(time_str):
    """'2026-05-20 22:41:00' → 微秒时间戳（与数据库16位时间戳一致）"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000000)
    except:
        return 0

# ============ 数据库连接（延迟导入避免循环）============
def _get_dr_connection():
    from schedule_db import get_dr_connection
    return get_dr_connection()

def _get_connection():
    from schedule_db import get_connection
    return get_connection()


def get_required_block_count(start_ts, end_ts, messages_per_block=5):
    """
    返回该时间区间最少需要的 block 数量 = ceil(消息总数 / messages_per_block)
    - start_ts: 区间开始时间（格式：YYYY-MM-DD HH:MM:SS）
    - end_ts: 区间结束时间（格式：YYYY-MM-DD HH:MM:SS）
    - messages_per_block: 每个 block 最多承载的消息数（默认5）
    """
    from_ts = _time_str_to_ts(start_ts)
    to_ts = _time_str_to_ts(end_ts)
    conn = _get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM user_messages
        WHERE timestamp >= ? AND timestamp <= ?
    ''', (from_ts, to_ts))
    count = c.fetchone()[0]
    conn.close()
    import math
    return math.ceil(count / messages_per_block)


def validate_record_count(start_ts, end_ts, messages_per_block=5):
    """
    验证该时间区间的 block 数量是否达标
    - start_ts: 区间开始时间（格式：YYYY-MM-DD HH:MM:SS）
    - end_ts: 区间结束时间（格式：YYYY-MM-DD HH:MM:SS）
    - messages_per_block: 每个 block 最多承载的消息数（默认5，即5条消息/1个block）
    
    返回：
    - True: 验证通过
    - str: 验证失败的提示词（提示 AI 需要拆得更细）
    """
    from_ts = _time_str_to_ts(start_ts)
    to_ts = _time_str_to_ts(end_ts)
    
    # 获取该区间的消息总数
    conn_dr = _get_dr_connection()
    c_dr = conn_dr.cursor()
    c_dr.execute('''
        SELECT COUNT(*) FROM user_messages
        WHERE timestamp >= ? AND timestamp <= ?
    ''', (from_ts, to_ts))
    total_messages = c_dr.fetchone()[0]
    conn_dr.close()
    
    # 计算最少需要的 block 数
    import math
    required_min = math.ceil(total_messages / messages_per_block)
    
    from_date = start_ts.split(' ')[0]
    to_date = end_ts.split(' ')[0]
    from_time = start_ts.split(' ')[1][:5]  # 截取 HH:MM（去掉秒）
    to_time = end_ts.split(' ')[1][:5]      # 截取 HH:MM（去掉秒）
    
    conn = _get_connection()
    c = conn.cursor()
    
    if from_date == to_date:
        c.execute('''
            SELECT COUNT(*) FROM schedule_records
            WHERE date = ? AND time_start >= ? AND time_end <= ?
        ''', (from_date, from_time, to_time))
    else:
        c.execute('''
            SELECT COUNT(*) FROM schedule_records
            WHERE (date = ? AND time_start >= ?) OR (date = ? AND time_end <= ?)
        ''', (from_date, from_time, to_date, to_time))
    
    actual_count = c.fetchone()[0]
    conn.close()
    
    if actual_count >= required_min:
        return True
    else:
        # 返回明确的提示词（动态使用 messages_per_block 参数，不写死）
        return (
            f"Block 数量不足：当前 {messages_per_block} 条消息/1个block 规则，"
            f"区间共 {total_messages} 条消息，最少需要 {required_min} 个 block，"
            f"实际只有 {actual_count} 个。请将活动拆分得更细致，每{messages_per_block}条消息一个block。"
        )
