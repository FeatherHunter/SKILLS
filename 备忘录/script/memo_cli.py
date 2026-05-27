#!/usr/bin/env python3
"""
备忘录 CLI 工具
所有命令返回 JSON 到标准输出
"""

import sys
import json
import sqlite3
import os
import argparse
from datetime import datetime, timedelta

from pathlib import Path

# ==================== 可配置常量 ====================
CRON_INTERVAL_MINUTES = 5          # cron执行间隔（分钟）
ADVANCE_TRIGGER_MINUTES = 10        # 提前a分钟触发（一次性提醒预通知）
GRACE_PERIOD_MULTIPLIER = 2         # 延后窗口 = cron间隔 × n
GRACE_PERIOD = CRON_INTERVAL_MINUTES * GRACE_PERIOD_MULTIPLIER  # 延后触发窗口（分钟）

DB_FILENAME = "memo.db"


# 三层查找DB路径：环境变量 SKILLS_DB_PATH > 父目录.db > 技能目录.db
def _find_db_path(skill_dir, db_filename):
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        return Path(env_path) / db_filename
    # 2. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return db_dir / db_filename
    # 3. 技能目录下 .db 子目录（默认 fallback）
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename

SKILL_DIR = Path(__file__).parent.parent
DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

def convert_weekday(user_weekday):
    """将用户输入的 weekday (0=周日) 转换为 Python weekday (0=周一)"""
    # 用户: 0=周日, 1=周一, 2=周二, 3=周三, 4=周四, 5=周五, 6=周六
    # Python: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
    return (user_weekday + 6) % 7

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def output_json(data, status="ok", message=""):
    print(json.dumps({"status": status, "data": data, "message": message}, ensure_ascii=False))
    sys.exit(0)

def error_json(message):
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
    sys.exit(1)

# ---- 笔记操作 ----

ALLOWED_CATEGORIES = {"社交", "心愿", "灵感", "成就", "工作", "学习", "记账", "打卡", "情绪", "general"}

def _resolve_media_path(media_arg):
    """处理媒体路径：必须以 MEMO_MEDIA_DIR 开头，存储时去掉前缀"""
    if not media_arg:
        return None
    media_dir = os.environ.get("MEMO_MEDIA_DIR", "media")
    # 确保 media_dir 以 / 结尾用于前缀匹配
    prefix = media_dir if media_dir.endswith("/") else media_dir + "/"
    if not media_arg.startswith(prefix) and media_arg != media_dir:
        error_json(f"媒体路径必须以 {media_dir} 开头，当前值: {media_arg}")
    # 去掉前缀，存储相对路径
    return media_arg[len(prefix):] if media_arg.startswith(prefix) else ""

