# render_搜索筛选.py - 私家大厨 · 搜索筛选域(search)渲染器
#
# 数据流:
#     scripts/搜索筛选/ops.py(search_recipes/suggest/list_all_recipes)
#                       ├─→ 占位符注入(<!--INJECT-DATA--> → window.__DATA__)
#     templates/搜索筛选/data_view.html ─┘
#                       ↓
#     $CHEF_OUTPUT_DIR/list/数据视图_search_<slug>_<YYYYMMDD_HHMMSS>.html(_N 后缀防覆盖)
#
# 08-HTML 交互规范 v1:
#     - 纠错详情层(search-2): 无结果自动纠错(同音/形近 suggest)→「你是不是想找:X」并直接展示正确结果
#     - 无结果详情层(search_no_result): 纠错仍无 → 候选列表 + 放宽关键词/录入新菜动作
#     - 双按钮硬标准: 复制数据(5 段 JSON)+ 复制日志(6 段)+ 纠错动作按钮
#     - 双通道: 本脚本输出一句话结果(AI 交付 HTML 时同步文字一句话)
#     - 网格卡片 7 字段: 菜名/难度/时间/状态/评分(avg_rating)/标签(口味+饮食)
import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 搜索筛选 import ops
from output_config import get_output_root
from align_08 import (build_copy_data, build_copy_log, inject_08_layer, unique_output_path)

SKILL_VERSION = "v4.0-T7"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "搜索筛选" / "data_view.html"

_ILLEGAL = __import__("re").compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = __import__("re").compile(r'\s+')


def slugify(name: str) -> str:
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:60] or "untitled"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 场景解析(08 契约 scene_id/command_cn · G4 场景卡)──────────────

def resolve_scene(keyword: str, exclude: list, filters: dict, correction: bool) -> tuple:
    """按查询特征解析场景标识: scenario_id + 中文命令"""
    if not keyword and not exclude and not any(filters.values()):
        return ("list_all_recipes", "查看全部")
    if exclude:
        return ("filter_exclude_ingredient", "筛选食材")
    if correction:
        return ("search_fuzzy_match", "搜索食谱")
    if keyword:
        return ("search_by_name_keyword", "搜索食谱")
    active = [k for k, v in filters.items() if v]
    if len(active) >= 2:
        return ("filter_combined", "筛选菜系")
    dim_map = {
        "cuisine": ("filter_cuisine_basic", "筛选菜系"),
        "difficulty": ("filter_difficulty_easy", "筛选难度"),
        "time_max": ("filter_time_quick", "筛选时间"),
        "cookware": ("filter_by_cookware", "筛选炊具"),
        "flavor": ("filter_by_flavor", "筛选口味"),
        "season": ("filter_by_season", "筛选季节"),
        "status": ("filter_by_status", "筛选状态"),
    }
    return dim_map.get(active[0], ("search_by_name_keyword", "搜索食谱"))


# ── 无结果动作层(search_no_result)─────────────────────────────────

def no_result_actions(keyword: str) -> list:
    return [
        {
            "label": "🔎 放宽关键词",
            "prompt": f"搜索「{keyword}」没有找到菜,请帮我放宽条件再找: 用更短的关键词、去掉筛选条件,或换个说法。",
        },
        {
            "label": "➕ 录入新菜",
            "prompt": f"「{keyword}」相关的一道菜,我想录入到私家大厨里(唤醒词:录入食谱),请开始引导我。",
        },
    ]


# ── payload 组装 ──────────────────────────────────────────────────

