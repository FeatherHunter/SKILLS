#!/usr/bin/env python3
"""
Mavis (MiniMax Code) Source Adapter - 同步本机 Mavis daemon 用户对话到录音机

来源：C:\\Users\\<user>\\.mavis\\sqlite.db 的 session_messages 表
渠道标识：channel = "MiniMaxCode"
提取条件：role = 'user' AND msg_content 非空（系统注入可能没 msg_content）

复用 db.py 的 insert_message / checkpoint 接口：
- checkpoint key = "__Mavis_global__"，按 sm.id（自增主键，严格单调）增量
- (content, timestamp) 唯一索引兜底跨源去重
- message_id 部分唯一索引兜底（MiniMaxCode 用 sm.msg_id）

字段映射（与 user_messages 表对齐）：
  message_id     ← sm.msg_id                ("umsg_xxx" 全局唯一)
  session_file   ← "Mavis:session:" + sm.session_id   （虚拟路径）
  timestamp      ← sm.timestamp × 1000       （毫秒 → 微秒，统一 db schema）
  channel        ← "MiniMaxCode"             （固定）
  sender_id      ← data.origin.rawMeta.senderId（飞书用户 ID）
                    或 data.source（CLI/API/cron 触发）
  content        ← data.msg_content          （用户原文）
  date           ← YYYYMMDD（基于 timestamp，北京时间）
  has_attachment ← 0                          （MiniMaxCode schema 不存附件）

注意：
  - Mavis 是单库，全局一个 checkpoint 即可（不分 session）
  - sm.id 严格单调，比 timestamp 更稳（避免时钟回拨）
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from db import Database

# Mavis 主 db：默认 ~/.mavis/sqlite.db，可用 MAVIS_DB 覆盖
MAVIS_DB = Path(os.environ.get("MAVIS_DB", Path.home() / ".mavis" / "sqlite.db"))
CHANNEL = "MiniMaxCode"
CHECKPOINT_KEY = "__Mavis_global__"
SOURCE_TABLE = "session_messages"
ROLE_FILTER = "user"

# 真人飞书用户白名单（2026-07-01 对抗式审查后收紧）
# 起因：之前不过滤 sender_id，导致 api/system/permission-response 等系统消息也入库
# 现在只录用户本人——5 个 ou_xxx（用户承认都是自己的号）
USER_SENDER_IDS = (
    "ou_cd84288d35925aa490f67332327972dd",  # mavis
    "ou_c1799e09e24951a31ce6dbf38156ea2f",  # xiaoyan
    "ou_e593dc144927a5dd3b103f51ec2273db",  # coder
    "ou_37683ad7bedafb3c10e15fbdbec58fe7",  # xiaozhuo（当前 agent）
    "ou_41997d1d375bc9c45329398400c1a622",  # xiaojiang
)


def parse_ms_timestamp(ms: int) -> int:
    """毫秒 → 微秒（统一 db schema 的 timestamp 单位）"""
    return int(ms) * 1000


def timestamp_ms_to_date(ms: int) -> str:
    """毫秒 → YYYYMMDD（北京时间）"""
    dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    beijing = dt.astimezone(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y%m%d")


def extract_sender_id(data_obj: dict) -> str:
    """
    从 data JSON 提取 sender_id。
    优先级：飞书 senderId > source 字段 > ""
    """
    raw_meta = data_obj.get("origin", {}).get("rawMeta", {}) or {}
    sender = raw_meta.get("senderId") or raw_meta.get("accountName")
    if sender:
        return str(sender)
    return str(data_obj.get("source") or "")


def collect_user_messages(mavis_conn, last_id: int) -> list:
    """
    从 Mavis 拉取 role=user 且 id > last_id 的所有消息，按 id 升序。
    用 id 而非 timestamp 做游标，因为 id 严格单调（自增主键）。

    过滤（2026-07-01 对抗式审查后收紧）：
      1. role = 'user'
      2. msg_content 非空
      3. senderId 在 USER_SENDER_IDS 白名单内（5 个 ou_xxx 真人飞书号）
    排除：api / system / communication / permission-response / 老数据空 senderId 等
    """
    cur = mavis_conn.cursor()
    placeholders = ",".join("?" for _ in USER_SENDER_IDS)
    cur.execute(f"""
        SELECT id, session_id, msg_id, data, timestamp
        FROM {SOURCE_TABLE}
        WHERE role = ?
          AND id > ?
          AND json_extract(data, '$.msg_content') IS NOT NULL
          AND trim(json_extract(data, '$.msg_content')) != ''
          AND json_extract(data, '$.origin.rawMeta.senderId') IN ({placeholders})
        ORDER BY id ASC
    """, (ROLE_FILTER, last_id, *USER_SENDER_IDS))
    return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description="从 Mavis sqlite.db 同步用户对话到录音机")
    parser.add_argument("--full", action="store_true",
                        help="全量重扫：清空 Mavis checkpoint 后重新扫描全部 user 消息")
    parser.add_argument("--mavis-db", default=None,
                        help="Mavis db 路径（默认 ~/.mavis/sqlite.db 或 $MAVIS_DB）")
    parser.add_argument("--limit", type=int, default=0,
                        help="限制本次最多同步 N 条（0=不限，调试用）")
    args = parser.parse_args()

    mavis_db = Path(args.mavis_db) if args.mavis_db else MAVIS_DB
    if not mavis_db.is_file():
        print(f"[错误] Mavis db 不存在: {mavis_db}")
        print(f"[提示] 检查 ~/.mavis/sqlite.db 是否存在，或用 --mavis-db 指定")
        return

    db = Database()

    if args.full:
        # 只清 Mavis 来源的 checkpoint，不影响其他来源（OpenClaw）
        # checkpoint key 是 "__Mavis_global__"，跟 OpenClaw 的 session_file 路径不冲突
        # 复用 db.checkpoint_finalize 把 last_timestamp=0 写入即可
        db.checkpoint_finalize(CHECKPOINT_KEY, 0, "")
        print("[全量模式] Mavis checkpoint 已重置，从 id=0 开始扫描")
        last_id = 0
    else:
        cp = db.get_checkpoint(CHECKPOINT_KEY)
        last_id = int(cp["last_timestamp"]) if cp else 0
        print(f"[增量模式] Mavis checkpoint: id > {last_id}")

    mavis_conn = sqlite3.connect(str(mavis_db))

    try:
        rows = collect_user_messages(mavis_conn, last_id)
    except sqlite3.OperationalError as e:
        print(f"[错误] 读取 Mavis db 失败: {e}")
        print(f"[提示] 确认表 {SOURCE_TABLE} 存在，role 列名为 'user'")
        mavis_conn.close()
        return

    print(f"[Mavis] db: {mavis_db}")
    print(f"[Mavis] 待同步 user 消息: {len(rows)} 条")
    print()

    if not rows:
        mavis_conn.close()
        print("[完成] 没有新消息")
        return

    # 应用 limit
    if args.limit and len(rows) > args.limit:
        print(f"[调试] --limit 限制: 只处理前 {args.limit} 条")
        rows = rows[:args.limit]

    total_new = 0
    total_skip = 0
    latest_id = last_id
    latest_msg_id = ""

    db.begin_checkpoint_transaction()

    for row in rows:
        sm_id, session_id, msg_id, data_str, ts_ms = row

        try:
            data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            total_skip += 1
            continue

        content = data.get("msg_content", "").strip()
        if not content:
            total_skip += 1
            continue

        ts_us = parse_ms_timestamp(ts_ms)
        sender_id = extract_sender_id(data)

        db.insert_message({
            "message_id": msg_id,
            "session_file": f"Mavis:session:{session_id}",
            "timestamp": ts_us,
            "channel": CHANNEL,
            "sender_id": sender_id,
            "content": content,
            "date": timestamp_ms_to_date(ts_ms),
            "has_attachment": 0,
        })
        total_new += 1

        if sm_id > latest_id:
            latest_id = sm_id
            latest_msg_id = msg_id

    # 提交并更新 checkpoint（即使 total_new=0 也要 update，因为 id 推进了）
    db.checkpoint_finalize(CHECKPOINT_KEY, latest_id, latest_msg_id)
    db.end_checkpoint_transaction()

    mavis_conn.close()

    print(f"[Mavis] 同步完成: {total_new} 条新入库, {total_skip} 条跳过, checkpoint=id:{latest_id}")


if __name__ == "__main__":
    main()