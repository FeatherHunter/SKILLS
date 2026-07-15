#!/usr/bin/env python3
"""复盘模块 - 集成层(⑤)

按 5 层架构定位:
- ⑤ 集成层:飞书发送 + 飞盘上传
- try/except + 失败降级(不阻塞主流程)
- 幂等键(防 cron 重跑产生重复消息)
- subprocess 列表传参(避免 PowerShell 中文乱码)
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


# ==================== 错误类 ====================

class FeishuError(Exception):
    """飞书集成错误基类"""
    pass


class ChatNotFoundError(FeishuError):
    """群名查不到"""
    pass


class SendError(FeishuError):
    """发送失败"""
    pass


# ==================== Targets 配置 ====================

def load_targets():
    """从环境变量读 REVIEW_FEISHU_TARGETS(JSON 字符串)

    Returns:
        list of dict, e.g.
            [{'type': 'im', 'open_id': 'ou_xxx'},
             {'type': 'group', 'group_name': '加油小分队'}]
    """
    raw = os.environ.get('REVIEW_FEISHU_TARGETS', '[]')
    try:
        targets = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FeishuError(f"REVIEW_FEISHU_TARGETS JSON 解析失败: {e}\n原始值: {raw[:100]}")

    if not isinstance(targets, list):
        raise FeishuError(f"REVIEW_FEISHU_TARGETS 必须是 JSON 数组,当前类型: {type(targets).__name__}")

    return targets


# ==================== 群名 → chat_id 实时查 ====================

def resolve_chat_id(group_name):
    """实时查群名 → chat_id(R1=A 不缓存)

    Args:
        group_name: 群名(如 '加油小分队')

    Returns:
        chat_id: oc_xxx

    Raises:
        ChatNotFoundError: 找不到
        FeishuError: lark-cli 失败
    """
    if not group_name:
        raise FeishuError("group_name 不能为空")

    # subprocess 列表传参(避免 shell 编码)
    result = subprocess.run(
        ['lark-cli', 'im', '+chat-search',
         '--query', group_name,
         '--format', 'json'],
        capture_output=True, text=True, encoding='utf-8',
        timeout=15,
    )

    if result.returncode != 0:
        raise FeishuError(
            f"lark-cli im +chat-search 失败 "
            f"(group_name={group_name}, returncode={result.returncode}): "
            f"{result.stderr[:200]}"
        )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise FeishuError(f"lark-cli 输出无法解析: {e}\nstdout={result.stdout[:200]}")

    if not output.get('ok'):
        raise FeishuError(f"lark-cli 返回 ok=false: {output}")

    # 找到匹配的群(名字去掉 emoji 后缀后精确匹配)
    items = output.get('data', {}).get('chats', [])
    for item in items:
        item_name = item.get('name', '')
        # 去 emoji 后缀(例:"加油小分队🧸" → "加油小分队")
        clean_name = item_name.split('🧸')[0].strip()
        if clean_name == group_name or item_name == group_name:
            chat_id = item.get('chat_id')
            if chat_id:
                return chat_id

    raise ChatNotFoundError(
        f"找不到群 '{group_name}',"
        f"已搜到 {len(items)} 个相关群: {[i.get('name') for i in items]}"
    )


# ==================== 发送实现 ====================

def send_im(open_id, text, idempotency_key):
    """发个人 IM 消息

    Args:
        open_id: ou_xxx
        text: 消息文本
        idempotency_key: 幂等键(防 lark-cli 重试产生重复)

    Raises:
        SendError: 发送失败
    """
    if not open_id:
        raise FeishuError("open_id 不能为空")

    content = json.dumps({'text': text}, ensure_ascii=False)

    result = subprocess.run(
        ['lark-cli', 'im', '+messages-send',
         '--as', 'user',
         '--user-id', open_id,
         '--msg-type', 'text',
         '--content', content,
         '--idempotency-key', idempotency_key,
         '--format', 'json'],
        capture_output=True, text=True, encoding='utf-8',
        timeout=15,
    )

    if result.returncode != 0:
        raise SendError(
            f"IM 发送失败 (open_id={open_id}, returncode={result.returncode}): "
            f"{result.stderr[:200]}"
        )


def send_group(chat_id, text, idempotency_key):
    """以 bot 名义发群消息

    Raises:
        SendError: 发送失败
    """
    if not chat_id:
        raise FeishuError("chat_id 不能为空")

    content = json.dumps({'text': text}, ensure_ascii=False)

    result = subprocess.run(
        ['lark-cli', 'im', '+messages-send',
         '--as', 'bot',
         '--chat-id', chat_id,
         '--msg-type', 'text',
         '--content', content,
         '--idempotency-key', idempotency_key,
         '--format', 'json'],
        capture_output=True, text=True, encoding='utf-8',
        timeout=15,
    )

    if result.returncode != 0:
        raise SendError(
            f"群消息发送失败 (chat_id={chat_id}, returncode={result.returncode}): "
            f"{result.stderr[:200]}"
        )


# ==================== 主入口(失败降级) ====================

def send_feishu(text, targets=None):
    """发飞书消息到多个 targets(失败降级)

    按 5 层规范:单个失败不影响其他,所有错误聚合返回

    Args:
        text: 消息文本
        targets: list,默认从 env 读

    Returns:
        dict: {
            'sent': N,
            'failed': M,
            'errors': [{'target': ..., 'error': str}, ...],
            'idempotency_key': str
        }
    """
    if targets is None:
        try:
            targets = load_targets()
        except FeishuError as e:
            return {'sent': 0, 'failed': 1, 'errors': [{'target': None, 'error': str(e)}], 'idempotency_key': None}

    if not targets:
        return {'sent': 0, 'failed': 0, 'errors': [], 'idempotency_key': None}

    idempotency_key = uuid4().hex
    results = {
        'sent': 0, 'failed': 0,
        'errors': [], 'idempotency_key': idempotency_key,
    }

    for target in targets:
        target_type = target.get('type')
        try:
            if target_type == 'im':
                send_im(target.get('open_id'), text, idempotency_key)
                results['sent'] += 1
            elif target_type == 'group':
                group_name = target.get('group_name')
                chat_id = resolve_chat_id(group_name)
                send_group(chat_id, text, idempotency_key)
                results['sent'] += 1
            else:
                raise FeishuError(f"未知 target type: {target_type}(应为 'im' 或 'group')")
        except FeishuError as e:
            # 失败降级:不抛,记录到 results
            print(f"Warning: 飞书发送失败 (target={target}): {e}", file=sys.stderr)
            results['failed'] += 1
            results['errors'].append({'target': target, 'error': str(e)})
        except Exception as e:
            # 兜底异常
            print(f"Error: 飞书发送未知异常 (target={target}): {e}", file=sys.stderr)
            results['failed'] += 1
            results['errors'].append({'target': target, 'error': f'未知异常: {e}'})

    return results


# ==================== 飞盘上传 ====================

def upload_to_feishu_drive(file_path):
    """上传 HTML 到飞书云盘

    按 5 层规范:
    - try/except 失败降级
    - 一条命令 Set-Location + lark-cli(避免跨调用 cwd 不持久)
    - 避免 Windows junction(用真实目录)

    Returns:
        飞书云盘 URL

    Raises:
        FeishuError: 上传失败
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FeishuError(f"文件不存在: {file_path}")

    dir_ = file_path.parent
    name = file_path.name

    # 一条命令搞定(避免 mavis bash 跨调用 cwd 不持久)
    ps_cmd = f'Set-Location "{dir_}"; lark-cli drive +upload --as user --file "./{name}" --name {name} --format json'

    try:
        result = subprocess.run(
            ps_cmd,
            shell=True,
            capture_output=True, text=True, encoding='utf-8',
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise FeishuError(f"飞盘上传超时 (30s): {file_path}")

    if result.returncode != 0:
        raise FeishuError(
            f"飞盘上传失败 (file={name}, returncode={result.returncode}): "
            f"{result.stderr[:200] or 'unknown error'}"
        )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise FeishuError(f"lark-cli 输出无法解析: {e}\nstdout={result.stdout[:200]}")

    if output.get('ok') is True:
        return output['data']['url']

    raise FeishuError(f"飞盘上传返回失败: {output}")