def build_payload(keyword: str, exclude: list, filters: dict, sort: str,
                  corrected_to: str = "") -> dict:
    """搜索 + 纠错(自动/手动)→ 渲染 payload(含 correction/suggestions)"""
    results = ops.search_recipes(keyword=keyword, exclude=exclude, filters=filters, sort=sort)
    correction = None
    suggestions = []
    original_kw = keyword

    if not results:
        if corrected_to:
            # AI 手动纠错(AI 主导,工具候选之外的同音/形近判断)
            results = ops.search_recipes(keyword=corrected_to, exclude=exclude,
                                         filters=filters, sort=sort)
            correction = {"original": keyword, "corrected": corrected_to, "auto": False}
            keyword = corrected_to
        else:
            cands = ops.suggest(keyword)
            suggestions = cands
            if cands:
                # 自动纠错: 取最高相似度候选,纠错命中直接展示正确结果
                top = cands[0]
                results = ops.search_recipes(keyword=top["name"], exclude=exclude,
                                             filters=filters, sort=sort)
                if results:
                    correction = {
                        "original": original_kw, "corrected": top["name"],
                        "auto": True, "score": top["score"],
                    }
                    keyword = top["name"]
                    suggestions = []
                else:
                    correction = None

    title = f"搜索结果: {keyword}" if keyword else "全部食谱"
    return {
        "type": "list",
        "title": title,
        "items": results,
        "items_count": len(results),
        "empty_msg": f'没有匹配"{original_kw}"的食谱,换个关键词或放宽条件试试',
        "generated_at": now_str(),
        "query": {"keyword": original_kw, "exclude": exclude, "filters": filters, "sort": sort},
        "correction": correction,
        "suggestions": suggestions if not results else [],
        "no_result_actions": no_result_actions(original_kw) if not results else [],
    }


# ── 08 信封(复制数据 5 段 + 复制日志 6 段)──────────────────────────

def build_envelope(payload: dict, scene_id: str, command_cn: str, wake_word: str,
                   cli_cmd: str, correction: dict) -> dict:
    target = f"搜索筛选: {payload['query']['keyword'] or '全部'}"
    ex = payload["query"]["exclude"]
    fl = {k: v for k, v in payload["query"]["filters"].items() if v}
    extra = [f"排除 {e}" for e in ex] + [f"{k}={v}" for k, v in fl.items()]
    if extra:
        target += " · " + " / ".join(extra)

    copy_data = build_copy_data(
        scene_id=scene_id,
        command_cn=command_cn,
        target=target,
        payload={
            "type": payload.get("type"),
            "title": payload.get("title"),
            "items_count": payload.get("items_count", 0),
            "query": payload.get("query"),
            "correction": payload.get("correction"),
            "generated_at": payload.get("generated_at"),
        },
    )
    thinking = f"意图理解 → 「{wake_word}」 → 检索 7 字段契约"
    if correction:
        thinking += f" → 无结果 → 纠错「{correction['corrected']}」({correction.get('auto') and '自动同音/形近' or 'AI 判定'})"
    elif payload["items_count"] == 0:
        thinking += " → 无结果 → 走无结果详情层(候选/放宽/录入)"
    elif ex:
        thinking += " → 排除条件 NOT 生效"
    copy_log = build_copy_log(
        scene_id=scene_id,
        command_cn=command_cn,
        wake_word=wake_word,
        thinking=thinking,
        data_structure="window.__DATA__(type/items/query/correction)· 读库(recipes/ingredients/flavors/diet_tags/history)",
        call_chain=cli_cmd,
    )
    return copy_data, copy_log


# ── 占位符注入(去 Jinja2 · T1 机制)────────────────────────────────

def inject_data(template_html: str, payload: dict) -> str:
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


# ── 渲染主函数 ────────────────────────────────────────────────────