def add_note(args):
    content = args.content
    if not content or not content.strip():
        error_json("笔记内容不能为空")
    category = args.category or "general"
    # ---- 分类白名单校验 ----
    if category not in ALLOWED_CATEGORIES:
        error_json(f"无效分类: {category}，允许的分类: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    media_path = _resolve_media_path(args.media)
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = conn.execute(
            "INSERT INTO notes (content, category, media_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (content.strip(), category, media_path, now, now)
        )
        note_id = cur.lastrowid
        conn.commit()
        output_json({"id": note_id, "content": content.strip(), "category": category}, message="笔记已添加")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def search_notes(args):
    keyword = args.keyword
    category = args.category
    limit = args.limit if args.limit is not None else 20
    if limit <= 0:
        error_json("limit 必须是正整数")
    conn = get_conn()
    try:
        if keyword:
            # 使用FTS5全文搜索
            sql = """
                SELECT n.* FROM notes n
                JOIN notes_fts f ON n.id = f.rowid
                WHERE notes_fts MATCH ?
            """
            params = [keyword]
            if category:
                sql += " AND n.category = ?"
                params.append(category)
            sql += " ORDER BY n.updated_at DESC LIMIT ?"
            params.append(limit)
            cur = conn.execute(sql, params)
        else:
            # 无关键词时按分类或全部列出
            sql = "SELECT * FROM notes WHERE 1=1"
            params = []
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            cur = conn.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        output_json(rows, message=f"找到 {len(rows)} 条笔记")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def update_note(args):
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    content = args.content
    category = args.category
    if category is not None and category not in ALLOWED_CATEGORIES:
        error_json(f"无效分类: {category}，允许的分类: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    media_path = _resolve_media_path(args.media) if args.media is not None else None
    reminder_id = args.reminder_id
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"笔记不存在: id={note_id}")
    try:
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content.strip())
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if media_path is not None:
            updates.append("media_path = ?")
            params.append(media_path)
        if reminder_id is not None:
            updates.append("reminder_id = ?")
            params.append(reminder_id)
        if not updates:
            error_json("至少需要提供一个更新字段: --content / --category / --media / --reminder-id")
        updates.append("updated_at = datetime('now','localtime')")
        params.append(note_id)
        conn.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        output_json({"id": note_id}, message="笔记已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def delete_note(args):
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"笔记不存在: id={note_id}")
    try:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        output_json({"id": note_id}, message="笔记已删除")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def get_note(args):
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    conn = get_conn()
    try:
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            error_json(f"笔记不存在: id={note_id}")
        output_json(dict(note))
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def _validate_date(date_str, field_name):
    """校验日期格式 YYYY-MM-DD"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt
    except ValueError:
        error_json(f"{field_name} 格式错误，要求 YYYY-MM-DD，当前值: {date_str}")

def search_by_date(args):
    start = args.start
    end = args.end
    start_dt = _validate_date(start, "start")
    end_dt = _validate_date(end, "end")
    if start_dt > end_dt:
        error_json(f"开始日期不能晚于结束日期: {start} > {end}")
    category = args.category
    limit = args.limit if args.limit is not None else 20
    if limit <= 0:
        error_json("limit 必须是正整数")
    conn = get_conn()
    try:
        sql = "SELECT * FROM notes WHERE created_at BETWEEN ? AND ?"
        params = [start, end]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        output_json(rows, message=f"找到 {len(rows)} 条笔记")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def update_category(args):
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    category = args.category
    if category not in ALLOWED_CATEGORIES:
        error_json(f"无效分类: {category}，允许的分类: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"笔记不存在: id={note_id}")
    try:
        conn.execute(
            "UPDATE notes SET category = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (category, note_id)
        )
        conn.commit()
        output_json({"id": note_id, "category": category}, message="分类已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

# ---- 提醒操作 ----

def _validate_remind_at(at_str):
    """校验 --at 时间格式 YYYY-MM-DD HH:MM"""
    if not at_str:
        return
    try:
        datetime.strptime(at_str, "%Y-%m-%d %H:%M")
    except ValueError:
        error_json(f"--at 格式错误，要求 YYYY-MM-DD HH:MM，当前值: {at_str}")

def _validate_repeat_rule(repeat_type, rule):
    """校验 --rule 格式是否匹配 --repeat-type"""
    if repeat_type == "一次性":
        return  # 一次性不需要 rule
    if not rule:
        error_json(f"--repeat-type={repeat_type} 时必须提供 --rule")
    parts = rule.strip().split(" ")
    try:
        if repeat_type == "每天":
            # 格式: "HH:MM"
            if len(parts) != 1:
                error_json(f"每天规则格式错误，要求 HH:MM，当前值: {rule}")
            h, m = parts[0].split(":")
            h, m = int(h), int(m)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                error_json(f"时间超出范围: {parts[0]}")
        elif repeat_type == "每周":
            # 格式: "W HH:MM" (W=0-6, 0=周日)
            if len(parts) != 2:
                error_json(f"每周规则格式错误，要求 W HH:MM，当前值: {rule}")
            w = int(parts[0])
            if not (0 <= w <= 6):
                error_json(f"星期超出范围 (0-6): {parts[0]}")
            h, m = parts[1].split(":")
            h, m = int(h), int(m)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                error_json(f"时间超出范围: {parts[1]}")
        elif repeat_type == "每月":
            # 格式: "D HH:MM" (D=1-31)
            if len(parts) != 2:
                error_json(f"每月规则格式错误，要求 D HH:MM，当前值: {rule}")
            d = int(parts[0])
            if not (1 <= d <= 31):
                error_json(f"日期超出范围 (1-31): {parts[0]}")
            h, m = parts[1].split(":")
            h, m = int(h), int(m)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                error_json(f"时间超出范围: {parts[1]}")
        elif repeat_type == "每年":
            # 格式: "MM-DD HH:MM"
            if len(parts) != 2:
                error_json(f"每年规则格式错误，要求 MM-DD HH:MM，当前值: {rule}")
            month, day = parts[0].split("-")
            month, day = int(month), int(day)
            if not (1 <= month <= 12):
                error_json(f"月份超出范围 (1-12): {month}")
            if not (1 <= day <= 31):
                error_json(f"日期超出范围 (1-31): {day}")
            h, m = parts[1].split(":")
            h, m = int(h), int(m)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                error_json(f"时间超出范围: {parts[1]}")
    except (ValueError, IndexError):
        error_json(f"--rule 格式错误，无法解析: {rule}")

def add_reminder(args):
    note_id = args.note_id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    remind_at = args.at
    repeat_type = args.repeat_type or "一次性"
    repeat_rule = args.rule
    # 校验 --at 格式
    _validate_remind_at(remind_at)
    # 校验 --rule 格式
    _validate_repeat_rule(repeat_type, repeat_rule)
    # 一次性必须有 --at
    if repeat_type == "一次性" and not remind_at:
        error_json("--repeat-type=一次性 时必须提供 --at")
    conn = get_conn()
    # 校验笔记存在
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"关联笔记不存在: id={note_id}")
    try:
        conn.execute(
            "INSERT INTO reminders (note_id, remind_at, repeat_type, repeat_rule, created_at) VALUES (?, ?, ?, ?, datetime('now','localtime'))",
            (note_id, remind_at, repeat_type, repeat_rule)
        )
        conn.commit()
        output_json({"note_id": note_id}, message="提醒已设置")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def list_due_reminders():
    """获取需要触发的提醒
    
    一次性：remind_at 日期 == 今天，且在触发窗口内
      提前a分钟：notified_at==None → 设置 notified_at
      准点（含容错T~T+窗口）：notified_at==None → 设置 notified_at + dismissed
    
    每天/每周/每月/每年：严格按 repeat_rule 解析判断
      repeat_rule 格式（Schema）：
        每天  : "HH:MM"            例 "09:00"
        每周  : "W HH:MM"          例 "5 17:00" (周五17:00)
        每月  : "D HH:MM"          例 "15 08:30" (每月15号08:30)
        每年  : "MM-DD HH:MM"      例 "12-25 10:00" (12月25日10:00)
      循环提醒触发后不标记 dismissed，只设置 notified_at
    
    配置常量：
      ADVANCE_TRIGGER_MINUTES = 提前触发分钟数（默认10）
      GRACE_PERIOD = 延后触发窗口（默认cron间隔×2）
    """
    conn = get_conn()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_date = now.strftime("%Y-%m-%d")
    now_minute = now.hour * 60 + now.minute
    
    due_items = []

    try:
        cur = conn.execute("""
            SELECT r.id, r.note_id, r.remind_at, r.repeat_type, r.repeat_rule,
                   r.notified_at, n.content
            FROM reminders r JOIN notes n ON r.note_id = n.id
            WHERE r.status = 'active'
        """)
        
        for row in cur.fetchall():
            reminder_id = row["id"]
            note_id = row["note_id"]
            remind_at = row["remind_at"]
            repeat_type = row["repeat_type"]
            repeat_rule = row["repeat_rule"]
            notified_at = row["notified_at"]
            content = row["content"]
            
            # ---- 解析 remind_at（带异常保护，畸形数据跳过）----
            remind_dt = None
            if remind_at:
                try:
                    remind_dt = datetime.strptime(remind_at, "%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    print(f"[警告] 提醒 {reminder_id} 的 remind_at 格式错误，已跳过: {remind_at}", file=sys.stderr)
                    continue
            
            # ---- 解析 repeat_rule（严格按 Schema 格式）----
            # 默认值：时间部分 fallback
            default_time = "09:00"
            if remind_dt:
                default_time = f"{remind_dt.hour:02d}:{remind_dt.minute:02d}"
            
            trigger_time_minute = None  # 触发时间（分钟整数，0-1440）
            in_cycle = False  # 是否在周期内
            
            if repeat_rule is None:
                # 无 repeat_rule → 退回一次性逻辑
                if repeat_type == "一次性" and remind_dt:
                    in_cycle = (today_date == remind_dt.strftime("%Y-%m-%d"))
                    trigger_time_minute = remind_dt.hour * 60 + remind_dt.minute
                else:
                    continue
            else:
                parts = repeat_rule.strip().split(" ")
                
                if repeat_type == "每天":
                    # repeat_rule = "HH:MM"
                    if len(parts) == 1:
                        hm = parts[0]
                        h = int(hm.split(":")[0])
                        m = int(hm.split(":")[1])
                        trigger_time_minute = h * 60 + m
                        in_cycle = True
                
                elif repeat_type == "每周":
                    # repeat_rule = "W HH:MM" (W=0=周日)
                    if len(parts) == 2:
                        try:
                            target_weekday = int(parts[0])  # 0=周日，6=周六
                            hm = parts[1]
                            h = int(hm.split(":")[0])
                            m = int(hm.split(":")[1])
                            trigger_time_minute = h * 60 + m
                            in_cycle = (now.weekday() == target_weekday)
                        except (ValueError, IndexError):
                            in_cycle = False
                
                elif repeat_type == "每月":
                    # repeat_rule = "D HH:MM" (D=1~31)
                    if len(parts) == 2:
                        try:
                            target_day = int(parts[0])
                            hm = parts[1]
                            h = int(hm.split(":")[0])
                            m = int(hm.split(":")[1])
                            trigger_time_minute = h * 60 + m
                            in_cycle = (now.day == target_day)
                        except (ValueError, IndexError):
                            in_cycle = False
                
                elif repeat_type == "每年":
                    # repeat_rule = "MM-DD HH:MM"
                    if len(parts) == 2:
                        try:
                            month_day = parts[0]  # "12-25"
                            month = int(month_day.split("-")[0])
                            day = int(month_day.split("-")[1])
                            hm = parts[1]
                            h = int(hm.split(":")[0])
                            m = int(hm.split(":")[1])
                            trigger_time_minute = h * 60 + m
                            in_cycle = (now.month == month and now.day == day)
                        except (ValueError, IndexError):
                            in_cycle = False
                
                elif repeat_type == "一次性":
                    # 一次性：有 repeat_rule 时视为时间，仅判断日期
                    if len(parts) == 1:
                        # 可能是 "HH:MM" 时间格式
                        if ":" in parts[0]:
                            hm = parts[0]
                            h = int(hm.split(":")[0])
                            m = int(hm.split(":")[1])
                            trigger_time_minute = h * 60 + m
                        else:
                            trigger_time_minute = 9 * 60  # 默认 9:00
                    if remind_dt:
                        in_cycle = (today_date == remind_dt.strftime("%Y-%m-%d"))
                        trigger_time_minute = remind_dt.hour * 60 + remind_dt.minute
                    else:
                        in_cycle = False
            
            # ---- 循环提醒的 cycle 判断（重置 notified_at）----
            # 在新周期开始时清除 notified_at，使提前触发和准点触发能再次工作
            if repeat_type != "一次性" and notified_at is not None:
                last_notified = datetime.strptime(notified_at, "%Y-%m-%d %H:%M:%S")
                if repeat_type == "每天":
                    if last_notified.date() < now.date():
                        notified_at = None  # 新的一天，重置
                elif repeat_type == "每周":
                    # 判断是否进入新的一周（按 ISO week）
                    last_year, last_week, _ = last_notified.isocalendar()
                    this_year, this_week, _ = now.isocalendar()
                    if (last_year, last_week) < (this_year, this_week):
                        notified_at = None  # 新的一周，重置
                elif repeat_type == "每月":
                    if last_notified.year < now.year or (last_notified.year == now.year and last_notified.month < now.month):
                        notified_at = None  # 新的一月，重置
                elif repeat_type == "每年":
                    if last_notified.year < now.year:
                        notified_at = None  # 新的一年，重置
            
            if not in_cycle or trigger_time_minute is None:
                continue
            
            # ---- 触发判断 ----
            advance_minute = trigger_time_minute - ADVANCE_TRIGGER_MINUTES
            if advance_minute < 0:
                advance_minute = 0
            
            triggered = False
            trigger_reason = ""
            
            # 条件1：提前a分钟（精确分钟匹配 + 未通知过）
            if notified_at is None and now_minute == advance_minute:
                triggered = True
                trigger_reason = "advance"
            
            # 条件2：准点（含延迟容错 T~T+窗口）
            if not triggered and notified_at is None:
                if trigger_time_minute <= now_minute <= trigger_time_minute + GRACE_PERIOD:
                    triggered = True
                    trigger_reason = "exact"
            
            if triggered:
                # display_time：循环提醒显示今天 HH:MM，一次性显示原始 remind_at
                if repeat_type == "一次性":
                    display_time = remind_at or f"{today_date} {default_time}"
                else:
                    h = trigger_time_minute // 60
                    m = trigger_time_minute % 60
                    display_time = f"{today_date} {h:02d}:{m:02d}"
                
                due_items.append({
                    "id": reminder_id,
                    "repeat_type": repeat_type,
                    "note_id": note_id,
                    "time": display_time,
                    "content": content,
                    "trigger_reason": trigger_reason
                })
                
                if trigger_reason == "advance":
                    conn.execute(
                        "UPDATE reminders SET notified_at = ? WHERE id = ?",
                        (now_str, reminder_id)
                    )
                elif trigger_reason == "exact":
                    if repeat_type == "一次性":
                        conn.execute(
                            "UPDATE reminders SET notified_at = ?, status = 'dismissed' WHERE id = ?",
                            (now_str, reminder_id)
                        )
                    else:
                        conn.execute(
                            "UPDATE reminders SET notified_at = ? WHERE id = ?",
                            (now_str, reminder_id)
                        )
        
        conn.commit()
        output_json(due_items, message=f"当前有 {len(due_items)} 个待提醒")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def dismiss_reminder(args):
    rid = args.id
    if rid <= 0:
        error_json("提醒 ID 必须是正整数")
    conn = get_conn()
    try:
        reminder = conn.execute("SELECT id, status FROM reminders WHERE id = ?", (rid,)).fetchone()
        if not reminder:
            error_json(f"提醒不存在: id={rid}")
        if reminder["status"] == "dismissed":
            error_json(f"提醒已经是废弃状态: id={rid}")
        conn.execute("UPDATE reminders SET status = 'dismissed' WHERE id = ?", (rid,))
        conn.commit()
        output_json({"id": rid}, message="提醒已废弃")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def completed_reminders(args):
    """查询已完成提醒：一次性提醒（已通知+打卡）或有打卡关联的重复提醒"""
    conn = get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()
        current_weekday = now.strftime("%w")  # 0=周日
        current_day = now.day
        current_month = now.month

        cur = conn.execute("""
            SELECT
                n.id as checkin_note_id,
                n.content as checkin_content,
                n.created_at as checkin_at,
                r.id as reminder_id,
                r.repeat_type,
                r.repeat_rule,
                r.notified_at,
                orig_n.content as reminder_content,
                orig_n.id as orig_note_id
            FROM notes n
            JOIN reminders r ON n.reminder_id = r.id
            JOIN notes orig_n ON r.note_id = orig_n.id
            WHERE n.category = '打卡' AND r.status = 'active'
            ORDER BY n.created_at DESC
        """)

        completed = []
        for row in cur.fetchall():
            d = dict(row)
            repeat_type = d["repeat_type"]
            repeat_rule = d["repeat_rule"] or ""
            checkin_time = datetime.strptime(d["checkin_at"], "%Y-%m-%d %H:%M:%S")
            checkin_date = checkin_time.strftime("%Y-%m-%d")

            # 一次性提醒：已通知即为完成
            if repeat_type == "一次性":
                if d["notified_at"]:
                    period = f"一次性 · {d['notified_at'][:16]}"
                    completed.append({
                        "reminder_id": d["reminder_id"],
                        "reminder_content": d["reminder_content"],
                        "checkin_note_id": d["checkin_note_id"],
                        "checkin_content": d["checkin_content"],
                        "checkin_at": d["checkin_at"][:16],
                        "period": period,
                        "repeat_type": "一次性"
                    })
                continue

            # 重复提醒：检查打卡时间是否在其当前周期内
            matched = False
            period = ""

            if repeat_type == "每天":
                # 每天：打卡日期 == 今天 → 今天完成
                if checkin_date == today:
                    matched = True
                    period = f"每天 {repeat_rule}"

            elif repeat_type == "每周":
                # 每周：打卡在当前自然周（本周一至今）内 且 星期对得上
                weekday_names = ["周日","周一","周二","周三","周四","周五","周六"]
                parts = repeat_rule.split()
                if len(parts) == 2:
                    rule_weekday = int(parts[0])   # 0=周日
                    rule_time = parts[1]
                    # 当前自然周的周一
                    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
                    if checkin_date >= week_start and checkin_date <= today:
                        if checkin_time.weekday() == rule_weekday:
                            matched = True
                            period = f"每周{weekday_names[rule_weekday]} {rule_time}"

            elif repeat_type == "每月":
                # 每月：打卡在当月内 且 日期对得上
                parts = repeat_rule.split()
                if len(parts) == 2:
                    rule_day = int(parts[0])
                    rule_time = parts[1]
                    # 当月1号至今
                    month_start = now.strftime("%Y-%m") + "-01"
                    if checkin_date >= month_start and checkin_date <= today:
                        if checkin_time.day == rule_day:
                            matched = True
                            period = f"每月{rule_day}号 {rule_time}"

            elif repeat_type == "每年":
                # 每年：打卡在年内 且 月-日对得上
                parts = repeat_rule.split()
                if len(parts) == 2:
                    rule_md = parts[0]   # MM-DD
                    rule_time = parts[1]
                    # 当年1月1日至今
                    year_start = now.strftime("%Y") + "-01-01"
                    if checkin_date >= year_start and checkin_date <= today:
                        if checkin_time.strftime("%m-%d") == rule_md:
                            matched = True
                            period = f"每年{rule_md} {rule_time}"

            if matched:
                completed.append({
                    "reminder_id": d["reminder_id"],
                    "reminder_content": d["reminder_content"],
                    "checkin_note_id": d["checkin_note_id"],
                    "checkin_content": d["checkin_content"],
                    "checkin_at": d["checkin_at"][:16],
                    "period": period,
                    "repeat_type": repeat_type
                })

        output_json(completed, message=f"共 {len(completed)} 条已完成提醒")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def list_reminders(args):
    status_filter = args.status or "active"
    if status_filter not in ("active", "dismissed"):
        error_json(f"无效状态: {status_filter}，允许的值: active, dismissed")
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT r.*, n.content FROM reminders r
            JOIN notes n ON r.note_id = n.id
            WHERE r.status = ?
            ORDER BY r.remind_at, r.repeat_type
        """, (status_filter,))
        rows = [dict(row) for row in cur.fetchall()]
        output_json(rows)
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

