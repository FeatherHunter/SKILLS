# -*- coding: utf-8 -*-
"""卡路里 · Base 管线共享层（#314 task ① · 2026-08-13）

66 个 HTML 渲染脚本共用的「接 Base 管线」四件事，避免同源副本：
  1. 统一信封：data.meta 必填字段 + data.scene.snapshot + data.copy_log
     （契约 = 公共组件/docs/component-contract.md §4，领域数据组织进 snapshot）
  2. Base 注入：调 公共组件/injector.py inject()（硬拦截：3 占位符缺失/重复 → 报错）
  3. BOM 写入：utf-8-sig（对齐饼干 #300 契约 + Windows GBK 误判防御）
  4. auto_snapshot：从领域数据自动提炼 snapshot（summary/sections），
     脚本可显式传 summary/sections 覆盖以获得更高质量的复制数据。

Base 资产路径：技能在 <repo>/卡路里/ → Base = 技能目录.parent / "公共组件"
（真实仓库路径优先；环境变量 SKILLS_BASE_DIR 仅 fallback，测试隔离用）。
公共组件资产只读，任何缺口走公共层 ISSUE，禁止技能内 fork（#291 Q 决议）。
"""

import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent

SKILL_NAME = "卡路里"
SKILL_VERSION = "2.4.19"

CHARTS_HELPERS = "<!--CHARTS-HELPERS-->"


def base_skill_dir() -> Path:
    """公共组件/ 目录（真实仓库路径优先，SKILLS_BASE_DIR 仅 fallback）"""
    d = SKILL_DIR.parent / "公共组件"
    if not (d / "assets" / "base.js").exists():
        d = Path(os.environ.get("SKILLS_BASE_DIR") or d)
    return d


def inject_base(template_text: str, payload: dict) -> str:
    """Base 注入器：payload + base.js + base.css + charts.js（硬拦截，占位符缺失/重复报错）

    CHARTS-HELPERS 为 0 或 1：模板含占位符 → 注入 charts.js（#317 task ③ 图表契约）；
    不含 → 不注入。charts.js 是公共组件唯一真相源，缺口走公共层 ISSUE，禁止技能内 fork。

    返回注入后的 HTML 字符串（不含 BOM；BOM 由 write_html 统一写）。
    """
    bd = base_skill_dir()
    if str(bd) not in sys.path:
        sys.path.insert(0, str(bd))
    try:
        from injector import inject
        base_js = (bd / "assets" / "base.js").read_text(encoding="utf-8").strip()
        base_css = (bd / "assets" / "base.css").read_text(encoding="utf-8").strip()
    except ImportError:
        raise RuntimeError(
            "Base Skill 资产缺失: 找不到 公共组件/injector.py。"
            "请确认 公共组件/ 目录存在（#314 依赖 Base 管线）"
        )
    charts_asset = None
    if CHARTS_HELPERS in template_text:
        charts_path = bd / "assets" / "charts.js"
        if not charts_path.exists():
            raise RuntimeError(
                f"Base Skill 图表资产缺失: {charts_path}。"
                "模板声明了 CHARTS-HELPERS 但公共组件缺 charts.js（缺口走公共层 ISSUE）"
            )
        charts_asset = charts_path.read_text(encoding="utf-8").strip()
    html, err = inject(template_text, payload, js_asset=base_js, css_asset=base_css,
                       charts_asset=charts_asset, strict=False)
    if err:
        raise RuntimeError(f"Base 注入失败: {err}")
    return html


