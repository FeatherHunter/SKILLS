#!/usr/bin/env python3
"""
私家大厨 · 通用数据视图渲染器(§04 原则 2 · 1 模板多 type)

数据流:
    4 类 CLI(全部已支持 --json)→ 统一聚合 → 注入 templates/data_view.html

支持 4 个子命令(对应 §04 原则 0 决策矩阵的 4 类榜单):
    search    list of recipes(搜索/筛选结果)
    history   timeline(烹饪历史,按时间倒序)
    stats     dashboard(烹饪统计,4-6 KPI 卡)
    relations list of parent/child(派生关系)

设计:
    - 不直连数据库(全部走子 CLI --json,§02 5 层架构)
    - 1 模板支持 3 type(list/timeline/dashboard)
    - 输出文件名:数据视图_<type>_<keyword>_<YYYYMMDD_HHMMSS>.html
    - 尊重 CHEF_OUTPUT_DIR 环境变量
"""
import sys
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "data_view.html"

# ── 文件名清洗 ──
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')

def slugify(name: str) -> str:
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:60] or "untitled"


# ── subprocess 调子 CLI 拿 JSON ──
def call_cli(manager_script: str, *args) -> dict:
    """调 scripts/{manager_script} <args> --json,返回 dict"""
    cmd = ["python3", str(SCRIPT_DIR / manager_script), *args, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"{manager_script} 失败: {result.stderr.strip() or 'unknown'}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{manager_script} 输出非 JSON: {e}\n前 200 字符: {result.stdout[:200]}")
    if data.get("status") != "success":
        raise RuntimeError(f"{manager_script} 返错: {data.get('message', 'unknown')}")
    return data.get("data", {})