def render_html(payload: dict, slug: str, output_path: str = None,
                scene_id: str = "search-1", command_cn: str = "搜索食谱",
                wake_word: str = "搜索食谱", cli_cmd: str = "") -> str:
    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板不存在: {TEMPLATE_PATH}", file=sys.stderr)
        return ""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    try:
        output = inject_data(template, payload)
        copy_data, copy_log = build_envelope(
            payload, scene_id, command_cn, wake_word, cli_cmd, payload.get("correction"))
        output = inject_08_layer(output, copy_data, copy_log)
    except (ValueError, OSError) as e:
        print(f"❌ 注入失败: {e}", file=sys.stderr)
        return ""

    if output_path:
        out = Path(output_path)
    else:
        target_dir = get_output_root() / "list"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = unique_output_path(target_dir, f"数据视图_search_{slug}_{ts}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    return str(out)


# ── CLI ───────────────────────────────────────────────────────────

def _parse_flags(argv: list) -> dict:
    """--key value / --flag(布尔) 极简解析"""
    out = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                out[a[2:]] = argv[i + 1]
                i += 2
            else:
                out[a[2:]] = True
                i += 1
        else:
            i += 1
    return out


def _collect_filters(f) -> dict:
    return {
        "cuisine": f.get("cuisine", ""),
        "time_max": f.get("time-max", ""),
        "difficulty": f.get("difficulty", ""),
        "status": f.get("status", ""),
        "cookware": f.get("cookware", ""),
        "flavor": f.get("flavor", ""),
        "season": f.get("season", ""),
    }


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("""用法:
    python scripts/render_搜索筛选.py search <关键词> [--exclude X] [--cuisine 川] [--time-max 30]
        [--difficulty 简单] [--status 已做] [--cookware 砂锅] [--flavor 辣] [--season 夏]
        [--sort rating|updated|name] [--corrected-to <正确词>] [--out <path>]
    python scripts/render_搜索筛选.py list-all [--sort updated] [--exclude X] [--out <path>]

示例:
    python scripts/render_搜索筛选.py search 排骨
    python scripts/render_搜索筛选.py search 宫暴鸡丁          # 无结果自动纠错「你是不是想找:宫保鸡丁」
    python scripts/render_搜索筛选.py search 宫暴鸡丁 --corrected-to 宫保鸡丁   # AI 手动纠错
    python scripts/render_搜索筛选.py search "" --exclude 辣    # 不吃辣(NOT 条件)
    python scripts/render_搜索筛选.py list-all

环境变量:
    CHEF_OUTPUT_DIR / SKILLS_DATA_DIR   HTML 输出目录(默认 D:/CookHub)
    输出子目录: $CHEF_OUTPUT_DIR/list/
""")
        return 0

    action = sys.argv[1]
    flags = _parse_flags(sys.argv[2:])
    if action == "search":
        keyword = flags.get("keyword", "") if "keyword" in flags else (
            sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "")
        exclude = flags.get("exclude", "")
        exclude = [x.strip() for x in exclude.split(",") if x.strip()] if exclude else []
        filters = _collect_filters(flags)
        sort = flags.get("sort", "rating")
        corrected_to = flags.get("corrected-to", "")
        payload = build_payload(keyword, exclude, filters, sort, corrected_to)
        scene_id, command_cn = resolve_scene(
            keyword, exclude, filters, payload.get("correction") is not None)
        wake = command_cn
        cli_cmd = f"python scripts/搜索筛选/cli.py search {keyword or '(空)'}"
        if exclude:
            cli_cmd += " " + " ".join(f"--exclude {e}" for e in exclude)
        for k, v in filters.items():
            if v:
                cli_cmd += f" --{k.replace('_', '-')} {v}"
        if corrected_to:
            cli_cmd += f" → 纠错重搜 {corrected_to}"
        slug = slugify((payload.get("correction") or {}).get("corrected") or keyword) or "all"
        out = render_html(payload, slug, flags.get("out"), scene_id, command_cn, wake, cli_cmd)
    elif action == "list-all":
        sort = flags.get("sort", "updated")
        payload = build_payload("", [], {}, sort)
        scene_id, command_cn = resolve_scene("", [], {}, False)
        out = render_html(payload, "all", flags.get("out"), scene_id, command_cn,
                          command_cn, "python scripts/搜索筛选/cli.py list-all")
    else:
        print(f"❌ 未知操作: {action}. 支持: search / list-all", file=sys.stderr)
        return 1

    if not out:
        return 1
    corr = payload.get("correction")
    line = f"✅ 已渲染: {out} · {payload['items_count']} 道菜"
    if corr:
        line += f" · 你是不是想找:「{corr['corrected']}」(原「{corr['original']}」"
        line += "自动纠错" if corr.get("auto") else "AI 纠错"
        line += ")"
    elif payload["items_count"] == 0:
        line += " · 无结果,已展示纠错/录入引导"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
