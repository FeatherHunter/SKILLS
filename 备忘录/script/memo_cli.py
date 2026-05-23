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

DB_PATH = os.environ.get("MEMO_DB_PATH", os.path.join(os.path.dirname(__file__), "../memo.db"))

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

def add_note(args):
    content = args.content
    category = args.category or "general"
    media_path = args.media
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = conn.execute(
            "INSERT INTO notes (content, category, media_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (content, category, media_path, now, now)
        )
        note_id = cur.lastrowid
        conn.commit()
        output_json({"id": note_id, "content": content, "category": category}, message="笔记已添加")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def search_notes(args):
    keyword = args.keyword
    category = args.category
    limit = args.limit or 20
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
    content = args.content
    category = args.category
    media_path = args.media
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json("笔记不存在")
    try:
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if media_path is not None:
            updates.append("media_path = ?")
            params.append(media_path)
        if not updates:
            error_json("没有提供要更新的字段")
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
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json("笔记不存在")
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
    conn = get_conn()
    try:
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            error_json("笔记不存在")
        output_json(dict(note))
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def search_by_date(args):
    start = args.start
    end = args.end
    category = args.category
    limit = args.limit or 20
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
    category = args.category
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json("笔记不存在")
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

def add_reminder(args):
    note_id = args.note_id
    remind_at = args.at      # 一次性时间 "YYYY-MM-DD HH:MM"
    repeat_type = args.repeat_type or "none"
    repeat_rule = args.rule
    conn = get_conn()
    # 校验笔记存在
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json("关联笔记不存在")
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
    
    两个独立条件，满足其一即触发：
    1. 提前10分钟：当前时间 HH:MM == remind_at - 10分钟，且未提前通知过
    2. 准点：当前时间分钟 == remind_at分钟（秒数忽略），且未准时通知过
    """
    conn = get_conn()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 计算提前10分钟的时间点
    advance_10 = now - timedelta(minutes=10)
    advance_10_str = advance_10.strftime("%Y-%m-%d %H:%M")  # 用于精确匹配 HH:MM
    now_minute = now.minute
    
    due_items = []

    try:
        # 查询所有 active 的一次性提醒
        cur = conn.execute("""
            SELECT r.id, r.note_id, r.remind_at, r.notified_at, n.content
            FROM reminders r JOIN notes n ON r.note_id = n.id
            WHERE r.status = 'active' AND r.repeat_type = 'none'
        """)
        
        for row in cur.fetchall():
            reminder_id = row["id"]
            note_id = row["note_id"]
            remind_at = row["remind_at"]
            notified_at = row["notified_at"]
            content = row["content"]
            
            # 解析 remind_at 的小时和分钟
            remind_dt = datetime.strptime(remind_at, "%Y-%m-%d %H:%M")
            remind_hour = remind_dt.hour
            remind_minute = remind_dt.minute
            
            # 计算提前10分钟的时间点（HH:MM）
            advance_dt = remind_dt - timedelta(minutes=10)
            advance_hhmm = advance_dt.strftime("%H:%M")
            
            # 当前时间 HH:MM
            now_hhmm = now.strftime("%H:%M")
            
            triggered = False
            trigger_reason = ""
            
            # 条件1：提前10分钟（精确匹配 HH:MM）
            if now_hhmm == advance_hhmm and notified_at is None:
                triggered = True
                trigger_reason = "advance"
            
            # 条件2：准点（分钟匹配，秒数忽略）
            # 注意：这里需要排除条件1已经触发的情况，避免重复记录
            elif now_minute == remind_minute:
                triggered = True
                trigger_reason = "exact"
            
            if triggered:
                due_items.append({
                    "id": reminder_id,
                    "type": "once",
                    "note_id": note_id,
                    "time": remind_at,
                    "content": content,
                    "trigger_reason": trigger_reason
                })
                if trigger_reason == "advance":
                    # 条件1：提前10分钟，只设置 notified_at，不标记 dismissed
                    conn.execute(
                        "UPDATE reminders SET notified_at = ? WHERE id = ?",
                        (now_str, reminder_id)
                    )
                elif trigger_reason == "exact":
                    # 条件2：准点，设置 notified_at 并标记为 dismissed
                    conn.execute(
                        "UPDATE reminders SET notified_at = ?, status = 'dismissed' WHERE id = ?",
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
    conn = get_conn()
    try:
        conn.execute("UPDATE reminders SET status = 'dismissed' WHERE id = ?", (rid,))
        conn.commit()
        output_json({"id": rid}, message="提醒已废弃")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def list_reminders(args):
    status_filter = args.status or "active"
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
    p_remind.add_argument("--repeat-type", choices=["none","daily","weekly","monthly","yearly"], default="none")
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
    else:
        parser.print_help()
        error_json("未知命令")

if __name__ == "__main__":
    main()