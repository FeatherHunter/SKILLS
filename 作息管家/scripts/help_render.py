#!/usr/bin/env python3
"""
作息管家 · HELP 中心渲染器(§07 契约)

第一性:场景资产是唯一事实源(§07 §5)。本脚本读 scenarios.yaml →
按 wake_word 分组 → 注入 templates/help_center.html → 写单文件离线 HTML。

用法:
    python scripts/help_render.py [--out <path>]
    # 默认写到 $SKILLS_DB_PATH/schedule_html/help/作息管家_HELP_<TIMESTAMP>.html

输出路径(作息管家内部一致性 + 对标饼干记账命名):
    SKILLS_DB_PATH/schedule_html/help/作息管家_HELP_<YYYYMMDD>_<HHMMSS>.html
    命名格式: {Skill名}_HELP_<YYYYMMDD>_<HHMMSS>[_<N>].html(N = 同秒冲突保护)
    对标: 饼干记账_HELP_<YYYYMMDD>_<HHMMSS>.html(命名格式)
    路径: schedule_html/help/ 子目录,与 record/day, plan/list 等同级
    兼具作息管家内部一致性(schedule_html/ 约定) + 跨 Skill 命名一致性({Skill名}_HELP_)

约束(§07 §5):
- 展示全部业务唤醒词 + 全部合法场景
- 每场景独立复制按钮 + 复制反馈
- 剪贴板 API 不可用时降级(execCommand + 提示)
- 5 状态 fallback:正常 / 空 / 缺 / 错 / 离线
- 移动端 + 窄宽屏适配(模板自带响应式 CSS)

第一性来源:总纲 SKILL开发总纲V1.0/07-HELP与场景完备性.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path


# === 路径 ===
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE_PATH = SKILL_DIR / "templates" / "help_center.html"


def get_html_base_dir() -> Path:
    """作息管家 HTML 输出基目录(同 schedule_html_render.py::_html_base_dir)"""
    db_dir = os.environ.get("SKILLS_DB_PATH") or str(SKILL_DIR / ".db")
    return Path(db_dir) / "schedule_html"


def help_naming_path() -> Path:
    """HELP HTML 输出路径(作息管家 · schedule_html/help/ 子目录 · 对标饼干记账命名)

    命名:{Skill名}_HELP_<YYYYMMDD>_<HHMMSS>[_<N>].html
    对标饼干记账:`饼干记账_HELP_<YYYYMMDD>_<HHMMSS>.html`(scripts/render_help.py:133)

    路径:$SKILLS_DB_PATH/schedule_html/help/<command>_<TIMESTAMP>.html
    - 与作息管家 record/plan 域同级(schedule_html/record/day/, schedule_html/plan/list/)
    - 命名风格对标饼干记账({Skill名}_HELP_<TIMESTAMP>.html)
    - 同秒冲突保护 _2/_3/...

    为什么放 schedule_html/help/(作息管家内部一致性)而非 SKILLS_DB_PATH 根:
    - 作息管家既有约定:所有 HTML 输出在 schedule_html/<domain>/<mode>/
    - HELP 是作息管家内部一种 HTML 类型,应遵循该约定
    - 命名风格仍对标饼干记账({Skill名}_HELP_<TIMESTAMP>.html),与饼干记账 v2.4 一致
    """
    command = "作息管家_HELP"
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = get_html_base_dir() / "help"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{command}_{stamp}.html"
    if not target.exists():
        return target
    n = 2
    while n < 1000:
        candidate = base / f"{command}_{stamp}_{n}.html"
        if not candidate.exists():
            return candidate
        n += 1
    raise RuntimeError(f"冲突保护超过 1000 次:{command}_{stamp}")


def load_scenarios() -> tuple[list[dict], str | None]:
    """加载场景资产,返回 (scenarios, error_or_None)

    失败时不抛异常(可恢复原则),返回 error 字符串让模板走 fallback 渲染。
    """
    if not SCENARIOS_PATH.exists():
        return [], f"场景资产不存在: {SCENARIOS_PATH}"

    try:
        import yaml
    except ImportError:
        return [], "缺少 PyYAML 依赖(运行: pip install pyyaml)"

    try:
        with open(SCENARIOS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
    except yaml.YAMLError as e:
        return [], f"场景资产 YAML 解析失败: {type(e).__name__}: {e}"

    if not isinstance(data, list):
        return [], "场景资产根结构不是 list"

    # 校验 7 字段契约(§07 §2.2)
    required = {"wake_word", "scenario_id", "scenario_title", "dimensions", "prompt", "status", "result"}
    for i, sc in enumerate(data):
        missing = required - set(sc.keys())
        if missing:
            return [], f"第 {i+1} 条场景缺字段: {missing}"

    return data, None


def group_by_wake_word(scenarios: list[dict]) -> list[dict]:
    """按 wake_word 分组,生成 sections"""
    groups = OrderedDict()
    for sc in scenarios:
        wake = sc["wake_word"]
        if wake not in groups:
            groups[wake] = []
        groups[wake].append(sc)

    sections = []
    for wake, scs in groups.items():
        pending_count = sum(1 for s in scs if s.get("status") == "【待开发】")
        sections.append({
            "wake_word": wake,
            "scenarios": scs,
            "pending_count": pending_count,
        })
    return sections


def escape_for_js(s: str) -> str:
    """JSON 注入防 XSS — 关键防护(总纲 §04 原则 4 第 2 条)

    嵌入位置:window.__SCENARIOS__ = <JSON>;  (JS object literal 语法)

    JSON 与 JS object literal 在结构语法上兼容({"key": "value"}),
    所以结构 " 不应 escape(由 json.dumps 已正确处理字符串值内的 ")。

    只需 escape 防 </script> 提前闭合 + JS 转义歧义:
    - \\ → \\\\ (防 JS 二次转义)
    - < → \\u003c (防 </script>)
    - > → \\u003e (同上)
    - / → \\/ (总纲 §04 原则 4 习惯)

    历史 bug:旧版本把 " 也 escape,导致 {" 变 {\",JSON.parse 失败,
    浏览器端 sections 数组为空,用户看到"没有任何数据"。
    """
    if s is None:
        return ""
    return (
        str(s)
        .replace("\\", "\\\\")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("/", "\\/")
    )


def build_payload(scenarios: list[dict], sections: list[dict]) -> dict:
    """构造注入 payload"""
    return {
        "wakeword_count": len(sections),
        "scenario_count": len(scenarios),
        "pending_count": sum(1 for s in scenarios if s.get("status") == "【待开发】"),
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sections": [
            {
                "wake_word": sec["wake_word"],
                "pending_count": sec["pending_count"],
                "scenarios": [
                    {
                        "wake_word": s["wake_word"],
                        "scenario_id": s["scenario_id"],
                        "scenario_title": s["scenario_title"],
                        "dimensions": s.get("dimensions") or {},
                        "prompt": s.get("prompt") or "",
                        "status": s.get("status") or "",
                        "result": s.get("result") or "",
                    }
                    for s in sec["scenarios"]
                ],
            }
            for sec in sections
        ],
    }


def inject_data(template: str, payload: dict) -> str:
    """替换模板中的占位符(总纲 §04 原则 4)"""
    # 1. 占位符唯一性校验
    if template.count("<!--INJECT-DATA-->") != 1:
        raise ValueError(f"模板占位符 <!--INJECT-DATA--> 必须唯一(实际 {template.count('<!--INJECT-DATA-->')} 处)")
    if template.count("<!--INJECT-SECTIONS-->") != 1:
        raise ValueError(f"模板占位符 <!--INJECT-SECTIONS--> 必须唯一")

    # 2. JSON 序列化 + 防 XSS 转义
    json_str = json.dumps(payload, ensure_ascii=False)
    safe_json = escape_for_js(json_str)

    # 3. 替换占位符
    out = template.replace(
        "<!--INJECT-DATA-->",
        safe_json,
        1,
    )
    # INJECT-SECTIONS 留给浏览器端 JS 渲染(无需注入,占位符保留为空字符串)
    out = out.replace("<!--INJECT-SECTIONS-->", "", 1)
    return out


def render(out_path: Path) -> dict:
    """主渲染流程,返回 {status, data, message} 三段式"""
    # 1. 加载场景资产
    scenarios, error = load_scenarios()
    if error:
        # 失败仍生成 HTML(走 5 状态 fallback:错)
        payload = {
            "wakeword_count": 0,
            "scenario_count": 0,
            "pending_count": 0,
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": [],
            "error": error,
        }
        sections = []
    else:
        sections = group_by_wake_word(scenarios)
        payload = build_payload(scenarios, sections)

    # 2. 读模板
    if not TEMPLATE_PATH.exists():
        return {
            "status": "error",
            "data": None,
            "message": f"模板不存在: {TEMPLATE_PATH}",
        }
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 3. 注入
    try:
        rendered = inject_data(template, payload)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"注入失败: {type(e).__name__}: {e}",
        }

    # 4. 写文件
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    return {
        "status": "ok" if not error else "error",
        "data": {
            "file_path": str(out_path),
            "size_kb": size_kb,
            "wakeword_count": payload["wakeword_count"],
            "scenario_count": payload["scenario_count"],
            "pending_count": payload["pending_count"],
        },
        "message": (
            f"✓ HELP 中心已生成: {payload['wakeword_count']} 唤醒词 / "
            f"{payload['scenario_count']} 场景 / {payload['pending_count']} 待开发 ({size_kb} KB)"
            if not error else f"⚠ HELP 中心生成失败: {error}"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="作息管家 HELP 中心渲染器(§07 契约)")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "输出路径(默认: $SKILLS_DB_PATH/schedule_html/help/"
            "作息管家_HELP_<YYYYMMDD>_<HHMMSS>.html,"
            "作息管家内部一致性 + 对标饼干记账命名)"
        ),
    )
    args = parser.parse_args()

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = help_naming_path()

    result = render(out_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()