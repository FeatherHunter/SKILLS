#!/usr/bin/env python3
"""
Daily Recorder - 主扫描脚本
从 OpenClaw session 文件中提取用户发言和附件，增量入库
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
    '[media attached:'
]

# 文件类型推断
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
    """解析 ISO 时间戳为微秒时间戳"""
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
    """从元数据块提取 channel, sender_id, message_id"""
    result = {'channel': 'pc', 'sender_id': None, 'message_id': None, 'timestamp': None}

    # Conversation info
    if text.startswith('Conversation info'):
        try:
            json_str = text.split('```json')[1].split('```')[0]
            meta = json.loads(json_str)
            chat_id = meta.get('chat_id', '')
            if 'qqbot' in chat_id:
                result['channel'] = 'qq'
            elif 'weixin' in chat_id or 'wechat' in chat_id:
                result['channel'] = 'wechat'

            # sender_id 优先取 sender_id，其次取 sender
            result['sender_id'] = meta.get('sender_id') or meta.get('sender', '')
            result['message_id'] = meta.get('message_id', '')
            result['timestamp'] = meta.get('timestamp', '')
        except:
            pass

    # Sender metadata
    elif text.startswith('Sender (untrusted'):
        try:
            json_str = text.split('```json')[1].split('```')[0]
            meta = json.loads(json_str)
            result['sender_id'] = meta.get('id', '') or meta.get('label', '')
        except:
            pass

    return result


def strip_timestamp_prefix(text: str) -> str:
    """去掉 [Day GMT+8] 时间戳前缀，返回实际内容"""
    # 格式: [Sat 2026-05-09 08:33 GMT+8] 实际内容
    import re
    match = re.match(r'^\[\w{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} GMT\+8\] (.+)', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def extract_content_and_attachments(text: str, timestamp: int, session_file: Path) -> tuple:
    """
    从消息文本提取内容和附件
    返回 (content, has_attachment, attachments)
    """
    content = None
    has_attachment = 0
    attachments = []

    # 先去掉 [Day GMT+8] 时间戳前缀
    clean_text = strip_timestamp_prefix(text)

    # 分割消息行
    lines = clean_text.split('\n')

    # 检查是否有 - ASR: 或 [Voice message]
    asr_content = None
    user_text_lines = []  # 收集所有可能是用户文字的行
    metadata_lines = set()  # 已知元数据行

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            metadata_lines.add(i)
            continue

        # - ASR: 格式
        if line_stripped.startswith('- ASR: '):
            asr_content = line_stripped[7:]
            metadata_lines.add(i)
            continue

        # - Voice: 格式 → 附件
        if line_stripped.startswith('- Voice: '):
            file_path = line_stripped.split(',')[0].replace('- Voice: ', '').strip()
            att = {
                'message_id': '',
                'session_file': str(session_file),
                'timestamp': timestamp,
                'channel': 'qq',
                'sender_id': None,
                'file_path': file_path,
                'file_type': infer_file_type(file_path),
            }
            attachments.append(att)
            has_attachment = 1
            metadata_lines.add(i)
            continue

        # - Images: 格式 → 附件
        if line_stripped.startswith('- Images: '):
            file_path = line_stripped.replace('- Images: ', '').strip()
            att = {
                'message_id': '',
                'session_file': str(session_file),
                'timestamp': timestamp,
                'channel': 'qq',
                'sender_id': None,
                'file_path': file_path,
                'file_type': infer_file_type(file_path),
            }
            attachments.append(att)
            has_attachment = 1
            metadata_lines.add(i)
            continue

        # [media attached: ...] 格式 → 附件
        if line_stripped.startswith('[media attached: '):
            match = re.match(r'\[media attached: (.+?) \(', line_stripped)
            if match:
                file_path = match.group(1).strip()
                att = {
                    'message_id': '',
                    'session_file': str(session_file),
                    'timestamp': timestamp,
                    'channel': 'qq',
                    'sender_id': None,
                    'file_path': file_path,
                    'file_type': infer_file_type(file_path),
                }
                attachments.append(att)
                has_attachment = 1
            metadata_lines.add(i)
            continue

        # [Voice message] 格式
        if line_stripped.startswith('[Voice message] '):
            asr_content = line_stripped[len('[Voice message] '):]
            metadata_lines.add(i)
            continue

        # [Attachment: /path/...] 格式 → 附件
        if line_stripped.startswith('[Attachment: '):
            match = re.match(r'\[Attachment: (.+?)\]', line_stripped)
            if match:
                file_path = match.group(1).strip()
                att = {
                    'message_id': '',
                    'session_file': str(session_file),
                    'timestamp': timestamp,
                    'channel': 'qq',
                    'sender_id': None,
                    'file_path': file_path,
                    'file_type': infer_file_type(file_path),
                }
                attachments.append(att)
                has_attachment = 1
            metadata_lines.add(i)
            continue

        # Conversation info / Sender 元数据块 → 跳过
        if line_stripped.startswith('Conversation info') or line_stripped.startswith('Sender (untrusted'):
            metadata_lines.add(i)
            continue

        # 可能是用户文字的行：收集但暂不确定
        user_text_lines.append(line_stripped)

    # 文字内容判断优先级：用户实际文字 > ASR > None
    # 如果有用户文字（排除纯元数据后的内容），优先使用
    if user_text_lines:
        # 用原始 clean_text 保留格式，用 metadata_lines 判断是否有真实内容
        # 去掉所有元数据/附件行后，看是否还有内容
        non_meta_lines = [l for j, l in enumerate(lines) if j not in metadata_lines and l.strip()]
        if non_meta_lines:
            content = clean_text.strip()
        else:
            # 所有非元数据行都是空的，只有 ASR 有内容
            content = asr_content.strip() if asr_content else None
    elif asr_content:
        content = asr_content.strip()
    else:
        content = None

    return content, has_attachment, attachments


def is_system_message(text: str) -> bool:
    """判断是否是系统消息"""
    for p in SYSTEM_PREFIXES:
        if text.startswith(p):
            return True
    return False


def infer_file_type(file_path: str) -> str:
    """根据文件扩展名推断 MIME 类型"""
    ext = Path(file_path).suffix.lower()
    return FILE_TYPE_MAP.get(ext, 'application/octet-stream')


def timestamp_to_date(ts: int) -> str:
    """微秒时间戳 -> YYYYMMDD"""
    dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    beijing = dt.astimezone(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y%m%d")


def parse_msg_timestamp(text: str) -> str | None:
    """从消息内容中提取 GMT+8 时间戳"""
    # 格式: [Sat 2026-05-09 16:23 GMT+8]
    match = re.search(r'\[(\w{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} GMT\+8)\]', text)
    if match:
        return match.group(1)
    return None


def process_message(obj: dict, session_file: Path, meta: dict) -> dict | None:
    """处理单条消息，返回用户消息或 None"""
    msg = obj.get("message", {})
    if msg.get("role") != ROLE_FILTER:
        return None

    text = ''
    for c in msg.get("content", []):
        if isinstance(c, dict) and c.get("type") == "text":
            text = c.get("text", "")
            break

    if not text or not text.strip():
        return None

    # 先剥时间戳前缀再判断是否系统消息
    stripped = strip_timestamp_prefix(text)
    # [cron:UUID Name] 格式是 cron 任务通知，不是用户内容
    if stripped.startswith('[cron:') or is_system_message(stripped):
        return None

    # 提取元数据
    meta_info = extract_metadata(text)

    # 提取内容和附件
    ts = parse_timestamp(obj.get("timestamp", ""))
    if ts is None:
        return None

    content, has_attachment, attachments = extract_content_and_attachments(
        text, ts, session_file
    )

    # 如果没有内容但有附件，也需要记录附件
    if content is None and attachments:
        # 只有附件，没有文字内容，单独处理附件
        for att in attachments:
            att['message_id'] = obj.get('id', '')
        return None  # 不创建用户消息

    if content is None:
        return None

    return {
        "message_id": obj.get("id", "") or f"{session_file.name}:{ts}",
        "session_file": str(session_file),
        "timestamp": ts,
        "channel": meta_info.get("channel", "pc"),
        "sender_id": meta_info.get("sender_id", ""),
        "content": content,
        "date": timestamp_to_date(ts),
        "has_attachment": has_attachment,
        "attachments": attachments,
    }


def process_session(session_file: Path, db: Database) -> tuple:
    """处理单个 session 文件，返回 (新增消息数, 新增附件数, 最新时间戳, 最新消息ID)"""
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

            # 先去掉时间戳前缀，再判断是否系统消息
            stripped_text = strip_timestamp_prefix(text)
            # [cron:UUID Name] 格式是 cron 任务通知，不是用户内容
            if stripped_text.startswith('[cron:') or is_system_message(stripped_text):
                continue

            ts = parse_timestamp(obj.get("timestamp", ""))
            if ts is None:
                continue

            if last_ts > 0 and ts <= last_ts:
                continue

            # 提取内容和附件
            content, has_attachment, attachments = extract_content_and_attachments(
                text, ts, session_file
            )

            msg_id = obj.get("id", "") or f"{session_file.name}:{ts}"

            # 元数据
            meta = extract_metadata(text)

            # 入库消息
            if content:
                msg_dict = {
                    "message_id": msg_id,
                    "session_file": str(session_file),
                    "timestamp": ts,
                    "channel": meta.get("channel", "pc"),
                    "sender_id": meta.get("sender_id", ""),
                    "content": content,
                    "date": timestamp_to_date(ts),
                    "has_attachment": has_attachment,
                }
                db.insert_message(msg_dict)
                file_new += 1

            # 入库附件
            for att in attachments:
                att["message_id"] = msg_id
                att["sender_id"] = meta.get("sender_id", "")
                att["channel"] = meta.get("channel", "pc")
                att["date"] = timestamp_to_date(ts)
                db.insert_attachment(att)
                file_attachments += 1

            latest_ts = ts
            latest_msg_id = msg_id

    # 更新 checkpoint
    if latest_ts > last_ts:
        db.upsert_checkpoint(str(session_file), latest_ts, latest_msg_id)

    return file_new, file_attachments, latest_ts, latest_msg_id


def main():
    db = Database(DB_PATH)

    # 扫描所有 session 文件
    session_files = sorted(SESSION_DIR.glob("*.jsonl"))
    session_files = [f for f in session_files if ".deleted." not in f.name]

    total_new = 0
    total_attachments = 0
    scanned = 0

    BATCH_SIZE = 10

    for i in range(0, len(session_files), BATCH_SIZE):
        batch = session_files[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(session_files) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"[批次 {batch_num}/{total_batches}] 扫描 {len(batch)} 个文件...")

        for session_file in batch:
            file_new, file_attachments, latest_ts, latest_msg_id = process_session(session_file, db)

            if file_new > 0 or file_attachments > 0:
                scanned += 1

            total_new += file_new
            total_attachments += file_attachments

        print(f"  累计: {scanned}/{len(session_files)} 个文件, {total_new} 条消息, {total_attachments} 条附件")

    print(f"\n扫描完成")
    print(f"扫描文件: {scanned}/{len(session_files)} 个")
    print(f"新增消息: {total_new} 条")
    print(f"新增附件: {total_attachments} 条")
    print(f"新增附件: {total_attachments} 条")


if __name__ == "__main__":
    main()