#!/usr/bin/env python3
"""
每日语录记录脚本 - OpenClaw 版
从所有 session 文件中提取用户发言，按时间全局排序，追加到语录文件

用法：
  python3 record_yulu.py [日期YYYYMMDD]
  不带参数默认今天
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ========== 配置 ==========
SESSION_DIR = Path("/home/feather/.openclaw/agents/main/sessions/")
YULU_BASE_DIR = Path("/mnt/d/2Study/StudyNotes/{year}/个人/{date}")
MAX_CONTENT_LEN = 200

# 过滤掉的消息前缀/关键词（命中任意一条则跳过）
SKIP_PATTERNS = [
    "[SYSTEM",
    "[System note",
    "[The user sent",
    "[cron:",
    "[OpenClaw heartbeat",
    "Sender (untrusted metadata)",
    "openclaw-control-ui",
    # 图片/文件类消息（通常是 AI 发的或者系统元数据）
]

# 过滤掉 role 不是 user 的消息
ROLE_FILTER = "user"


def is_valid_message(text: str) -> bool:
    """判断消息是否应该被记录"""
    if not text or not text.strip():
        return False
    for pattern in SKIP_PATTERNS:
        if pattern in text:
            return False
    return True


def extract_user_messages(session_dir: Path, start_dt: datetime, end_dt: datetime):
    """扫描所有 session 文件，提取指定时间范围内的用户消息，全局排序"""
    beijing_tz = timezone(timedelta(hours=8))
    all_messages = []

    for session_file in session_dir.glob("*.jsonl"):
        if ".deleted." in session_file.name:
            continue

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # 只处理 message 类型
                    if obj.get('type') != 'message':
                        continue

                    msg = obj.get('message', {})
                    if msg.get('role') != ROLE_FILTER:
                        continue

                    # 提取文本内容
                    text = ""
                    for c in msg.get('content', []):
                        if isinstance(c, dict) and c.get('type') == 'text':
                            text = c.get('text', "")
                            break

                    # 过滤
                    if not is_valid_message(text):
                        continue

                    # 解析时间戳（UTC -> 北京时间）
                    try:
                        iso_ts = obj.get('timestamp', '').replace('Z', '+00:00')
                        msg_dt = datetime.fromisoformat(iso_ts).astimezone(beijing_tz)
                    except (ValueError, OSError):
                        continue

                    # 时间范围过滤
                    if not (start_dt <= msg_dt <= end_dt):
                        continue

                    # 内容截断
                    first_line = text.strip().split("\n")[0]
                    if len(first_line) > MAX_CONTENT_LEN:
                        first_line = first_line[:MAX_CONTENT_LEN] + "..."

                    all_messages.append((msg_dt, first_line))

        except (OSError, IOError):
            continue

    # 全局按时间排序
    all_messages.sort(key=lambda x: x[0])
    return all_messages


def get_or_create_yulu_file(yulu_path: Path, date_str: str) -> tuple:
    """
    获取或创建语录文件
    返回 (file_path, existing_last_content)
    existing_last_content: 文件中最后一条有效消息内容（用于去重），若无返回 None
    """
    yulu_path.parent.mkdir(parents=True, exist_ok=True)

    if yulu_path.exists():
        # 读取最后一行有效消息内容（用于追加时的去重）
        with open(yulu_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 跳过 header，找到最后一条有效消息
        last_content = None
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith('# ') or line.startswith('---') or line.startswith('采集时间') or line.startswith('总消息数') or line.startswith('**'):
                continue
            if ' - ' in line:
                last_content = line.split(' - ', 1)[1].strip()
                break

        return yulu_path, last_content
    else:
        # 创建新文件
        header = f"# {date_str} 语录\n\n采集时间：{date_str} 00:00:00 ~ 现在\n总消息数：计算中...\n\n---\n\n"
        with open(yulu_path, 'w', encoding='utf-8') as f:
            f.write(header)
        return yulu_path, None


def append_to_yulu(yulu_path: Path, messages: list, existing_last_content: str):
    """
    追加消息到语录文件
    - existing_last_content: 如果有，追加时跳过重复内容
    """
    if not messages:
        print("没有新消息需要追加")
        return 0

    # 去重：如果最后一条已存在，跳过重复
    start_idx = 0
    if existing_last_content:
        for i, (dt, text) in enumerate(messages):
            if text.strip() == existing_last_content.strip():
                start_idx = i + 1
                break

    if start_idx >= len(messages):
        print("没有新消息需要追加（已全部存在）")
        return 0

    messages_to_write = messages[start_idx:]

    # 追加写入
    with open(yulu_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 确保末尾有换行符
    if content and not content.endswith('\n'):
        content += '\n'

    # 追加消息
    entries = []
    for dt, text in messages_to_write:
        entries.append(f"{dt.strftime('%Y-%m-%d %H:%M:%S')} - {text}")

    content += '\n'.join(entries) + '\n'

    with open(yulu_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return len(entries)


def update_header(yulu_path: Path, date_str: str, total_count: int, start_dt: datetime, end_dt: datetime):
    """更新语录文件头部统计"""
    with open(yulu_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到总消息数那行并更新
    for i, line in enumerate(lines):
        if line.startswith('总消息数：'):
            lines[i] = f"总消息数：{total_count} 条\n"
            break
        if line.startswith('采集时间：'):
            lines[i] = f"采集时间：{date_str} 00:00:00 ~ {end_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            break

    with open(yulu_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def main():
    beijing_tz = timezone(timedelta(hours=8))

    # 解析日期参数
    if len(sys.argv) > 1:
        date_str = sys.argv[1]  # YYYYMMDD
        year = date_str[:4]
        month = int(date_str[4:6])
        day = int(date_str[6:8])
    else:
        now = datetime.now(tz=beijing_tz)
        date_str = now.strftime('%Y%m%d')
        year = now.strftime('%Y')
        month = now.month
        day = now.day

    # 时间范围：当天 00:00:00 ~ 23:59:59 北京时间
    start_dt = datetime(int(year), month, day, 0, 0, 0, tzinfo=beijing_tz)
    end_dt = datetime(int(year), month, day, 23, 59, 59, tzinfo=beijing_tz)

    print(f"记录日期: {date_str}")
    print(f"时间范围: {start_dt} ~ {end_dt}")

    # 获取语录文件
    yulu_base = Path(f"/mnt/d/2Study/StudyNotes/{year}/个人/{date_str}")
    yulu_base.mkdir(parents=True, exist_ok=True)
    yulu_path = yulu_base / f"{date_str}_语录.md"

    yulu_path, existing_last_content = get_or_create_yulu_file(yulu_path, date_str)

    # 提取消息
    print("扫描 session 文件...")
    messages = extract_user_messages(SESSION_DIR, start_dt, end_dt)
    print(f"找到 {len(messages)} 条用户消息")

    # 追加
    added = append_to_yulu(yulu_path, messages, existing_last_content)
    print(f"追加了 {added} 条消息")

    # 更新统计
    total = len(messages)
    update_header(yulu_path, date_str, total, start_dt, datetime.now(tz=beijing_tz))
    print(f"完成！语录文件: {yulu_path}")


if __name__ == "__main__":
    main()
