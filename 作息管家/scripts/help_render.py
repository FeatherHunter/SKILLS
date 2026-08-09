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
    from schedule_db import get_db_base_dir
    return get_db_base_dir() / "schedule_html"


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


# === group_by_wake_word 已弃用 · 改用 group_by_category(下方)===
# group_by_wake_word 保留仅用于向后兼容占位,新代码请用 group_by_category。
def group_by_wake_word(scenarios: list[dict]) -> list[dict]:
    """[已弃用] 按 wake_word 分组,生成 sections。
    新代码请用 group_by_category(categories/wake_words/scenarios 三层结构)。
    """
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


# === 模块分类映射(作息管家 · 5 大模块 · 对标饼干记账 5 类)===
# 每个唤醒词归类到一个模块(category)。硬编码而不修改 scenarios.yaml(不破坏 §07 契约)。
CATEGORY_MAP = [
    {
        "key": "write",
        "name": "写入与同步",
        "icon": "📝",
        "desc": "记录作息 / 同步消息 / 增量同步",
        "wake_words": ["#0 记作息", "#1 准备消息", "#2 同步作息", "#3 增量同步"],
    },
    {
        "key": "query",
        "name": "查询与浏览",
        "icon": "🔍",
        "desc": "查作息 / 查日程 / 查状态 / 时间轴 / 范围",
        "wake_words": [
            "#4 今天总结", "#5 汇总作息", "#6 查作息", "#7 查作息详情",
            "#8 查作息时间轴", "#9 查作息范围", "#11 查作息状态",
            "#12 查日程", "#15 24h 概览", "#16 查多日计划", "#23 按 ID 查记录",
        ],
    },
    {
        "key": "plan",
        "name": "日程与计划",
        "icon": "📅",
        "desc": "计划 CRUD / 商量 / 复盘 / 飞书同步",
        "wake_words": [
            "#13 补计划", "#14 复盘", "#17 商量计划",
            "#18 改计划", "#19 删计划", "#20 日程管家同步",
            "复盘今日", "复盘本周", "复盘本月", "复盘区间",
        ],
    },
    {
        "key": "analyze",
        "name": "分析与洞察",
        "icon": "🔬",
        "desc": "对比 / 修正 / 类别深挖 / 异常检测 / 摘要",
        "wake_words": [
            "#24 写作息摘要", "#25 对比两个月", "#26 修正作息",
            "T4 类别深挖", "T5 异常检测",
        ],
    },
    {
        "key": "admin",
        "name": "辅助与管理",
        "icon": "⚙️",
        "desc": "飞书探测 / 初始化数据库",
        "wake_words": ["#21 飞书探测", "#22 初始化数据库"],
    },
]

# 反向索引:wake_word → category_key
WAKE_WORD_TO_CATEGORY = {}
for _cat in CATEGORY_MAP:
    for _ww in _cat["wake_words"]:
        WAKE_WORD_TO_CATEGORY[_ww] = _cat["key"]


def group_by_category(scenarios: list[dict]) -> list[dict]:
    """按 category → wake_word 二级分组,生成 categories 列表

    第一性:category 硬编码在 CATEGORY_MAP(对标饼干记账的 _categories 字段),
    scenarios.yaml 不变(§07 契约不动)。未在 CATEGORY_MAP 里的 wake_word
    自动归到 "_uncategorized" 类别(防御性兜底)。
    """
    # 第一步:category → wake_word → scenarios
    bucket: dict[str, dict[str, list[dict]]] = {}
    for s in scenarios:
        wake = s["wake_word"]
        cat_key = WAKE_WORD_TO_CATEGORY.get(wake, "_uncategorized")
        if cat_key not in bucket:
            bucket[cat_key] = {}
        if wake not in bucket[cat_key]:
            bucket[cat_key][wake] = []
        bucket[cat_key][wake].append(s)

    # 第二步:按 CATEGORY_MAP 顺序组装 categories
    categories = []
    for cat in CATEGORY_MAP:
        cat_key = cat["key"]
        if cat_key not in bucket:
            continue
        wws = []
        for wake, scs in bucket[cat_key].items():
            pending = sum(1 for s in scs if s.get("status") == "【待开发】")
            wws.append({
                "wake_word": wake,
                "pending_count": pending,
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
                    for s in scs
                ],
            })
        pending_count = sum(ww["pending_count"] for ww in wws)
        categories.append({
            "key": cat_key,
            "name": cat["name"],
            "icon": cat["icon"],
            "desc": cat.get("desc", ""),
            "wake_words": wws,
            "pending_count": pending_count,
        })

    # 兜底:未在 CATEGORY_MAP 的 wake_word 放到 _uncategorized 类别
    if "_uncategorized" in bucket:
        wws = []
        for wake, scs in bucket["_uncategorized"].items():
            pending = sum(1 for s in scs if s.get("status") == "【待开发】")
            wws.append({
                "wake_word": wake,
                "pending_count": pending,
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
                    for s in scs
                ],
            })
        pending_count = sum(ww["pending_count"] for ww in wws)
        categories.append({
            "key": "_uncategorized",
            "name": "未分类(防御性兜底)",
            "icon": "❓",
            "desc": "未在 CATEGORY_MAP 中登记的唤醒词",
            "wake_words": wws,
            "pending_count": pending_count,
        })

    return categories


