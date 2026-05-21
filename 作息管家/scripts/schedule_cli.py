#!/usr/bin/env python3
"""
作息管家 - 主CLI脚本
功能：分析语录数据库 → 生成作息记录 → 提供查询接口

三层架构：
  1. schedule_db.py     → 数据库底层
  2. schedule_cli.py   → 本文件，AI分析+CLI逻辑
  3. SKILL.md          → 上层技能定义

增量同步逻辑（核心）：
  下次继续从最新的最后一条记录开始
"""

import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    init_db, get_last_record, get_prev_message,
    get_messages_after, get_messages_between,
    add_record, get_records_by_date, get_records_range,
    clear_date_records, save_daily_summary, get_daily_summary,
    get_summaries_range, get_connection, DB_PATH
)

# ============ AI 分析引擎 ============
CATEGORIES = {
    "睡眠": ["睡觉", "睡眠", "躺", "入睡", "睡着了", "困", "休息", "打盹", "午睡", "躺床上"],
    "工作": ["工作", "写代码", "上班", "开会", "改bug", "需求", "研发", "任务", "编写", "调试"],
    "学习": ["学习", "复习", "看书", "课程", "练", "背", "刷题", "算法", "学", "读", "笔记"],
    "运动": ["骑行", "骑车", "跑步", "锻炼", "俯卧撑", "健身", "运动", "散步"],
    "通勤": ["出发", "到达", "骑车上班", "通勤", "地铁", "公交", "打车", "开车"],
    "餐饮": ["吃饭", "午餐", "早餐", "晚餐", "点外卖", "外卖", "食堂", "烹饪", "做饭", "厨房"],
    "娱乐": ["游戏", "刷手机", "看视频", "短视频", "B站", "抖音", "bilibili", "youtube", "追剧"],
    "社交": ["女朋友", "洋洋", "约会", "聊天", "通话", "视频", "打电话", "发消息"],
    "休闲": ["休息", "放松", "摸鱼", "发呆", "躺", "听歌", "音乐"],
    "健康": ["医院", "看病", "买药", "检查", "身体"],
    "洗漱": ["洗澡", "刷牙", "洗脸", "沐浴", "洗", "上厕所"],
    "兴趣爱好": ["技能", "SKILL", "代码", "编程", "研究", "折腾", "优化", "写代码"],
    "未知": []
}

def classify_message(content):
    """根据消息内容判断分类，返回 (category, activity, confidence, reasoning)"""
    if not content:
        return "未知", "未知活动", "unknown", ""
    
    content_lower = content.lower()
    matched = []
    
    for cat, keywords in CATEGORIES.items():
        if cat == "未知":
            continue
        for kw in keywords:
            if kw.lower() in content_lower:
                matched.append((cat, kw))
                break
    
    if matched:
        cat = matched[0][0]
        kw = matched[0][1]
        reasoning = f"关键词「{kw}」匹配分类「{cat}」，消息内容：{content.strip()[:80]}"
        return cat, content.strip()[:60], "high", reasoning
    
    reasoning = f"未匹配到任何分类关键词，消息内容：{content.strip()[:80]}"
    return "未知", content.strip()[:60], "low", reasoning

def analyze_messages_to_blocks(messages):
    """
    把一组消息分析成作息时间块
    messages: list of (msg_id, time_str_HHMM, channel, content)
    返回: list of dict {time_start, time_end, activity, category, source_messages, source_message_times, analysis_reasoning, msg_ids}
    """
    if not messages:
        return []
    
    sorted_msgs = sorted(messages, key=lambda m: m[1])
    blocks = []
    
    for i, msg in enumerate(sorted_msgs):
        msg_id, time_hhmm, channel, content = msg
        if not content:
            continue
        
        category, activity, confidence, reasoning = classify_message(content)
        
        if i < len(sorted_msgs) - 1:
            next_hhmm = sorted_msgs[i + 1][1]
        else:
            h, m = map(int, time_hhmm.split(":"))
            total_min = h * 60 + m + 30
            next_hhmm = f"{total_min // 60:02d}:{total_min % 60:02d}"
        
        blocks.append({
            "time_start": time_hhmm,
            "time_end": next_hhmm,
            "activity": activity,
            "category": category,
            "confidence": confidence,
            "msg_ids": [msg_id],
            "msg_times": [time_hhmm],
            "msg_contents": [content[:100]],
            "reasonings": [reasoning],
            "source_messages": content[:200],
            "source_message_times": time_hhmm,
            "analysis_reasoning": reasoning
        })
    
    # 合并相邻同分类块（间隔<20分钟）
    return _merge_adjacent_blocks(blocks)