def write_html(html: str, out: Path) -> Path:
    """utf-8-sig BOM 写入（#314 用户拍板引入 BOM · 对齐饼干 #300 契约）"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8-sig")
    return out


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_SECTION_LIST_KEYS = (
    "history", "meals", "records", "items", "entries", "logs", "photos",
    "movements", "days", "series", "list", "rows", "data_rows",
)

_MAX_SUMMARY = 8
_MAX_ROWS = 30
_MAX_ROW_LEN = 120


def _fmt(v):
    if isinstance(v, float):
        r = round(v, 2)
        return str(int(r)) if r.is_integer() else str(r)
    return str(v)


def _auto_summary(data: dict, message: str = None) -> list:
    lines = []
    summary = data.get("summary")
    if isinstance(summary, dict):
        for k, v in summary.items():
            if isinstance(v, (dict, list)):
                continue
            lines.append(f"{k} {_fmt(v)}")
    for k in ("subtitle", "one_line", "date", "period", "title"):
        v = data.get(k)
        if v is not None and v != "":
            lines.append(_fmt(v))
    if not lines and message:
        lines.append(message)
    return lines[:_MAX_SUMMARY]


def _auto_sections(data: dict) -> list:
    sections = []
    for key in _SECTION_LIST_KEYS:
        v = data.get(key)
        if isinstance(v, list) and v:
            rows = []
            for it in v[:_MAX_ROWS]:
                if isinstance(it, dict):
                    row = " | ".join(
                        f"{k}: {_fmt(val)}" for k, val in it.items()
                        if not isinstance(val, (dict, list))
                    )
                else:
                    row = _fmt(it)
                rows.append(row[:_MAX_ROW_LEN])
            sections.append({"heading": key, "rows": rows})
    summary = data.get("summary")
    if isinstance(summary, dict):
        rows = [f"{k}: {_fmt(v)}" for k, v in summary.items()]
        if rows:
            sections.insert(0, {"heading": "summary", "rows": rows})
    return sections


def envelope(data: dict, command_cn: str, wake_word: str = "",
             render_cmd: str = None, summary: list = None,
             sections: list = None, scene_id: str = "",
             data_structure: str = "calorie_data.db",
             thinking: str = None) -> dict:
    """给 payload.data 补齐 Base 信封（component-contract §4 必填 + snapshot + copy_log）

    契约必填：data.meta.command_cn / data.meta.occurred_at / data.scene(对象)。
    snapshot 结构校验（违规 Base 报错）：title 非空 + summary 数组 + sections 数组。
    技能把领域数据组织成 summary/sections 传入，Base 只渲染（领域无关）；
    不传时用 auto_snapshot 从领域数据自动提炼。
    """
    meta = data.setdefault("meta", {})
    meta.setdefault("command_cn", command_cn)
    meta.setdefault("occurred_at", now_str())
    meta.setdefault("skill_name", SKILL_NAME)
    meta.setdefault("skill_version", SKILL_VERSION)
    meta.setdefault("wake_word", wake_word or command_cn)
    meta.setdefault("scene_id", scene_id or command_cn)
    if render_cmd:
        meta.setdefault("render_cmd", render_cmd)
    if summary is None:
        summary = _auto_summary(data)
    if sections is None:
        sections = _auto_sections(data)
    data["scene"] = {
        "scene_id": scene_id or command_cn,
        "snapshot": {"title": command_cn, "summary": list(summary), "sections": list(sections)},
        "buttons": [],
    }
    chain = meta.get("chain")
    data["copy_log"] = {
        "thinking": (chain or thinking
                     or f"意图理解: 唤醒词「{wake_word or command_cn}」→ 渲染 {command_cn}"),
        "data_structure": data_structure,
        "call_chain": render_cmd or "（本地渲染）",
        "timestamp": meta["occurred_at"],
        "exception": "无",
    }
    return data


def render_template(template_path, data, command_cn=None, wake_word="",
                    render_cmd=None):
    """读模板 + envelope 包装 + Base 注入（替代各脚本自研 window.__DATA__ 注入）

    兼容两种入参：
      - 裸领域数据 dict（如 build_data() 返回的 data）→ 包 {status:'ok', data:...}
      - 已包装三段式 {status, data, message} → 只给 data 补信封
    command_cn 缺省时从 data.meta 的 command_cn/wake_word/scene_name 推断。
    """
    template = template_path.read_text(encoding="utf-8")
    if isinstance(data, dict) and data.get("status") is not None \
            and isinstance(data.get("data"), dict):
        payload = data
        inner = data["data"]
        meta = inner.setdefault("meta", {})
        if command_cn is None:
            command_cn = (meta.get("command_cn") or meta.get("wake_word")
                          or meta.get("scene_name") or "操作回执")
        envelope(inner, command_cn, wake_word=wake_word or "",
                 render_cmd=render_cmd)
    else:
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        if command_cn is None:
            command_cn = (meta.get("command_cn") or meta.get("wake_word")
                          or meta.get("scene_name") or "操作回执")
        payload = {"status": "ok",
                   "data": envelope(data, command_cn, wake_word=wake_word or "",
                                    render_cmd=render_cmd)}
    return inject_base(template, payload)


def error_envelope(message: str, command_cn: str = "操作失败") -> dict:
    """错误 payload 的信封（status=error）：模板错误卡 + 复制按钮仍可用

    保持 data 不为 None（Base buildDataText/buildLogText 依赖 data.scene.snapshot）。
    """
    return {
        "status": "error",
        "data": {
            "meta": {
                "command_cn": command_cn,
                "occurred_at": now_str(),
                "skill_name": SKILL_NAME,
                "skill_version": SKILL_VERSION,
                "wake_word": "",
                "scene_id": "error",
            },
            "scene": {
                "scene_id": "error",
                "snapshot": {
                    "title": command_cn,
                    "summary": [message or "未知错误"],
                    "sections": [],
                },
                "buttons": [],
            },
            "copy_log": {
                "thinking": "命令执行失败，无有效数据",
                "data_structure": "calorie_data.db（未读取）",
                "call_chain": "（渲染失败）",
                "timestamp": now_str(),
                "exception": message or "未知错误",
            },
        },
        "message": message or "未知错误",
    }
