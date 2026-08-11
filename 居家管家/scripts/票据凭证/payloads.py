"""SM6 票据凭证域 · 场景 payload 构建(供 templates/票据凭证/*.html 注入)

08 规范契约:
  - 复制数据 5 段: scene_id / command_cn / occurred_at / target / payload
  - 复制日志 6 段: 场景标识 / AI 思考链 / 数据结构 / CLI 调用链 / 时间戳+版本 / 异常
  - 敏感字段: 证件号只给脱敏值, 密码永不出现(敏感复制分离 = 结构保证)

#250(2026-08-11)单一事实源改造:
  scene_id / wake_word / title 从 references/scenarios.yaml 读取(场景清单 = 唯一事实源),
  由 CLI 调用方传入具体场景 id(如 SM6-2 查上月购买), 渲染 meta 用该场景的信息。
  静态 SCENE_META 已删除(与清单双源维护 = 漂移隐患;scene_meta 清单缺失时返回默认)。
"""
from datetime import datetime
from pathlib import Path

from 票据凭证 import ops

SKILL_DIR = Path(__file__).parent.parent.parent
SCENARIOS_YAML = SKILL_DIR / "references" / "scenarios.yaml"


def _load_scenes():
    """从场景清单读取 receipt 域场景(唯一事实源 · 懒加载)"""
    try:
        import yaml
    except ImportError:
        return {}
    if not SCENARIOS_YAML.exists():
        return {}
    data = yaml.safe_load(SCENARIOS_YAML.read_text(encoding="utf-8"))
    out = {}
    for s in (data.get("scenarios") or []):
        if s.get("domain") == "receipt":
            out[s.get("id")] = s
    return out


def scene_meta(scene_id):
    """从场景清单取 receipt 场景的 meta(单一事实源 · #250)

    scene_id: 场景资产 id(如 "SM6-2" 查上月购买)
    返回 meta dict: scene_id / command_cn / wake_word / title / subtitle / scenario_title
    """
    scenes = _load_scenes()
    s = scenes.get(scene_id)
    if not s:
        return {"scene_id": scene_id, "command_cn": scene_id, "wake_word": scene_id,
                "title": scene_id, "subtitle": ""}
    return {
        "scene_id": scene_id,
        "command_cn": s.get("wake_word", scene_id),
        "wake_word": s.get("wake_word", ""),
        "title": s.get("scenario_title", s.get("wake_word", "")),
        "subtitle": s.get("result", ""),
        "scenario_title": s.get("scenario_title", ""),
    }

VERSION = "2.0-SM6"

# 模板 → 12.A command_cn 命名前缀(域内自建, 不动公共 TEMPLATE_TO_COMMAND_CN)
TEMPLATE_CN = {
    "票据凭证/purchase_records.html": "购买记录",
    "票据凭证/warranty.html": "保修",
    "票据凭证/certificates.html": "证件",
    "票据凭证/accounts.html": "账号",
}


def _occurred_at():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _photo_base64(path_str, max_bytes=300_000):
    """票据/证件照片 → base64(≤300KB, 超限或缺失返回 '')"""
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    try:
        data = p.read_bytes()
        if len(data) > max_bytes:
            return ""
        import base64
        return base64.b64encode(data).decode()
    except OSError:
        return ""


def _cli_chain(cmd, args_dict):
    """调用链(复制日志 ④ 段): 域 CLI 完整命令"""
    parts = ["python", "scripts/票据凭证/cli.py", cmd]
    for k, v in args_dict.items():
        if v is None or v == "":
            continue
        parts.append(f"--{k}")
        parts.append(str(v))
    return " ".join(parts)


# ── 购买记录 ────────────────────────────────────────────────────────

def purchase_payload(conn, item_id=None, year=None, month=None, scene="SM6-1"):
    rows = ops.purchase_list(conn, item_id=item_id, year=year, month=month)
    stats = ops.purchase_stats(conn, year=year)
    now_return = sum(1 for r in rows if r.get("return_days_left") is not None
                     and r["return_days_left"] >= 0)
    for r in rows:
        r["photo_base64"] = _photo_base64(r.get("receipt_photo", ""))
    return {
        "status": "ok",
        "data": {
            "meta": scene_meta(scene),
            "occurred_at": _occurred_at(),
            "version": VERSION,
            "cli_chain": _cli_chain("purchase list", {"item-id": item_id, "year": year, "month": month}),
            "summary": {
                "title": f"购买记录{' · ' + str(year) if year else ''}",
                "subtitle": "按时间浏览 · 消费统计 · 票据归档",
                "metrics": [
                    {"label": "记录数", "value": f"{stats['count']} 条"},
                    {"label": "累计花费", "value": f"¥{stats['total_price']:.2f}"},
                    {"label": "可退货", "value": f"{now_return} 件"},
                    {"label": "分类", "value": f"{len(stats['by_category'])} 类"},
                ],
            },
            "items": rows,
            "category_stats": stats["by_category"],
            "filter": {"year": year, "month": month},
            "empty_hint": "没有购买记录。录入物品时填写购买日期/价格, 或在「购买记录」登记。",
        },
        "message": "购买记录已生成",
    }