def _merge_adjacent_blocks(blocks):
    """合并相邻的同分类块（间隔<20分钟）"""
    if not blocks:
        return []
    
    merged = [blocks[0].copy()]
    
    for block in blocks[1:]:
        prev = merged[-1]
        time_gap = _time_diff_minutes(prev["time_end"], block["time_start"])
        
        if prev["category"] == block["category"] and time_gap < 20:
            # 合并
            prev["time_end"] = block["time_end"]
            prev["msg_ids"].extend(block["msg_ids"])
            prev["msg_times"].extend(block["msg_times"])
            prev["msg_contents"].extend(block["msg_contents"])
            prev["reasonings"].append(f"与上一块合并，间隔{time_gap}分钟")
            prev["confidence"] = "medium"
        else:
            merged.append(block.copy())
    
    # 构建最终字段
    result = []
    for b in merged:
        result.append({
            "time_start": b["time_start"],
            "time_end": b["time_end"],
            "activity": b["activity"],
            "category": b["category"],
            "confidence": b["confidence"],
            "source_messages": " || ".join(b["msg_contents"]),
            "source_message_times": ",".join(b["msg_times"]),
            "analysis_reasoning": " --> ".join(b["reasonings"])
        })
    
    return result

def _time_diff_minutes(t1, t2):
    """计算t2-t1的分钟数"""
    try:
        h1, m1 = map(int, t1.split(":"))
        h2, m2 = map(int, t2.split(":"))
        diff = (h2 * 60 + m2) - (h1 * 60 + m1)
        if diff < 0:
            diff += 1440
        return diff
    except:
        return 0

def calculate_daily_summary(records):
    """根据记录计算每日摘要"""
    summary = {
        "sleep": 0, "work": 0, "exercise": 0,
        "commute": 0, "eating": 0, "learning": 0,
        "entertainment": 0, "unknown": 0
    }
    
    category_map = {
        "睡眠": "sleep", "工作": "work", "运动": "exercise",
        "通勤": "commute", "餐饮": "eating", "学习": "learning",
        "娱乐": "entertainment", "未知": "unknown"
    }
    
    for rec in records:
        _, time_start, time_end, duration, activity, category, _, _, _ = rec
        minutes = duration or 0
        key = category_map.get(category, "unknown")
        summary[key] += minutes
    
    return summary

# ============ 核心同步逻辑 ============
def sync_incremental():
    """
    增量同步：自动找上次最后记录的位置，继续处理新消息
    """
    last = get_last_record()
    
    if last is None:
        print("  暂无记录，将从语录数据库中最早的记录开始...")
        target_date = date.today() - timedelta(days=1)
        print(f"  自动选择日期: {target_date}")
        return sync_date(target_date)
    
    last_date, last_time_start, last_time_end = last
    print(f"  最后记录: {last_date} {last_time_end}")
    
    last_time_str = f"{last_date} {last_time_end}:00"
    
    prev_msg = get_prev_message(last_time_str)
    if prev_msg:
        print(f"  上下文: {prev_msg[1]} - {prev_msg[3][:30]}...")
    
    new_messages = get_messages_after(last_time_str)
    print(f"  发现新消息: {len(new_messages)} 条")
    
    if not new_messages:
        print("  没有新消息")
        return
    
    date_groups = {}
    for msg in new_messages:
        msg_id, time_hhmm, channel, content = msg
        h = int(time_hhmm.split(":")[0])
        msg_date = last_date
        if h < 6 and last_date:
            from datetime import datetime
            d = datetime.strptime(last_date, "%Y-%m-%d") - timedelta(days=1)
            msg_date = d.strftime("%Y-%m-%d")
        
        if msg_date not in date_groups:
            date_groups[msg_date] = []
        date_groups[msg_date].append(msg)
    
    for msg_date, msgs in sorted(date_groups.items()):
        print(f"\n  处理日期: {msg_date}, 消息数: {len(msgs)}")
        
        clear_date_records(msg_date)
        
        blocks = analyze_messages_to_blocks(msgs)
        print(f"    生成 {len(blocks)} 个作息块")
        
        for block in blocks:
            add_record(
                date=msg_date,
                time_start=block["time_start"],
                time_end=block["time_end"],
                activity=block["activity"],
                category=block["category"],
                source_messages=block["source_messages"],
                source_message_times=block["source_message_times"],
                analysis_reasoning=block["analysis_reasoning"]
            )
        
        records = get_records_by_date(msg_date)
        summary = calculate_daily_summary(records)
        save_daily_summary(msg_date, summary)
    
    print("\n  增量同步完成")

