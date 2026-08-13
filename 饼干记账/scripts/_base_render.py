# -*- coding: utf-8 -*-
"""饼干记账 · Base 管线共享层（#300 task ① · 2026-08-13）

6 个 HTML 渲染脚本共用的「接 Base 管线」三件事，避免 6 份同源副本：
  1. 统一信封：data.meta 必填字段 + data.scene.snapshot + data.copy_log
     （契约 = 公共组件/docs/component-contract.md §4，领域数据组织进 snapshot）
  2. Base 注入：调 公共组件/injector.py inject()（硬拦截：3 占位符缺失/重复 → 报错）
  3. BOM 写入：utf-8-sig（ADR-0002 + tests/test_render.py TestBomBytes 契约）

Base 资产路径：技能在 <repo>/饼干记账/ → Base = 技能目录.parent / "公共组件"
（真实仓库路径优先；环境变量 SKILLS_BASE_DIR 仅 fallback，测试隔离用）。
公共组件资产只读，任何缺口走公共层 ISSUE，禁止技能内 fork（#294 Q 决议）。
"""

import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent

SKILL_NAME = "饼干记账"
SKILL_VERSION = "2.0"

CHARTS_HELPERS = "<!--CHARTS-HELPERS-->"


def base_skill_dir() -> Path:
    """公共组件/ 目录（真实仓库路径优先，SKILLS_BASE_DIR 仅 fallback）"""
    d = SKILL_DIR.parent / "公共组件"
    if not (d / "assets" / "base.js").exists():
        d = Path(os.environ.get("SKILLS_BASE_DIR") or d)
    return d


def inject_base(template_text: str, payload: dict) -> str:
    """Base 注入器：payload + base.js + base.css + charts.js（硬拦截，占位符缺失/重复报错）

    CHARTS-HELPERS 为 0 或 1：模板含占位符 → 注入 charts.js（#302 task ③ 图表契约）；
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
            "请确认 公共组件/ 目录存在（#300 依赖 Base 管线）"
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
    """utf-8-sig BOM 写入（TestBomBytes 契约 + Windows GBK 误判防御）"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8-sig")
    return out


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def envelope(data: dict, command_cn: str, wake_word: str, scene_id: str,
             render_cmd: str, summary: list, sections: list,
             buttons: list = None, thinking: str = None,
             data_structure: str = "biscuit_accountant.db（只读查询）",
             exception: str = "无") -> dict:
    """给 payload.data 补齐 Base 信封（component-contract §4 必填 + snapshot + copy_log）

    契约必填：data.meta.command_cn / data.meta.occurred_at / data.scene(对象)。
    snapshot 结构校验（违规 Base 报错）：title 非空 + summary 数组 + sections 数组。
    技能把领域数据组织成 summary/sections 传入，Base 只渲染（领域无关）。
    """
    meta = data.setdefault("meta", {})
    meta.setdefault("command_cn", command_cn)
    meta.setdefault("occurred_at", now_str())
    meta.setdefault("skill_name", SKILL_NAME)
    meta.setdefault("skill_version", SKILL_VERSION)
    meta.setdefault("wake_word", wake_word)
    meta.setdefault("scene_id", scene_id)
    if render_cmd:
        meta.setdefault("render_cmd", render_cmd)
    data["scene"] = {
        "scene_id": scene_id,
        "snapshot": {"title": command_cn, "summary": list(summary), "sections": list(sections)},
        "buttons": list(buttons or []),
    }
    data["copy_log"] = {
        "thinking": thinking or f"意图理解: 唤醒词「{wake_word}」→ 渲染 {command_cn}",
        "data_structure": data_structure,
        "call_chain": render_cmd or "（本地渲染）",
        "timestamp": meta["occurred_at"],
        "exception": exception,
    }
    return data


def error_envelope(message: str, command_cn: str = "查询失败") -> dict:
    """错误 payload 的信封（status=error）：模板错误卡 + 复制按钮仍可用

    保持 data 不为 None（Base buildDataText/buildLogText 依赖 data.scene.snapshot），
    但不含领域字段，模板按 status!=ok 走错误卡分支不受影响。
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
                "data_structure": "biscuit_accountant.db（未读取）",
                "call_chain": "（渲染失败）",
                "timestamp": now_str(),
                "exception": message or "未知错误",
            },
        },
        "message": message or "未知错误",
    }


def bill_rows(records: list, limit: int = 20) -> list:
    """账单记录 → 人类可读明细行（time category amount note）"""
    if not records:
        return []
    rows = []
    for r in records[:limit]:
        amt = r.get("amount")
        amt_s = f"{float(amt):.2f}" if isinstance(amt, (int, float)) else str(amt or "")
        rows.append(
            f"{str(r.get('time') or '')[:16]} {r.get('category') or ''} "
            f"{amt_s} {r.get('note') or ''}".strip()
        )
    if len(records) > limit:
        rows.append(f"...共 {len(records)} 笔（仅列前 {limit}）")
    return rows


def bill_summary(data: dict) -> list:
    """账单类 payload → 关键指标行（按字段存在性选取）"""
    summary = []
    if data.get("subtitle"):
        summary.append(str(data["subtitle"]))
    for k, lab in (
        ("count", "笔数"), ("expense", "支出"), ("income", "收入"), ("net", "净额"),
        ("total", "总额"), ("total_records", "总笔数"), ("total_days", "记账天数"),
        ("month", "月份"), ("year", "年份"),
    ):
        v = data.get(k)
        if v is not None and v != "":
            summary.append(f"{lab} {v}")
    return summary