# ---- 主程序 ----

def main():
    parser = argparse.ArgumentParser(description="备忘录 CLI")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add")
    p_add.add_argument("content")
    p_add.add_argument("--category", "-c")
    p_add.add_argument("--media", "-m")

    # search
    p_search = sub.add_parser("search")
    p_search.add_argument("keyword", nargs="?", default="")
    p_search.add_argument("--category", "-c")
    p_search.add_argument("--limit", "-l", type=int)

    # update
    p_update = sub.add_parser("update")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--content")
    p_update.add_argument("--category", "-c")
    p_update.add_argument("--media", "-m")
    p_update.add_argument("--reminder-id", type=int)

    # delete
    p_del = sub.add_parser("delete")
    p_del.add_argument("id", type=int)

    # get note
    p_get = sub.add_parser("get")
    p_get.add_argument("id", type=int)

    # search by date
    p_date = sub.add_parser("search-date")
    p_date.add_argument("start", help="开始时间 YYYY-MM-DD")
    p_date.add_argument("end", help="结束时间 YYYY-MM-DD")
    p_date.add_argument("--category", "-c")
    p_date.add_argument("--limit", "-l", type=int)

    # update category
    p_cat = sub.add_parser("update-category")
    p_cat.add_argument("id", type=int)
    p_cat.add_argument("category")

    # reminder add
    p_remind = sub.add_parser("remind")
    p_remind.add_argument("note_id", type=int)
    p_remind.add_argument("--at")
    p_remind.add_argument("--repeat-type", choices=["一次性","每天","每周","每月","每年"], default="一次性")
    p_remind.add_argument("--rule")

    # due
    p_due = sub.add_parser("due")
    p_due.add_argument("--db", help="数据库路径覆盖")

    # dismiss reminder
    p_dismiss = sub.add_parser("dismiss")
    p_dismiss.add_argument("id", type=int)

    # list reminders
    p_lr = sub.add_parser("reminders")
    p_lr.add_argument("--status", "-s", default="active")

    # completed reminders
    p_completed = sub.add_parser("completed")

    args = parser.parse_args()

    if args.command == "add":
        add_note(args)
    elif args.command == "search":
        search_notes(args)
    elif args.command == "update":
        update_note(args)
    elif args.command == "delete":
        delete_note(args)
    elif args.command == "get":
        get_note(args)
    elif args.command == "search-date":
        search_by_date(args)
    elif args.command == "update-category":
        update_category(args)
    elif args.command == "remind":
        add_reminder(args)
    elif args.command == "due":
        # 支持 --db 参数覆盖 DB_PATH
        if args.db:
            import memo_cli
            memo_cli.DB_PATH = args.db
        list_due_reminders()
    elif args.command == "dismiss":
        dismiss_reminder(args)
    elif args.command == "reminders":
        list_reminders(args)
    elif args.command == "completed":
        completed_reminders(args)
    else:
        parser.print_help()
        error_json("未知命令")

if __name__ == "__main__":
    main()