def sync_date(target_date):
    """
    同步指定日期：从语录数据库读取该日期所有消息 → 生成作息记录
    """
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"[sync_date] 处理 {date_str}")
    
    start_time = f"{date_str} 00:00:00"
    end_time = f"{date_str} 23:59:59"
    messages = get_messages_between(start_time, end_time)
    print(f"  语录消息数: {len(messages)}")
    
    if not messages:
        print("  无消息，跳过")
        return
    
    clear_date_records(date_str)
    
    blocks = analyze_messages_to_blocks(messages)
    print(f"  生成 {len(blocks)} 个作息块")
    
    for block in blocks:
        add_record(
            date=date_str,
            time_start=block["time_start"],
            time_end=block["time_end"],
            activity=block["activity"],
            category=block["category"],
            source_messages=block["source_messages"],
            source_message_times=block["source_message_times"],
            analysis_reasoning=block["analysis_reasoning"]
        )
    
    records = get_records_by_date(date_str)
    summary = calculate_daily_summary(records)
    save_daily_summary(date_str, summary)
    
    print(f"  完成")

def auto_sync_days(days_back=3):
    """自动扫描过去N天"""
    init_db()
    today = date.today()
    
    for i in range(days_back, -1, -1):
        target = today - timedelta(days=i)
        sync_date(target)

# ============ CLI 命令 ============
def cmd_help():
    print("""
作息管家 CLI 用法：
    python schedule_cli.py init              # 初始化数据库
    python schedule_cli.py sync              # 增量同步（从最后记录继续）
    python schedule_cli.py sync <YYYY-MM-DD> # 同步指定日期
    python schedule_cli.py sync-days <N>     # 扫描过去N天
    python schedule_cli.py list [日期]        # 查看指定日期作息（默认今天）
    python schedule_cli.py summary [日期]     # 查看指定日期摘要
    python schedule_cli.py timeline [日期]    # 时间轴展示
    python schedule_cli.py report [日期]      # 完整报告
    python schedule_cli.py range <开始> <结束>  # 日期范围统计
    python schedule_cli.py status            # 数据库状态
    python schedule_cli.py detail [日期]     # 详细展示（含分析推理）
""")

def fmt_time(t):
    return t.split(":")[0] + ":" + t.split(":")[1] if ":" in t else t

def print_records(date_str, records):
    print(f"\n{'='*60}")
    print(f"📅 {date_str} 作息记录")
    print(f"{'='*60}")
    if not records:
        print("  （无记录）")
        return
    
    total_min = 0
    emoji_map = {
        "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
        "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
        "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
        "兴趣爱好": "🎨", "未知": "❓"
    }
    
    for rec in records:
        _, ts, te, dur, act, cat, src_msgs, src_times, reasoning = rec
        total_min += dur or 0
        emoji = emoji_map.get(cat, "📌")
        conf_mark = "✓" if len(src_msgs.split("||")) == 1 else "○"
        print(f"  {emoji} {fmt_time(ts)}~{fmt_time(te)} [{cat}] {conf_mark}")
        print(f"     {act[:45]}")
    
    print(f"\n  共 {len(records)} 块, 约 {total_min//60}h{total_min%60}m")

def print_detail(date_str, records):
    """详细展示，包含分析推理过程"""
    print(f"\n{'='*60}")
    print(f"📋 {date_str} 详细分析")
    print(f"{'='*60}")
    if not records:
        print("  （无记录）")
        return
    
    for rec in records:
        _, ts, te, dur, act, cat, src_msgs, src_times, reasoning = rec
        print(f"\n⏰ {fmt_time(ts)} ~ {fmt_time(te)} [{cat}] ({dur}min)")
        print(f"  活动: {act[:60]}")
        print(f"  消息来源: {src_msgs[:80]}...")
        print(f"  消息时间: {src_times}")
        print(f"  推理: {reasoning[:100]}...")

