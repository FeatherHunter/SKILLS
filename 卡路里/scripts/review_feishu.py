#!/usr/bin/env python3
"""复盘模块 - 飞书发送(group 群 / im 个人)

设计:
- D2 决策:webhook 群 + IM 个人 都支持
- Q14 决策:纯文本消息
- 配置来源:环境变量(避免硬编码,不破坏 config-calorie.ts)

环境变量:
- REVIEW_FEISHU_CHANNEL    = 'group' / 'im'(默认 group)
- REVIEW_FEISHU_WEBHOOK_URL = webhook 群消息 URL
- REVIEW_FEISHU_USER_OPEN_ID = IM 用户的 open_id
"""

import os
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path


def get_channel() -> str:
    """读环境变量,获取飞书通道"""
    return os.environ.get('REVIEW_FEISHU_CHANNEL', 'group').lower()


def send_feishu(text: str, channel: str | None = None) -> bool:
    """发送飞书消息

    Args:
        text: 消息文本(纯文本,已含 emoji + 换行)
        channel: 'group' / 'im',默认读环境变量

    Returns:
        True 成功, False 失败
    """
    channel = (channel or get_channel()).lower()
    if channel == 'group':
        return send_via_webhook(text)
    elif channel == 'im':
        return send_via_lark_im(text)
    else:
        raise ValueError(f"未知飞书通道: {channel}(应为 'group' 或 'im')")


def send_via_webhook(text: str) -> bool:
    """通过 webhook 群消息发送(用 mavis feishu-webhook-skill)

    直接调 feishu-webhook-skill 的底层实现(POST 到 webhook URL)
    """
    webhook_url = os.environ.get('REVIEW_FEISHU_WEBHOOK_URL')
    if not webhook_url:
        raise ValueError(
            "REVIEW_FEISHU_WEBHOOK_URL 环境变量未设置,"
            "webhook 群消息无法发送"
        )

    payload = {
        'msg_type': 'text',
        'content': {'text': text},
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('StatusCode') == 0 or result.get('code') == 0
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Error: webhook 发送失败: {e}")
        return False


def send_via_lark_im(text: str) -> bool:
    """通过 lark-cli 发 IM 个人消息"""
    user_open_id = os.environ.get('REVIEW_FEISHU_USER_OPEN_ID')
    if not user_open_id:
        raise ValueError(
            "REVIEW_FEISHU_USER_OPEN_ID 环境变量未设置,"
            "IM 个人消息无法发送"
        )

    # 用 lark-cli 发消息(mavis 提供的)
    # 注意:lark-cli 在 Windows + junction 路径下会失败,需用真实目录
    try:
        result = subprocess.run(
            [
                'lark-cli', 'im', '+messages-send',
                '--as', 'user',
                '--receive_id', user_open_id,
                '--msg_type', 'text',
                '--content', json.dumps({'text': text}, ensure_ascii=False),
                '--format', 'pretty',
            ],
            capture_output=True, text=True, encoding='utf-8',
            timeout=15,
        )
        if result.returncode != 0:
            print(f"Error: lark-cli 失败: {result.stderr}")
            return False
        output = json.loads(result.stdout)
        return output.get('ok') is True
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: lark-cli 调用失败: {e}")
        return False


# ==================== 飞盘上传 ====================

def upload_to_feishu_drive(file_path: str | Path) -> str:
    """上传 HTML 到飞书云盘,返回飞书链接

    用 mavis HTML 飞盘 技能(底层 lark-cli drive +upload)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    dir_ = file_path.parent
    name = file_path.name

    # 一条命令搞定(避免 mavis bash 跨调用 cwd 不持久)
    # 注意:Windows junction 路径会让 Go EvalSymlinks 失败,需用真实目录
    try:
        result = subprocess.run(
            f'Set-Location "{dir_}"; lark-cli drive +upload --as user --file "./{name}" --name {name} --format pretty',
            shell=True,
            capture_output=True, text=True, encoding='utf-8',
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"上传失败: {result.stderr}")

        output = json.loads(result.stdout)
        if output.get('ok') is True:
            return output['data']['url']
        raise RuntimeError(f"上传失败: {output}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        raise RuntimeError(f"lark-cli drive +upload 失败: {e}")