# ── 4 个 type 适配器:CLI 输出 → 模板 payload ──
def adapt_search(keyword: str, cli_data: dict) -> dict:
    """search/筛选 → type=list"""
    # 兼容 3 个字段名:recipe_manager.search 返 'results',list 返 'recipes'
    recipes = cli_data.get("recipes") or cli_data.get("items") or cli_data.get("results") or []
    items = []
    for r in recipes:
        tags = []
        if r.get("difficulty"):
            tags.append(f"难度:{r['difficulty']}")
        if r.get("total_time_minutes"):
            tags.append(f"⏱{r['total_time_minutes']}min")
        if r.get("status"):
            tags.append(r["status"])
        items.append({
            "name": r.get("name", "?"),
            "subtitle": f"id: {r.get('id', '?')[:8]}…",
            "tags": tags,
            "rating": r.get("avg_rating"),
            "description": r.get("description"),
        })
    return {
        "type": "list",
        "title": f"搜索结果: {keyword}" if keyword else "全部食谱",
        "items": items,
        "items_count": len(items),
        "empty_msg": f'没有匹配"{keyword}"的食谱',
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def adapt_history(keyword: str, cli_data: dict) -> dict:
    """查看历史 → type=timeline"""
    history = cli_data.get("history") or cli_data.get("items") or []
    items = []
    for h in history:
        items.append({
            "date": h.get("cook_date", ""),
            "sequence": h.get("cook_sequence"),
            "rating": h.get("rating"),
            "content": h.get("feedback", "(无反馈)"),
        })
    return {
        "type": "timeline",
        "title": f"烹饪历史: {keyword}" if keyword else "烹饪历史",
        "items": items,
        "items_count": len(items),
        "empty_msg": "这道菜还没做过",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def adapt_stats(keyword: str, cli_data: dict) -> dict:
    """查看统计 → type=dashboard"""
    stats = cli_data.get("stats") or cli_data
    total = stats.get("total_cooks") or stats.get("count") or 0
    avg = stats.get("avg_rating") or 0
    mx = stats.get("max_rating") or 0
    mn = stats.get("min_rating") or 0
    last = stats.get("last_date") or "无记录"
    kpis = [
        {"label": "总次数", "value": str(total), "unit": "次", "style": "primary"},
        {"label": "平均分", "value": f"{avg:.1f}" if avg else "—", "unit": "/5", "style": "warn" if avg >= 4 else "primary"},
        {"label": "最高分", "value": f"{mx:.1f}" if mx else "—", "unit": "/5", "style": "success"},
        {"label": "最低分", "value": f"{mn:.1f}" if mn else "—", "unit": "/5", "style": "danger" if mn < 3 and mn else "primary"},
        {"label": "最近做", "value": str(last)[:10] if last != "无记录" else "—", "style": "primary"},
    ]
    return {
        "type": "dashboard",
        "title": f"烹饪统计: {keyword}" if keyword else "烹饪统计",
        "kpis": kpis,
        "items_count": total,
        "empty_msg": "暂无统计数据",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def adapt_relations(keyword: str, parent_data: dict, child_data: dict) -> dict:
    """查看派生 → type=list(简化:不画图谱,展示 parent + child 两组)"""
    items = []
    for p in parent_data.get("relations") or parent_data.get("items") or []:
        items.append({
            "name": f"派生自 {p.get('parent_name', '?')}",
            "subtitle": f"关系:{p.get('relation_type', '?')} · child: {p.get('child_name', '?')[:20]}",
            "tags": ["父本→子本"],
            "description": p.get("change_summary"),
        })
    for c in child_data.get("relations") or child_data.get("items") or []:
        items.append({
            "name": f"派生出 {c.get('child_name', '?')}",
            "subtitle": f"关系:{c.get('relation_type', '?')} · parent: {c.get('parent_name', '?')[:20]}",
            "tags": ["子本"],
            "description": c.get("change_summary"),
        })
    return {
        "type": "list",
        "title": f"派生关系: {keyword}" if keyword else "派生关系",
        "items": items,
        "items_count": len(items),
        "empty_msg": "这道菜无任何派生关系",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── 注入数据到模板 ──
def inject_data(template_html: str, payload: dict) -> str:
    """注入 payload 到 <!--INJECT-DATA--> 占位符"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


# ── 4 个子命令入口 ──
def cmd_search(keyword: str, output_path: str = None) -> bool:
    try:
        if keyword:
            cli_data = call_cli("recipe_manager.py", "search", keyword)
        else:
            cli_data = call_cli("recipe_manager.py", "list")
    except (RuntimeError, FileNotFoundError) as e:
        print(f"❌ search 失败: {e}", file=sys.stderr)
        return False
    payload = adapt_search(keyword, cli_data)
    return render_html(payload, f"search_{slugify(keyword) if keyword else 'all'}", output_path)


def cmd_history(keyword: str, output_path: str = None) -> bool:
    try:
        cli_data = call_cli("history_manager.py", "list", keyword)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"❌ history 失败: {e}", file=sys.stderr)
        return False
    payload = adapt_history(keyword, cli_data)
    return render_html(payload, f"history_{slugify(keyword)}", output_path)


def cmd_stats(keyword: str, output_path: str = None) -> bool:
    try:
        cli_data = call_cli("history_manager.py", "stats", keyword)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"❌ stats 失败: {e}", file=sys.stderr)
        return False
    payload = adapt_stats(keyword, cli_data)
    return render_html(payload, f"stats_{slugify(keyword)}", output_path)


def cmd_relations(keyword: str, output_path: str = None) -> bool:
    try:
        parent = call_cli("relation_manager.py", "list-parent", keyword)
        child = call_cli("relation_manager.py", "list-child", keyword)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"❌ relations 失败: {e}", file=sys.stderr)
        return False
    payload = adapt_relations(keyword, parent, child)
    return render_html(payload, f"relations_{slugify(keyword)}", output_path)


# ── 渲染主函数 ──
def render_html(payload: dict, slug: str, output_path: str = None) -> bool:
    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板不存在: {TEMPLATE_PATH}", file=sys.stderr)
        return False
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    try:
        output = inject_data(template, payload)
    except ValueError as e:
        print(f"❌ 注入失败: {e}", file=sys.stderr)
        return False
    if output_path:
        out = Path(output_path)
    else:
        base_dir = Path(os.environ.get("CHEF_OUTPUT_DIR", "D:/CookHub"))
        sub = payload["type"]  # list/timeline/dashboard
        target_dir = base_dir / sub
        target_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = target_dir / f"数据视图_{slug}_{ts}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    print(f"✅ 已渲染: {out}  ({len(output)/1024:.1f} KB) · type={payload['type']} · {payload.get('items_count', 0)} 项")
    return True


# ── CLI ──
def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("""\n用法:
    python scripts/render_data.py search <关键词>
    python scripts/render_data.py history <菜名或ID>
    python scripts/render_data.py stats <菜名或ID>
    python scripts/render_data.py relations <菜名或ID>
    python scripts/render_data.py <subcommand> <keyword> --out <path>

环境变量:
    CHEF_OUTPUT_DIR   HTML 输出目录(默认 D:/CookHub)
    输出子目录: \$CHEF_OUTPUT_DIR/{list,timeline,dashboard}/

子命令对应 4 类榜单(§04 原则 0):
    search    → 搜索/筛选结果(11 唤醒词)
    history   → 烹饪历史时间线
    stats     → 烹饪统计仪表盘
    relations → 派生关系列表
""")
        return

    subcommand = sys.argv[1]
    keyword = sys.argv[2] if len(sys.argv) > 2 else ""
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    dispatch = {
        "search": cmd_search,
        "history": cmd_history,
        "stats": cmd_stats,
        "relations": cmd_relations,
    }
    if subcommand not in dispatch:
        print(f"❌ 未知子命令: {subcommand}. 支持: {', '.join(dispatch.keys())}", file=sys.stderr)
        sys.exit(1)
    ok = dispatch[subcommand](keyword, output_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()