def print_summary(date_str, summary):
    print(f"\n📊 {date_str} 作息摘要")
    print(f"{'='*50}")
    
    items = [
        ("😴 睡眠", summary.get("sleep", 0)),
        ("💼 工作", summary.get("work", 0)),
        ("📚 学习", summary.get("learning", 0)),
        ("🏋️ 运动", summary.get("exercise", 0)),
        ("🚴 通勤", summary.get("commute", 0)),
        ("🍽️ 餐饮", summary.get("eating", 0)),
        ("🎮 娱乐", summary.get("entertainment", 0)),
        ("❓ 未知", summary.get("unknown", 0)),
    ]
    
    total = 0
    for label, minutes in items:
        if minutes > 0:
            print(f"  {label}: {minutes//60}h{minutes%60}m")
            total += minutes
    
    print(f"\n  总计: {total//60}h{total%60}m")

def cmd_list(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    print_records(date_str, records)

def cmd_detail(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    print_detail(date_str, records)

def cmd_summary(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    summary = get_daily_summary(date_str)
    if summary:
        print_summary(date_str, summary)
    else:
        print(f"  暂无 {date_str} 的摘要数据")

def cmd_timeline(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    
    print(f"\n⏰ {date_str} 时间轴")
    print(f"{'='*60}")
    
    if not records:
        print("  （无记录）")
        return
    
    emoji_map = {
        "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
        "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
        "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
        "兴趣爱好": "🎨", "未知": "❓"
    }
    
    timeline = ["  "] * 24
    for rec in records:
        _, ts, te, dur, act, cat, src_msgs, src_times, reasoning = rec
        try:
            h_start = int(ts.split(":")[0])
            h_end = int(te.split(":")[0]) if te else h_start + 1
        except:
            continue
        emoji = emoji_map.get(cat, "📌")
        label = cat[:2]
        
        for h in range(h_start, min(h_end + 1, 24)):
            timeline[h] = f"{emoji}{label}"
    
    for h in range(24):
        bar = "▓▓▓" if timeline[h] != "  " else "░░░"
        print(f"  {h:02d}:00 {bar} {timeline[h]}")

def cmd_report(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    summary = get_daily_summary(date_str)
    print_records(date_str, records)
    if summary:
        print_summary(date_str, summary)

def cmd_status():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM schedule_records')
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(DISTINCT date) FROM schedule_records')
    days = c.fetchone()[0]
    
    c.execute('SELECT MIN(date), MAX(date) FROM schedule_records')
    min_d, max_d = c.fetchone()
    
    last = get_last_record()
    
    print(f"""
作息管家 数据库状态
{'='*50}
  数据库: {DB_PATH}
  总记录数: {total}
  已记录天数: {days}
  日期范围: {min_d or '无'} ~ {max_d or '无'}
  最后记录: {last if last else '无'}
""")
    conn.close()

# ============ 主入口 ============
if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "init":
        init_db()
        print("✓ 数据库初始化完成")
    
    elif cmd == "sync":
        if args:
            target = datetime.strptime(args[0], "%Y-%m-%d").date()
            sync_date(target)
        else:
            sync_incremental()
    
    elif cmd == "sync-days":
        days = int(args[0]) if args else 3
        auto_sync_days(days)
    
    elif cmd == "list":
        cmd_list(args)
    
    elif cmd == "detail":
        cmd_detail(args)
    
    elif cmd == "summary":
        cmd_summary(args)
    
    elif cmd == "timeline":
        cmd_timeline(args)
    
    elif cmd == "report":
        cmd_report(args)
    
    elif cmd == "range":
        if len(args) >= 2:
            start, end = args[0], args[1]
            rows = get_summaries_range(start, end)
            print(f"\n📅 {start} ~ {end} 作息汇总\n{'='*60}")
            for row in rows:
                d, sl, wk, ex, cm, ea, ln, en, unk = row
                total = sl + wk + ex + cm + ea + ln + en + unk
                print(f"  {d}: 睡{sl//60}h 工{wk//60}h 学{ln//60}h 运{ex//60}h 娱{en//60}h 总{total//60}h")
        else:
            print("用法: schedule_cli.py range <开始> <结束>")
    
    elif cmd == "status":
        cmd_status()
    
    elif cmd == "help":
        cmd_help()
    
    else:
        print(f"未知命令: {cmd}")
        cmd_help()