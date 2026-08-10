# render_开始使用.py - SM8 域渲染助手(08-HTML 交互规范 v1)
# 职责: 统一 payload 信封(meta/复制数据/复制日志/顺路提醒)+ emit 输出
# 复制数据(硬标准): 结构化 JSON 5 段 {scene_id, command_cn, occurred_at, target, payload}
# 复制日志(硬标准): 6 段(场景标识/AI 思考链/数据结构/调用链/时间戳+版本/异常)
import json
from datetime import datetime

from render import render_page

SKILL_VERSION = "v2.0-SM8"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def humanize(obj, depth=0):
    """把 dict/list 转成人类可读文本(非 JSON): 每项一行, 嵌套缩进

    08 规范 2026-08-10 修订: 复制数据禁默认 JSON, 改人类可读结构化文本。
    dict → `键: 值`; 嵌套 dict/list 递归缩进; list 每元素一行。
    """
    pad = "  " * depth
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None or v == "":
                continue
            if isinstance(v, dict):
                if v:
                    lines.append(f"{pad}{k}:")
                    lines.append(humanize(v, depth + 1))
            elif isinstance(v, list):
                if v:
                    lines.append(f"{pad}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(humanize(item, depth + 1))
                        else:
                            lines.append(f"{pad}  · {item}")
            else:
                lines.append(f"{pad}{k}: {v}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                lines.append(humanize(item, depth))
            else:
                lines.append(f"{pad}· {item}")
    else:
        lines.append(f"{pad}{obj}")
    return "\n".join(lines)


def build_human_copy(copy_data, copy_log, reminders):
    """生成人类可读的复制数据 / 复制日志文本(08 规范修订 · 禁默认 JSON)

    复制数据: 【场景名 · 数据快照】标题 + 场景/时间/对象 + payload 逐行
    复制日志: 6 段逐行(①-⑥)
    """
    command_cn = copy_data.get("command_cn", "")
    data_lines = [f"【{command_cn} · 数据快照】"]
    if copy_data.get("scene_id"):
        data_lines.append(f"场景: {copy_data['scene_id']}")
    if copy_data.get("occurred_at"):
        data_lines.append(f"时间: {copy_data['occurred_at']}")
    if copy_data.get("target"):
        data_lines.append(f"对象: {copy_data['target']}")
    payload = copy_data.get("payload") or {}
    body = humanize(payload)
    if body:
        data_lines.append("")
        data_lines.append(body)
    if reminders:
        data_lines.append("")
        data_lines.append("顺路提醒:")
        for r in reminders:
            data_lines.append(f"  · {r.get('text', '')}")

    log_lines = [
        f"① 场景: {copy_log.get('scene', '')}",
        f"② 思考链: {copy_log.get('thinking', '')}",
        f"③ 数据结构: {copy_log.get('data_structure', '')}",
        f"④ 调用链: {copy_log.get('call_chain', '')}",
        f"⑤ 时间戳: {copy_log.get('timestamp', '')}",
        f"⑥ 异常: {copy_log.get('exception', '') or '无'}",
    ]
    return "\n".join(data_lines), "\n".join(log_lines)


def build_envelope(data, scene_id, wake_word, command_cn, target=None,
                   copy_log=None, reminders=None):
    """组装标准 payload 信封(与 render_物品.build_envelope 同构)

    data: 场景数据(dict)
    target: 复制数据段 target(操作对象)
    copy_log: 6 段日志(其中 ③ 数据结构/④ 调用链 由场景传入)
    reminders: 顺路提醒区列表 [{type, text}](可空)
    """
    occurred = now_str()
    copy_data = {
        "scene_id": scene_id,
        "command_cn": command_cn,
        "occurred_at": occurred,
        "target": target or "",
        "payload": data,
    }
    log = copy_log or {}
    copy_log_full = {
        "scene": f"{command_cn} · 唤醒词「{wake_word}」 · 场景「{scene_id}」",
        "thinking": log.get("thinking", "意图理解 → 决策点 → 关键判断(摘要级)"),
        "data_structure": log.get("data_structure", "payload JSON(输入/输出)+ DB 操作类型"),
        "call_chain": log.get("call_chain", "渲染脚本 / CLI 命令(完整,可复制执行)"),
        "timestamp": f"{occurred} · {SKILL_VERSION}",
        "exception": log.get("exception", ""),
    }
    copy_data_human, copy_log_human = build_human_copy(
        copy_data, copy_log_full, reminders or [])
    return {
        "status": "ok",
        "data": {
            "meta": {
                "scene_id": scene_id,
                "wake_word": wake_word,
                "command_cn": command_cn,
                "occurred_at": occurred,
                "skill_version": SKILL_VERSION,
            },
            "scene": data,
            "reminders": reminders or [],
            "copy_data": copy_data,
            "copy_log": copy_log_full,
            "copy_data_human": copy_data_human,
            "copy_log_human": copy_log_human,
        },
        "message": f"{command_cn}结果已生成",
    }


def emit_sm8(template, data, scene_id, wake_word, command_cn, target=None,
             copy_log=None, reminders=None, output_path=None, message=None):
    """渲染 SM8 模板并输出(模板位于 templates/开始使用/)"""
    envelope = build_envelope(data, scene_id, wake_word, command_cn,
                              target=target, copy_log=copy_log, reminders=reminders)
    result = render_page(f"开始使用/{template}", envelope, output_path,
                         message or envelope["message"])
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def emit_error(wake_word, command_cn, reason, key_data=None, suggest=None,
               output_path=None, exception=None):
    """错误回执 HTML(08 §6.1 失败回执): 操作名/失败原因/关键数据/建议下一步
    render_page 只接受 status=ok 的信封;错误形态由 data.error 承载(正常流程形态)。
    """
    occurred = now_str()
    copy_data = {"scene_id": "", "command_cn": command_cn, "occurred_at": occurred,
                 "target": key_data or {}, "payload": {}}
    copy_log_full = {"scene": f"{command_cn} · 唤醒词「{wake_word}」",
                     "thinking": "", "data_structure": "", "call_chain": "",
                     "timestamp": f"{occurred} · {SKILL_VERSION}",
                     "exception": exception or reason}
    copy_data_human, copy_log_human = build_human_copy(copy_data, copy_log_full, [])
    envelope = {
        "status": "ok",
        "data": {
            "meta": {"scene_id": "", "wake_word": wake_word, "command_cn": command_cn,
                     "occurred_at": occurred, "skill_version": SKILL_VERSION},
            "error": {
                "action": command_cn,
                "wake_word": wake_word,
                "reason": reason,
                "key_data": key_data or {},
                "suggest": suggest or "修正参数后重试",
            },
            "reminders": [],
            "copy_data": copy_data,
            "copy_log": copy_log_full,
            "copy_data_human": copy_data_human,
            "copy_log_human": copy_log_human,
        },
        "message": f"{command_cn}失败:{reason}",
    }
    result = render_page("开始使用/error_receipt.html", envelope, output_path, f"{command_cn}失败")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "ok" else 2