# ── 保修与保养 ──────────────────────────────────────────────────────

def warranty_payload(conn, status_filter=None, scene="SM6-6"):
    items = ops.warranty_list(conn, status_filter=status_filter)
    n_in = sum(1 for i in items if i["status"] == "在保")
    n_warn = sum(1 for i in items if i["status"] == "即将到期")
    n_over = sum(1 for i in items if i["status"] in ("已过", "到期未做"))
    reminders = ops.reminders_cert(conn)
    for i in items:
        i["photo_base64"] = _photo_base64(i.get("photo", ""))
    return {
        "status": "ok",
        "data": {
            "meta": scene_meta(scene),
            "occurred_at": _occurred_at(),
            "version": VERSION,
            "cli_chain": _cli_chain("warranty list", {"status": status_filter}),
            "summary": {
                "title": "保修与保养",
                "subtitle": "权益状态 · 维修记录 · 保养周期",
                "metrics": [
                    {"label": "在保", "value": f"{n_in} 项", "severity": "info"},
                    {"label": "即将到期", "value": f"{n_warn} 项", "severity": "warn"},
                    {"label": "已过/待保养", "value": f"{n_over} 项", "severity": "danger"},
                ],
            },
            "items": items,
            "reminders": reminders,
            "empty_hint": "没有保修/保养登记。登记后这里会显示权益状态与到期提醒。",
        },
        "message": "保修与保养已生成",
    }


# ── 证件 ────────────────────────────────────────────────────────────

def certificates_payload(conn, scene="SM6-11"):
    items = ops.cert_list(conn)
    n_warn = sum(1 for i in items if i["cert_status"] == "即将到期")
    n_over = sum(1 for i in items if i["cert_status"] == "已过期")
    for i in items:
        i["photo_base64"] = _photo_base64(i.get("photo", ""))
    reminders = ops.reminders_warranty(conn)
    return {
        "status": "ok",
        "data": {
            "meta": scene_meta(scene),
            "occurred_at": _occurred_at(),
            "version": VERSION,
            "cli_chain": _cli_chain("cert list", {}),
            "summary": {
                "title": "证件管理",
                "subtitle": "按到期排序 · 号码脱敏 · 复制数据不含证件号",
                "metrics": [
                    {"label": "证件数", "value": f"{len(items)} 本"},
                    {"label": "即将到期", "value": f"{n_warn} 本", "severity": "warn"},
                    {"label": "已过期", "value": f"{n_over} 本", "severity": "danger"},
                ],
            },
            "items": items,
            "reminders": reminders,
            "empty_hint": "没有证件登记。护照/身份证/驾照/签证/保险单到期前 30 天会在这里提醒。",
        },
        "message": "证件清单已生成",
    }


# ── 账号密码 ────────────────────────────────────────────────────────

def accounts_payload(conn=None, scene="SM6-15"):
    rows = ops_account_list_masked_safe()
    by_type = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r)
    grouped = [{"type": t, "accounts": by_type[t]} for t in
               ("购物", "银行", "社交", "其他") if t in by_type]
    return {
        "status": "ok",
        "data": {
            "meta": scene_meta(scene),
            "occurred_at": _occurred_at(),
            "version": VERSION,
            "cli_chain": _cli_chain("account list", {}),
            "summary": {
                "title": "账号密码",
                "subtitle": "密码加密存储 · 清单全脱敏 · 复制数据默认不含密码",
                "metrics": [
                    {"label": "账号数", "value": f"{len(rows)} 个"},
                    {"label": "类型", "value": f"{len(by_type)} 类"},
                    {"label": "主密钥", "value": "已设置" if _master_set() else "未设置",
                     "severity": "info" if _master_set() else "warn"},
                ],
            },
            "groups": grouped,
            "empty_hint": "没有账号。用「存账号」登记, 密码经主密钥加密存储。",
            "master_set": _master_set(),
        },
        "message": "账号清单已生成",
    }


def ops_account_list_masked_safe():
    from 票据凭证.account_ops import account_list_masked
    return account_list_masked()


def _master_set():
    from 票据凭证.account_ops import is_master_key_set
    return is_master_key_set()
