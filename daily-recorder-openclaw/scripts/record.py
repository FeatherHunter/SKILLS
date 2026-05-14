#!/usr/bin/env python3
"""
Daily Recorder - 主扫描脚本
从 OpenClaw session 文件中提取用户发言和附件，增量入库

优化版 v2:
1. 优先扫描白纸文件（无 checkpoint 的文件优先处理）
2. 每处理一条消息实时更新 checkpoint，不怕中断
3. 批次从 10 增大到 50，全局 WAL 事务复用连接加速
4. 排除 .trajectory.jsonl（compaction 快照，历史归档，只需扫一次）
5. 有 checkpoint 的活跃文件优先于白纸文件（活跃文件的消息有时效性）
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from db import Database

SESSION_DIR = Path("/home/feather/.openclaw/agents/main/sessions/")
DB_PATH = Path("/mnt/d/2Study/StudyNotes/.db/daily_recorder.db")
ROLE_FILTER = "user"

# 系统前缀列表（过滤用）
SYSTEM_PREFIXES = [
    'A new session',
    'Read HEARTBEAT',
    'The user sent',
    'Write a dream diary entry',
    '[cron:',
    '[Queued messages while',
    '[Queued user message that',
    '[Bootstrap pending]',
    'Continue where you left off',
    'Continue the OpenClaw',
    '[OpenClaw heartbeat',
    '[Startup context',
    'System (untrusted)',
    'System:',
    'Use the "',
    'Use the \'',
    '[Subagent Context]',
    '<<<BEGIN_OPENCLAW',
    'Pre-compaction memory',
    'Sender (untrusted',
    'Conversation info',
    '[media reference removed - already processed by model]',
]

FILE_TYPE_MAP = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.wav': 'audio/wav',
    '.mp3': 'audio/mpeg',
    '.md': 'file/markdown',
    '.txt': 'file/text',
    '.pdf': 'file/pdf',
}


def parse_timestamp(ts_str: str) -> int | None:
    if not ts_str:
        return None
    try:
        ts_str = ts_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts_str)
        dt_utc = dt.astimezone(timezone.utc)
        return int(dt_utc.timestamp() * 1_000_000)
    except (ValueError, OSError):
        return None


def extract_metadata(text: str) -> dict:
    result = {'channel': 'pc', 'sender_id': None, 'message_id': None, 'timestamp': None}
    if text.startswith('Conversation info'):
        try:
            json_str = text.split('```json')[1].split('```')[0]
            meta = json.loads(json_str)
            chat_id = meta.get('chat_id', '')
            if 'qqbot' in chat_id:
                result['channel'] = 'qq'
            elif 'weixin' in chat_id or 'wechat' in chat_id:
                result['channel'] = 'wechat'
            result['sender_id'] = meta.get('sender_id') or meta.get('sender', '')
            result['message_id'] = meta.get('message_id', '')
            result['timestamp'] = meta.get('timestamp', '')
        except:
            pass
    elif text.startswith('Sender (untrusted'):
        try:
            json_str = text.split('```json')[1].split('```')[0]
            meta = json.loads(json_str)
            result['sender_id'] = meta.get('id', '') or meta.get('label', '')
        except:
            pass
    return result


def strip_timestamp_prefix(text: str) -> str:
    match = re.match(r'^\[\w{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} GMT\+8\] (.+)', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def extract_content_and_attachments(text: str, timestamp: int, session_file: Path) -> tuple:
    content = None
    has_attachment = 0
    attachments = []

    clean_text = strip_timestamp_prefix(text)
    lines = clean_text.split('\n')
    asr_content = None
    metadata_lines = set()

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('- ASR: '):
            asr_content = line_stripped[7:]
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('- Voice: '):
            file_path = line_stripped.split(',')[0].replace('- Voice: ', '').strip()
            attachments.append({
                'message_id': '', 'session_file': str(session_file), 'timestamp': timestamp,
                'channel': 'qq', 'sender_id': None, 'file_path': file_path,
                'file_type': infer_file_type(file_path),
            })
            has_attachment = 1
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('- Images: '):
            file_path = line_stripped.replace('- Images: ', '').strip()
            attachments.append({
                'message_id': '', 'session_file': str(session_file), 'timestamp': timestamp,
                'channel': 'qq', 'sender_id': None, 'file_path': file_path,
                'file_type': infer_file_type(file_path),
            })
            has_attachment = 1
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('[media reference removed - already processed by model]'):
            attachments.append({
                'message_id': '', 'session_file': str(session_file), 'timestamp': timestamp,
                'channel': 'qq', 'sender_id': None, 'file_path': '', 'file_type': 'image/gif',
            })
            has_attachment = 1
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('[Voice message] '):
            asr_content = line_stripped[len('[Voice message] '):]
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('[Attachment: '):
            match = re.match(r'\[Attachment: (.+?)\]', line_stripped)
            if match:
                attachments.append({
                    'message_id': '', 'session_file': str(session_file), 'timestamp': timestamp,
                    'channel': 'qq', 'sender_id': None, 'file_path': match.group(1).strip(),
                    'file_type': infer_file_type(match.group(1).strip()),
                })
                has_attachment = 1
            metadata_lines.add(i)
            continue

        if line_stripped.startswith('Conversation info') or line_stripped.startswith('Sender (untrusted'):
            metadata_lines.add(i)
            continue

    non_meta_lines = [l for j, l in enumerate(lines) if j not in metadata_lines and l.strip()]
    if non_meta_lines:
        content = clean_text.strip()
    elif asr_content:
        content = asr_content.strip()
    else:
        content = None

    return content, has_attachment, attachments


def is_system_message(text: str) -> bool:
    for p in SYSTEM_PREFIXES:
        if text.startswith(p):
            return True
    return False


def infer_file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return FILE_TYPE_MAP.get(ext, 'application/octet-stream')


def timestamp_to_date(ts: int) -> str:
    dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    beijing = dt.astimezone(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y%m%d")


def process_session(session_file: Path, db: Database, touch_fn=None) -> tuple:
    checkpoint = db.get_checkpoint(str(session_file))
    last_ts = checkpoint["last_timestamp"] if checkpoint else 0

    file_new = 0
    file_attachments = 0
    latest_ts = last_ts
    latest_msg_id = checkpoint["last_message_id"] if checkpoint else ""

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("type") != "message":
                continue

            msg = obj.get("message", {})
            if msg.get("role") != ROLE_FILTER:
                continue

            text = ''
            for c in msg.get("content", []):
                if isinstance(c, dict) and c.get("type") == "text":
                    text = c.get("text", "")
                    break

            if not text or not text.strip():
                continue

            stripped_text = strip_timestamp_prefix(text)
            if stripped_text.startswith('[cron:') or is_system_message(stripped_text):
                continue

            ts = parse_timestamp(obj.get("timestamp", ""))
            if ts is None:
                continue

            if last_ts > 0 and ts <= last_ts:
                continue

            content, has_attachment, attachments = extract_content_and_attachments(text, ts, session_file)
            msg_id = obj.get("id", "") or f"{session_file.name}:{ts}"
            meta = extract_metadata(text)

            if content:
                db.insert_message({
                    "message_id": msg_id, "session_file": str(session_file), "timestamp": ts,
                    "channel": meta.get("channel", "pc"), "sender_id": meta.get("sender_id", ""),
                    "content": content, "date": timestamp_to_date(ts), "has_attachment": has_attachment,
                })
                file_new += 1

            for att in attachments:
                att["message_id"] = msg_id
                att["sender_id"] = meta.get("sender_id", "")
                att["channel"] = meta.get("channel", "pc")
                att["date"] = timestamp_to_date(ts)
                db.insert_attachment(att)
                file_attachments += 1

            latest_ts = ts
            latest_msg_id = msg_id

            # 【优化2】每条消息处理完立即实时更新 checkpoint，不怕中断
            if touch_fn:
                touch_fn(str(session_file), latest_ts, latest_msg_id)

    # 扫完后统一更新 checkpoint（无论有没有新消息）
    db.upsert_checkpoint(str(session_file), latest_ts, latest_msg_id)

    return file_new, file_attachments, latest_ts, latest_msg_id


def main():
    db = Database(DB_PATH)

    # 【优化1+4】排除 trajectory，只扫活跃的 .jsonl 文件
    all_files = sorted(SESSION_DIR.glob("*.jsonl"))
    all_files = [f for f in all_files
                 if ".deleted." not in f.name and ".trajectory." not in f.name]

    files_no_cp = []       # 白纸：从未处理过
    files_has_cp = []      # 有 checkpoint 的活跃文件
    checkpoint_files = []  # checkpoint.*.jsonl 文件（不需要实时扫）

    for f in all_files:
        sf_name = f.name
        # checkpoint.*.jsonl 或 uuid.checkpoint.uuid.jsonl 都是 checkpoint 文件
        is_cp_file = sf_name.startswith("checkpoint.") or ".checkpoint." in sf_name
        if is_cp_file:
            checkpoint_files.append(f)
        elif db.get_checkpoint(str(f)):
            files_has_cp.append(f)
        else:
            files_no_cp.append(f)

    # 扫描顺序：
    # 1. 有 checkpoint 的活跃文件（有时效性，优先）
    # 2. 白纸文件（新创建的，尚未有任何数据）
    # 3. checkpoint 文件（历史元数据，低优先级）
    session_files = (
        sorted(files_has_cp, key=lambda f: f.stat().st_mtime) +
        files_no_cp +
        sorted(checkpoint_files, key=lambda f: f.stat().st_mtime)
    )

    print(f"[优化版 v2] 有CP活跃: {len(files_has_cp)} | 白纸: {len(files_no_cp)} | checkpoint文件: {len(checkpoint_files)}")
    print(f"[优化版 v2] 总扫描文件: {len(session_files)}（不含 .trajectory）")

    total_new = 0
    total_attachments = 0
    scanned = 0

    # 【优化3】不限批次，一次扫完所有文件（已有 checkpoint 增量，不怕重复扫）
    total_files = len(session_files)
    print(f"[优化版 v2] 有CP活跃: {len(files_has_cp)} | 白纸: {len(files_no_cp)} | checkpoint文件: {len(checkpoint_files)}")
    print(f"[优化版 v2] 总扫描文件: {total_files}（不含 .trajectory）")
    print(f"[优化版 v2] 预计时间: ~{(total_files * 20 / 1000 / 60):.1f} 分钟（快速模式）")
    print()

    total_new = 0
    total_attachments = 0
    scanned = 0

    # 开启全局 WAL 事务，复用连接加速
    db.begin_checkpoint_transaction()

    for idx, session_file in enumerate(session_files, 1):
        file_new, file_attachments, latest_ts, latest_msg_id = process_session(
            session_file, db, touch_fn=db.touch_checkpoint
        )
        if file_new > 0 or file_attachments > 0:
            scanned += 1
        total_new += file_new
        total_attachments += file_attachments

        # 每 100 个文件提交一次，打印进度
        if idx % 100 == 0:
            db._conn.commit()
            print(f"  进度: {idx}/{total_files} 个文件, {total_new} 条消息, {total_attachments} 条附件")

    db._conn.commit()
    print(f"  最终: {scanned}/{total_files} 个文件, {total_new} 条消息, {total_attachments} 条附件")

    db.end_checkpoint_transaction()

    print(f"\n扫描完成")
    print(f"扫描文件: {scanned}/{total_files} 个")
    print(f"新增消息: {total_new} 条")
    print(f"新增附件: {total_attachments} 条")


if __name__ == "__main__":
    main()