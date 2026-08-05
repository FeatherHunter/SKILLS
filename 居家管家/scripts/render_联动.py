# render_联动.py - SM9 域渲染助手(08-HTML 交互规范 v1 · 镜像 render_物品.py 模式)
# 职责: 统一 payload 信封(meta/复制数据/复制日志/顺路提醒)+ emit 输出
# 复制数据(硬标准): 结构化 JSON 5 段 {scene_id, command_cn, occurred_at, target, payload}
# 复制日志(硬标准): 6 段(场景标识/AI 思考链/数据结构/调用链/时间戳+版本/异常)
import json
from datetime import datetime

from render import render_page

SKILL_VERSION = "v2.0-SM9"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_envelope(data, scene_id, wake_word, command_cn, target=None,
                   copy_log=None, reminders=None):
    """组装标准 payload 信封(与 render_物品.build_envelope 同构)"""
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
        },
        "message": f"{command_cn}结果已生成",
    }


def emit_link(template, data, scene_id, wake_word, command_cn, target=None,
              copy_log=None, reminders=None, output_path=None, message=None):
    """渲染 SM9 模板并输出(模板位于 templates/联动/)"""
    envelope = build_envelope(data, scene_id, wake_word, command_cn,
                              target=target, copy_log=copy_log, reminders=reminders)
    result = render_page(f"联动/{template}", envelope, output_path,
                         message or envelope["message"])
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def emit_error(wake_word, command_cn, reason, key_data=None, suggest=None,
               output_path=None):
    """错误回执 HTML(08 §6.1 失败回执): 操作名/失败原因/关键数据/建议下一步
    render_page 只接受 status=ok 的信封;错误形态由 data.error 承载(正常流程形态)。"""
    occurred = now_str()
    envelope = {
        "status": "ok",
        "data": {
            "meta": {"scene_id": "", "wake_word": wake_word, "command_cn": command_cn,
                     "occurred_at": occurred, "skill_version": SKILL_VERSION},
            "error": {
                "action": command_cn,
                "reason": reason,
                "key_data": key_data or {},
                "suggest": suggest or "修正参数后重试",
            },
            "reminders": [],
            "copy_data": {"scene_id": "", "command_cn": command_cn, "occurred_at": occurred,
                          "target": key_data or {}, "payload": {}},
            "copy_log": {"scene": f"{command_cn} · 唤醒词「{wake_word}」",
                         "thinking": "", "data_structure": "", "call_chain": "",
                         "timestamp": f"{occurred} · {SKILL_VERSION}",
                         "exception": reason},
        },
        "message": f"{command_cn}失败:{reason}",
    }
    result = render_page("联动/error.html", envelope, output_path, f"{command_cn}失败")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "ok" else 2
