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
    try:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        output_json({"id": note_id}, message="笔记已删除")
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
    """获取未来10分钟内需要触发的提醒"""
    conn = get_conn()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    window_end = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    due_items = []

    try:
        # 一次性提醒
        cur = conn.execute("""
            SELECT r.id, r.note_id, r.remind_at, n.content
            FROM reminders r JOIN notes n ON r.note_id = n.id
            WHERE r.status = 'active' AND r.repeat_type = 'none'
              AND r.remind_at BETWEEN ? AND ?
        """, (now_str, window_end))
        for row in cur.fetchall():
            due_items.append({
                "id": row["id"],
                "type": "once",
                "note_id": row["note_id"],
                "time": row["remind_at"],
                "content": row["content"]
            })

        # 重复提醒：逐条解析规则计算虚拟时间
        cur = conn.execute("""
            SELECT r.id, r.note_id, r.repeat_type, r.repeat_rule, n.content
            FROM reminders r JOIN notes n ON r.note_id = n.id
            WHERE r.status = 'active' AND r.repeat_type != 'none'
        """)
        for row in cur.fetchall():
            rule = row["repeat_rule"]
            rtype = row["repeat_type"]
            if not rule:
                continue
            virt_time = None
            try:
                if rtype == "daily":
                    # 规则 "09:00"
                    t = datetime.strptime(rule, "%H:%M").time()
                    virt_time = datetime.combine(now.date(), t)
                elif rtype == "weekly":
                    # "3 09:00"
                    parts = rule.split()
                    weekday = int(parts[0])
                    t = datetime.strptime(parts[1], "%H:%M").time()
                    # 计算本周的这一天
                    days_until = (weekday - now.weekday()) % 7
                    target_date = now.date() + timedelta(days=days_until)
                    virt_time = datetime.combine(target_date, t)
                elif rtype == "monthly":
                    # "15 08:30"
                    parts = rule.split()
                    day = int(parts[0])
                    t = datetime.strptime(parts[1], "%H:%M").time()
                    target_date = now.date().replace(day=day)
                    if target_date < now.date():
                        # 本月已过，计算下个月
                        if target_date.month == 12:
                            target_date = target_date.replace(year=target_date.year+1, month=1)
                        else:
                            target_date = target_date.replace(month=target_date.month+1)
                    virt_time = datetime.combine(target_date, t)
                elif rtype == "yearly":
                    # "12-25 10:00"
                    parts = rule.split()
                    md = parts[0]
                    t = datetime.strptime(parts[1], "%H:%M").time()
                    month, day = map(int, md.split("-"))
                    target_date = now.date().replace(month=month, day=day)
                    if target_date < now.date():
                        target_date = target_date.replace(year=target_date.year+1)
                    virt_time = datetime.combine(target_date, t)
            except:
                continue

            if virt_time:
                if now <= virt_time <= window_end:
                    due_items.append({
                        "id": row["id"],
                        "type": rtype,
                        "note_id": row["note_id"],
                        "time": virt_time.strftime("%Y-%m-%d %H:%M"),
                        "content": row["content"]
                    })

        # 将过期的 active 一次性提醒标记为 dismissed
        conn.execute("""
            UPDATE reminders SET status = 'dismissed'
            WHERE status = 'active' AND repeat_type = 'none'
              AND remind_at < ?
        """, (now_str,))
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

    # reminder add
    p_remind = sub.add_parser("remind")
    p_remind.add_argument("note_id", type=int)
    p_remind.add_argument("--at")
    p_remind.add_argument("--repeat-type", choices=["none","daily","weekly","monthly","yearly"], default="none")
    p_remind.add_argument("--rule")

    # due
    p_due = sub.add_parser("due")

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
    elif args.command == "remind":
        add_reminder(args)
    elif args.command == "due":
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