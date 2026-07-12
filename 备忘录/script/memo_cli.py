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


def _fallback_db_dir():
    """全局 fallback DB 目录：Windows → D:/.db，WSL → /mnt/d/.db"""
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    raise RuntimeError(
        'SKILLS_DB_PATH 未设置，且 D: 盘未挂载到 /mnt/d/。'
        '请检查 WSL automount 配置或设置 SKILLS_DB_PATH 环境变量。'
    )

# 两层查找DB路径：环境变量 SKILLS_DB_PATH > D:\.db\
def _find_db_path(skill_dir, db_filename):
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        return Path(env_path) / db_filename
    # 2. fallback: D:\.db\（WSL 自动转 /mnt/d/.db/）
    db_dir = _fallback_db_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / db_filename

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

ALLOWED_CATEGORIES = {"备忘", "心愿", "打卡", "情绪日记"}
# sub_category 是自由文本字段，不设白名单
# AI 智能从用户原话推断 1 个 2 字，推断不出则 NULL

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
    category = args.category or "备忘"
    # ---- 顶层分类白名单校验 ----
    if category not in ALLOWED_CATEGORIES:
        error_json(f"无效分类: {category}，允许的分类: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    # ---- sub_category：自由文本，不做白名单校验，AI 智能推断 1 个 2 字 ----
    sub_category = args.sub_category
    media_path = _resolve_media_path(args.media)
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = conn.execute(
            "INSERT INTO notes (content, category, sub_category, media_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (content.strip(), category, sub_category, media_path, now, now)
        )
        note_id = cur.lastrowid
        conn.commit()

        # 飞书同步 hook（第一性：自动检测 CLI，无开关）
        # 仅 category=心愿 时联动飞书（其他类别不联动）
        feishu_sync_result = None
        if category == "心愿":
            try:
                from feishu_sync import is_feishu_available, add_wish_sync
                if is_feishu_available():
                    # tasklist_guid 由调用方通过 --tasklist-guid 显式传入（不读环境变量）
                    sync_r = add_wish_sync(
                        note_id, content.strip(), category,
                        tasklist_guid=getattr(args, 'tasklist_guid', None),
                    )
                    if sync_r.get("ok") and sync_r.get("task_guid"):
                        # 把 task_guid 写回 notes.feishu_task_guid
                        conn.execute(
                            "UPDATE notes SET feishu_task_guid = ? WHERE id = ?",
                            (sync_r["task_guid"], note_id),
                        )
                        conn.commit()
                        feishu_sync_result = {"synced": True, "task_guid": sync_r["task_guid"]}
                    else:
                        feishu_sync_result = {"synced": False, "error": sync_r.get("error")}
                else:
                    feishu_sync_result = {"synced": False, "reason": "feishu CLI not available"}
            except Exception as e:
                feishu_sync_result = {"synced": False, "error": str(e)}

        out_data = {"id": note_id, "content": content.strip(), "category": category, "sub_category": sub_category}
        if feishu_sync_result is not None:
            out_data["feishu_sync"] = feishu_sync_result
        output_json(out_data, message="笔记已添加")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def search_notes(args):
    keyword = args.keyword
    category = args.category
    sub_category = getattr(args, 'sub_category', None)
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
            if sub_category:
                sql += " AND n.sub_category = ?"
                params.append(sub_category)
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
            if sub_category:
                sql += " AND sub_category = ?"
                params.append(sub_category)
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
    sub_category = getattr(args, 'sub_category', None)
    if category is not None and category not in ALLOWED_CATEGORIES:
        error_json(f"无效分类: {category}，允许的分类: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    # sub_category：自由文本，不做白名单校验
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
        if sub_category is not None:
            # sub_category 自由文本,适用于所有 category,不再校验 effective_cat == "备忘"
            updates.append("sub_category = ?")
            params.append(sub_category)
        if media_path is not None:
            updates.append("media_path = ?")
            params.append(media_path)
        if reminder_id is not None:
            updates.append("reminder_id = ?")
            params.append(reminder_id)
        if not updates:
            error_json("至少需要提供一个更新字段: --content / --category / --sub-category / --media / --reminder-id")
        updates.append("updated_at = datetime('now','localtime')")
        params.append(note_id)
        conn.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        # 飞书同步 hook（content 变化时同步更新飞书 task）
        feishu_sync_result = None
        new_content = content.strip() if content is not None else None
        if new_content is not None:
            try:
                from feishu_sync import is_feishu_available, update_wish_sync
                note_row = conn.execute("SELECT category, feishu_task_guid FROM notes WHERE id = ?", (note_id,)).fetchone()
                if note_row and note_row["category"] == "心愿" and note_row["feishu_task_guid"] and is_feishu_available():
                    sync_r = update_wish_sync(note_row["feishu_task_guid"], new_content)
                    feishu_sync_result = {"synced": sync_r.get("ok", False), "error": sync_r.get("error")}
                elif note_row and note_row["category"] == "心愿" and not is_feishu_available():
                    feishu_sync_result = {"synced": False, "reason": "feishu CLI not available"}
            except Exception as e:
                feishu_sync_result = {"synced": False, "error": str(e)}

        out_data = {"id": note_id}
        if feishu_sync_result is not None:
            out_data["feishu_sync"] = feishu_sync_result
        output_json(out_data, message="笔记已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()

def delete_note(args):
    """删除笔记（可选级联删提醒）

    用法：
      memo_cli.py delete <id>                         # 有关联提醒则报错
      memo_cli.py delete <id1> <id2> ...              # 批量
      memo_cli.py delete <id> --with-reminders        # 关联提醒一并删，active 提醒交互确认
      memo_cli.py delete <id> --with-reminders -y     # 跳过确认（自动化用）
    """
    note_ids = args.id
    with_reminders = getattr(args, 'with_reminders', False)
    auto_yes = getattr(args, 'yes', False)

    # 校验：所有 id 必须是正整数
    for nid in note_ids:
        if nid <= 0:
            error_json("笔记 ID 必须是正整数")

    conn = get_conn()
    try:
        # 1. 校验所有笔记存在
        existing = []
        for nid in note_ids:
            row = conn.execute("SELECT id, content FROM notes WHERE id = ?", (nid,)).fetchone()
            if not row:
                error_json(f"笔记不存在: id={nid}")
            existing.append(row)

        # 2. 收集所有关联的提醒
        related_reminders = []
        for nid in note_ids:
            rems = conn.execute(
                "SELECT id, note_id, remind_at, repeat_type, status, content FROM reminders WHERE note_id = ?",
                (nid,)
            ).fetchall()
            related_reminders.extend(rems)

        # 2.5 收集所有心愿 note 的 feishu_task_guid（删除前快照，用于飞书同步）
        wish_sync_targets = []  # [(memo_id, task_guid, category), ...]
        for nid in note_ids:
            row = conn.execute(
                "SELECT id, category, feishu_task_guid FROM notes WHERE id = ?",
                (nid,),
            ).fetchone()
            if row and row["category"] == "心愿" and row["feishu_task_guid"]:
                wish_sync_targets.append((row["id"], row["feishu_task_guid"], row["category"]))

        # 3. 如果有关联提醒但没传 --with-reminders → 报错提示
        if related_reminders and not with_reminders:
            error_json(
                f"笔记 {note_ids} 关联 {len(related_reminders)} 个提醒，"
                f"请加 --with-reminders 参数级联删除（提醒不会被自动删除）"
            )

        # 4. 如果有 active 提醒且无 -y → 交互式二次确认
        active_reminders = [r for r in related_reminders if r['status'] == 'active']
        if with_reminders and active_reminders and not auto_yes:
            print("⚠️ 以下提醒状态为 active（未触发），确认删除？", flush=True)
            for r in active_reminders:
                print(
                    f"  - ID {r['id']} [active] {r['remind_at']} {r['repeat_type']} "
                    f"笔记 {r['note_id']} | {r['content']}",
                    flush=True
                )
            print("  以及其他 dismissed 提醒一并删除。", flush=True)
            try:
                ans = input("确认删除？(y/N): ").strip().lower()
            except EOFError:
                ans = 'n'
            if ans != 'y':
                output_json({"cancelled": True}, message="已取消删除")

        # 5. 执行删除：先删 reminders，再删 notes（避开外键约束）
        deleted_reminder_ids = []
        if with_reminders and related_reminders:
            for r in related_reminders:
                conn.execute("DELETE FROM reminders WHERE id = ?", (r['id'],))
                deleted_reminder_ids.append(r['id'])

        deleted_note_ids = []
        for nid in note_ids:
            conn.execute("DELETE FROM notes WHERE id = ?", (nid,))
            deleted_note_ids.append(nid)

        conn.commit()

        # 6.5 飞书同步 hook（删除心愿时标飞书 task 完成）
        # 必须在 output_json 之前执行（output_json 会 sys.exit）
        feishu_sync_results = []
        if wish_sync_targets:
            try:
                from feishu_sync import is_feishu_available, complete_wish_sync
                if is_feishu_available():
                    for memo_id, task_guid, _cat in wish_sync_targets:
                        sync_r = complete_wish_sync(task_guid)
                        feishu_sync_results.append({
                            "memo_id": memo_id,
                            "task_guid": task_guid,
                            "synced": sync_r.get("ok", False),
                            "error": sync_r.get("error"),
                        })
                else:
                    for memo_id, task_guid, _cat in wish_sync_targets:
                        feishu_sync_results.append({
                            "memo_id": memo_id,
                            "task_guid": task_guid,
                            "synced": False,
                            "reason": "feishu CLI not available",
                        })
            except Exception as e:
                for memo_id, task_guid, _cat in wish_sync_targets:
                    feishu_sync_results.append({"memo_id": memo_id, "task_guid": task_guid, "error": str(e)})

        # 7. 输出结果（合并 feishu_sync）
        result = {
            "deleted_notes": deleted_note_ids,
            "deleted_reminders": deleted_reminder_ids,
        }
        if active_reminders:
            result["active_reminders_deleted"] = len(active_reminders)
        if feishu_sync_results:
            result["feishu_sync"] = feishu_sync_results

        if deleted_reminder_ids:
            msg = f"已删除 {len(deleted_note_ids)} 个笔记 + {len(deleted_reminder_ids)} 个提醒"
            if active_reminders:
                msg += f"（含 {len(active_reminders)} 个未触发）"
        else:
            msg = f"已删除 {len(deleted_note_ids)} 个笔记"

        output_json(result, message=msg)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        error_json(str(e))
    finally:
        conn.close()

def complete_wish(args):
    """第一性：心愿完成的本质是原子转换——'待完成项'变成'已完成记录'。

    行为：
      1. 找到 category='心愿' 的 note（闸门：只处理心愿）
      2. DELETE 该心愿 note（关联 reminders 已手动先删，外键 ON DELETE NO ACTION 不阻塞）
      3. INSERT 一条 category='打卡' 的新 note，content 默认拷贝原心愿
      4. 整个过程在单个事务里，失败回滚

    设计取舍（第一性推导）：
      - 不写 reminder_id：CASCADE 删 reminders 后 reminder_id 必然悬空，留 NULL 更干净
      - 硬删除：不软删除，违背"流式工作流"的本质
      - content 默认拷贝：content 是用户原话，没提供则用心愿原文
    """
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    conn = get_conn()
    try:
        # Step 1: 识别"是不是心愿"——第一道闸门，同时取 feishu_task_guid 快照
        wish = conn.execute(
            "SELECT id, content, feishu_task_guid FROM notes WHERE id = ? AND category = '心愿'",
            (note_id,)
        ).fetchone()
        if not wish:
            error_json(f"心愿不存在或非心愿分类: id={note_id}")
        wish_feishu_task_guid = wish["feishu_task_guid"]  # 删除前快照

        # Step 2: 决定打卡 content
        # 第一性：content 是用户原话。用户提供 → 用用户的；没提供 → 拷贝心愿原文
        if args.content and args.content.strip():
            checkin_content = args.content.strip()
        else:
            checkin_content = wish["content"]

        # Step 3: 原子事务
        # 第一性：真实 DB 的 reminders FK 是 NO ACTION（不是 CASCADE），
        #         必须先删 reminders 再删 note，否则 FK 约束失败
        #         不论 FK 是 CASCADE 还是 NO ACTION，手动先删都安全
        conn.execute("DELETE FROM reminders WHERE note_id = ?", (note_id,))
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        cur = conn.execute(
            """INSERT INTO notes (content, category, created_at, updated_at)
               VALUES (?, '打卡', datetime('now','localtime'), datetime('now','localtime'))""",
            (checkin_content,)
        )
        checkin_id = cur.lastrowid
        conn.commit()

        # 飞书同步 hook（第一性：自动检测 CLI，无开关；本地优先，飞书失败不影响本地）
        # 用 wish_feishu_task_guid（删除前快照）调 complete_wish_sync
        feishu_sync_result = None
        try:
            from feishu_sync import is_feishu_available, complete_wish_sync
            if wish_feishu_task_guid and is_feishu_available():
                sync_r = complete_wish_sync(wish_feishu_task_guid)
                feishu_sync_result = {
                    "synced": sync_r.get("ok", False),
                    "task_guid": wish_feishu_task_guid,
                    "error": sync_r.get("error"),
                }
            elif wish_feishu_task_guid:
                feishu_sync_result = {
                    "synced": False,
                    "task_guid": wish_feishu_task_guid,
                    "reason": "feishu CLI not available",
                }
        except Exception as e:
            feishu_sync_result = {"synced": False, "reason": "exception", "error": str(e)}

        out_data = {
            "deleted_wish_id": note_id,
            "created_checkin_id": checkin_id,
            "checkin_content": checkin_content,
        }
        if feishu_sync_result is not None:
            out_data["feishu_sync"] = feishu_sync_result
        output_json(out_data, message=f"✓ 心愿 #{note_id} 已完成，打卡 #{checkin_id} 已记录")
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
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
    note = conn.execute("SELECT id, category, sub_category FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"笔记不存在: id={note_id}")
    try:
        # sub_category 是内容维度的二阶属性,改顶层分类不联动清空
        conn.execute(
            "UPDATE notes SET category = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (category, note_id)
        )
        conn.commit()
        output_json({"id": note_id, "category": category, "sub_category": note["sub_category"]}, message="分类已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()


def update_sub_category(args):
    """单独修改 sub_category（不动 category）。适用于所有 category（sub_category 是自由文本）。"""
    note_id = args.id
    if note_id <= 0:
        error_json("笔记 ID 必须是正整数")
    sub_category = args.sub_category
    # 允许清除（传空字符串或 "null" 或 NULL）
    if sub_category in ("", "null", "NULL", "None"):
        sub_category = None
    # sub_category：自由文本，不做白名单校验（适用于所有 category）
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json(f"笔记不存在: id={note_id}")
    try:
        conn.execute(
            "UPDATE notes SET sub_category = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (sub_category, note_id)
        )
        conn.commit()
        output_json({"id": note_id, "sub_category": sub_category}, message="子分类已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()


def set_due(args):
    """心愿排期:批量设置心愿 due 日期,同步飞书 task due

    第一性:
      - 备忘录 notes.due 是 SoT,飞书 task.due 是镜像
      - 飞书 update 失败不阻塞本地:本地写入始终成功,errors 累积

    用法:
      memo_cli.py set-due 123 124 125 --due 2026-06-30
      memo_cli.py set-due 123 --due 2026-06-30           # 单条
      memo_cli.py set-due 123 --due null                 # 清除 due
    """
    note_ids = args.ids
    if not note_ids:
        error_json("至少提供一个笔记 ID")

    due_raw = args.due
    # 允许清除 (传 null/空/NULL/None)
    if due_raw in ("", "null", "NULL", "None"):
        due_iso = None
    else:
        # 校验 YYYY-MM-DD 格式
        try:
            datetime.strptime(due_raw, "%Y-%m-%d")
            due_iso = due_raw
        except ValueError:
            error_json(f"due 必须是 YYYY-MM-DD 格式或 null,当前: {due_raw}")

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    try:
        # 飞书同步 lazy import(避免 add/等命令不依赖 lark-cli)
        try:
            from feishu_sync import is_feishu_available, update_due_sync, clear_due_sync
            feishu_ready = is_feishu_available()
        except Exception:
            feishu_ready = False
            update_due_sync = None
            clear_due_sync = None

        result = {
            "requested": len(note_ids),
            "updated": 0,
            "skipped_not_wish": 0,
            "skipped_not_found": 0,
            "feishu_synced": 0,
            "errors": [],
        }
        for nid in note_ids:
            note = conn.execute(
                "SELECT id, category, feishu_task_guid FROM notes WHERE id = ?", (nid,)
            ).fetchone()
            if not note:
                result["skipped_not_found"] += 1
                result["errors"].append(f"id={nid}: not found")
                continue
            if note["category"] != "心愿":
                result["skipped_not_wish"] += 1
                result["errors"].append(f"id={nid}: category={note['category']} 不是心愿")
                continue

            # 本地写入 (SoT)
            conn.execute(
                "UPDATE notes SET due = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (due_iso, nid),
            )
            result["updated"] += 1

            # 飞书同步 (镜像) - 根据 due_iso 真值分流:
            #   due_iso 非空 → update_due_sync (已有)
            #   due_iso 为空 → clear_due_sync (新增,飞书 task due 字段清空)
            if note["feishu_task_guid"]:
                if not feishu_ready:
                    result["errors"].append(f"id={nid}: 本地 due 已设,lark-cli 不可用")
                elif due_iso and update_due_sync:
                    sync_r = update_due_sync(note["feishu_task_guid"], due_iso)
                    if sync_r.get("ok"):
                        result["feishu_synced"] += 1
                    else:
                        result["errors"].append(f"id={nid} feishu: {sync_r.get('error')}")
                elif due_iso is None and clear_due_sync:
                    sync_r = clear_due_sync(note["feishu_task_guid"])
                    if sync_r.get("ok"):
                        result["feishu_synced"] += 1
                    else:
                        result["errors"].append(f"id={nid} feishu clear: {sync_r.get('error')}")
            else:
                # 心愿无飞书 task_guid → 飞书侧没任务可改,但本地 due 仍生效
                # (可能本地心愿刚建还没补飞书 task,或 sync-from-feishu 未补建)
                result["errors"].append(f"id={nid}: 本地 due 已设,飞书 task 缺失(可跑 sync-from-feishu 补建)")

        conn.commit()
        output_json(
            result,
            message=f"排期完成: 本地更新={result['updated']}, 飞书同步={result['feishu_synced']}, 错误={len(result['errors'])}",
        )
    except Exception as e:
        conn.rollback()
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
    content = args.content
    if not content or not content.strip():
        error_json("请填入提醒内容")
    if note_id is not None and note_id <= 0:
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
    # 仅当提供了 note_id 时才校验笔记存在性
    if note_id is not None:
        note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            error_json(f"关联笔记不存在: id={note_id}")
    try:
        conn.execute(
            "INSERT INTO reminders (note_id, remind_at, repeat_type, repeat_rule, content, created_at) VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))",
            (note_id, remind_at, repeat_type, repeat_rule, content)
        )
        conn.commit()
        output_json({"note_id": note_id, "content": content}, message="提醒已设置")
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
                   r.notified_at, r.content, n.content as note_content
            FROM reminders r LEFT JOIN notes n ON r.note_id = n.id
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
            
            # 条件1：提前a分钟（范围匹配，cron 在 T-提前量 ~ T-1 任一时刻触发均生效）
            if notified_at is None and advance_minute <= now_minute < trigger_time_minute:
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
                    "content": content or row["note_content"] or "",
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
                r.content as reminder_content,
                orig_n.content as orig_note_content,
                orig_n.id as orig_note_id
            FROM notes n
            JOIN reminders r ON n.reminder_id = r.id
            LEFT JOIN notes orig_n ON r.note_id = orig_n.id
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
                        "reminder_content": d["reminder_content"] or d["orig_note_content"] or "",
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
                    "reminder_content": d["reminder_content"] or d["orig_note_content"] or "",
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
            SELECT r.*, r.content, n.content as note_content FROM reminders r
            LEFT JOIN notes n ON r.note_id = n.id
            WHERE r.status = ?
            ORDER BY r.remind_at, r.repeat_type
        """, (status_filter,))
        rows = []
        for row in cur.fetchall():
            d = dict(row)
            d["content"] = d.get("content") or d.get("note_content") or ""
            rows.append(d)
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
    p_add.add_argument("--category", "-c", help="顶层分类：备忘/心愿/打卡/情绪日记（默认 备忘）")
    p_add.add_argument("--sub-category", "-s", help="备忘内部分类：社交/工作/学习/灵感/记账/成就")
    p_add.add_argument("--media", "-m")
    p_add.add_argument("--tasklist-guid", help="飞书 tasklist GUID（仅 category=心愿 时生效；不传则飞书 task 进'我的任务'主页）")

    # search
    p_search = sub.add_parser("search")
    p_search.add_argument("keyword", nargs="?", default="")
    p_search.add_argument("--category", "-c", help="顶层分类过滤")
    p_search.add_argument("--sub-category", "-s", help="子分类过滤")
    p_search.add_argument("--limit", "-l", type=int)

    # update
    p_update = sub.add_parser("update")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--content")
    p_update.add_argument("--category", "-c")
    p_update.add_argument("--sub-category", "-s")
    p_update.add_argument("--media", "-m")
    p_update.add_argument("--reminder-id", type=int)

    # delete
    p_del = sub.add_parser("delete")
    p_del.add_argument("id", type=int, nargs="+", help="要删除的笔记 ID（可多个，空格分隔）")
    p_del.add_argument("--with-reminders", action="store_true",
                       help="级联删除关联的提醒（不加则有关联提醒会报错）")
    p_del.add_argument("-y", "--yes", action="store_true",
                       help="跳过二次确认（QQbot 自动化用）")

    # complete-wish
    p_complete = sub.add_parser(
        "complete-wish",
        help="完成心愿：原子删除心愿 + 新建打卡 note"
    )
    p_complete.add_argument("id", type=int, help="要完成的心愿 note ID")
    p_complete.add_argument("--content", help="打卡内容（默认拷贝心愿原文）")

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

    # update sub-category
    p_subcat = sub.add_parser("update-sub-category")
    p_subcat.add_argument("id", type=int)
    p_subcat.add_argument("sub_category")

    # set-due (心愿排期)
    p_setdue = sub.add_parser("set-due", help="心愿排期:批量设置心愿 due 日期,同步飞书 task due")
    p_setdue.add_argument("ids", nargs="+", type=int, help="心愿 note id 列表(可多个)")
    p_setdue.add_argument("--due", required=True, help="期望完成日期 (YYYY-MM-DD) 或 null 清除")

    # sync-from-feishu (反向同步)
    p_sync = sub.add_parser("sync-from-feishu", help="反向同步：飞书已完成 task → 本地 complete-wish")

    # reminder add
    p_remind = sub.add_parser("remind")
    p_remind.add_argument("note_id", nargs="?", type=int, default=None)
    p_remind.add_argument("--at")
    p_remind.add_argument("--content", default=None)
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
    elif args.command == "complete-wish":
        complete_wish(args)
    elif args.command == "get":
        get_note(args)
    elif args.command == "search-date":
        search_by_date(args)
    elif args.command == "update-category":
        update_category(args)
    elif args.command == "update-sub-category":
        update_sub_category(args)
    elif args.command == "set-due":
        set_due(args)
    elif args.command == "sync-from-feishu":
        # 双向对账：本地补建 + 飞书 done 反向 + 飞书 due 反向
        from feishu_sync import sync_from_feishu
        result = sync_from_feishu()
        msg = (
            f"双向同步完成: "
            f"补建={result.get('backfilled', 0)} | "
            f"done扫到={result.get('scanned_done', 0)}, 反向同步={result.get('synced', 0)}, "
            f"跳过(无本地note)={result.get('skipped_no_local_note', 0)} | "
            f"pending扫到={result.get('scanned_pending', 0)}, "
            f"due新增={result.get('due_added', 0)}, "
            f"due覆盖={result.get('due_overridden', 0)}, "
            f"due清除={result.get('due_removed', 0)} | "
            f"错误={len(result.get('errors', []))}"
        )
        output_json(result, message=msg)
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