def build_payload(scenarios: list[dict], categories: list[dict]) -> dict:
    """构造注入 payload(3 层折叠:category → wake_word → scenario)"""
    return {
        "category_count": len(categories),
        "wakeword_count": sum(len(c["wake_words"]) for c in categories),
        "scenario_count": len(scenarios),
        "pending_count": sum(1 for s in scenarios if s.get("status") == "【待开发】"),
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "categories": categories,
    }


def inject_data(template: str, payload: dict) -> str:
    """替换模板中的占位符(总纲 §04 原则 4)"""
    # 1. 占位符唯一性校验
    if template.count("<!--INJECT-DATA-->") != 1:
        raise ValueError(f"模板占位符 <!--INJECT-DATA--> 必须唯一(实际 {template.count('<!--INJECT-DATA-->')} 处)")

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


def sync_to_stable_mirror(rendered_html: str) -> Path:
    """同步渲染产物到根目录 `作息管家.html`(ADR-0001 · 稳定入口)

    第一性:根目录 `作息管家.html` 是 HELP HTML 的"永远最新"稳定入口 —
    每次 help_render.py 跑完自动覆盖写,与 `schedule_html/help/作息管家_HELP_<TS>.html`
    (历史快照,遵守总纲 §04 原则 12)并存。

    总纲 §04 原则 12 "绝不覆盖 + _N 冲突保护" 在此处被 ADR-0001 显式豁免:
    - 镜像在 SKILL_DIR 根目录(IDE 即开即看),无 timestamp,覆盖写
    - 历史快照在 schedule_html/help/ 子目录,带 timestamp,不覆盖(原则 12)

    Returns:
        镜像 Path(已写入)。调用方应将此路径放入 data.mirror_path 字段。
    """
    mirror_path = SKILL_DIR / "作息管家.html"
    mirror_path.write_text(rendered_html, encoding="utf-8")
    return mirror_path


def render(out_path: Path) -> dict:
    """主渲染流程,返回 {status, data, message} 三段式

    ADR-0001:渲染完成后自动同步到根目录作息管家.html(无 flag,自动)。
    """
    # 1. 加载场景资产
    scenarios, error = load_scenarios()
    if error:
        # 失败仍生成 HTML(走 5 状态 fallback:错)
        payload = {
            "category_count": 0,
            "wakeword_count": 0,
            "scenario_count": 0,
            "pending_count": 0,
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "categories": [],
            "error": error,
        }
        categories = []
    else:
        categories = group_by_category(scenarios)
        payload = build_payload(scenarios, categories)

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

    # 4. 写主输出(schedule_html/help/作息管家_HELP_<TS>.html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024

    # 5. ADR-0001 · 同步到根目录作息管家.html(稳定入口,覆盖写)
    mirror_path = sync_to_stable_mirror(rendered)

    return {
        "status": "ok" if not error else "error",
        "data": {
            "file_path": str(out_path),
            "mirror_path": str(mirror_path),
            "size_kb": size_kb,
            "wakeword_count": payload["wakeword_count"],
            "scenario_count": payload["scenario_count"],
            "pending_count": payload["pending_count"],
        },
        "message": (
            f"✓ HELP 中心已生成: {payload['wakeword_count']} 唤醒词 / "
            f"{payload['scenario_count']} 场景 / {payload['pending_count']} 待开发 ({size_kb} KB)"
            f" · 已同步镜像 → {mirror_path.name}"
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