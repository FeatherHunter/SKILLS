# render_派生.py - 私家大厨 · 派生域(relation)渲染器(T12 · v4.0 / G9 决策)
#
# 职责: 渲染派生域的 4 个模板(08-HTML交互规范):
#     templates/派生/derive_edit.html       rel-3 过程 HTML(母本全字段预填 · 三态标色 · G9)
#     templates/派生/relation_confirm.html  rel-1 添加派生关系确认卡(G8 核心骨架)
#     templates/派生/回执.html              rel-1/rel-3 成功回执(diff+撤销)/ 失败回执(08 §6.1)
#     templates/派生/relation_tree.html     rel-2 家族树(根=当前菜 · 祖先/后代多代连链)
#
# 数据流:
#     AI 收集/预填 → payload JSON 文件 → 本脚本注入模板 → HTML(输出双通道:文字一句话 + HTML)
#
# 用法:
#     python scripts/render_派生.py derive-edit <payload.json> [--out <path>]
#     python scripts/render_派生.py confirm    <payload.json> [--out <path>]
#     python scripts/render_派生.py receipt    <payload.json> [--out <path>]
#     python scripts/render_派生.py tree       <菜名或ID>     [--out <path>]
#
# 输出:
#     $CHEF_OUTPUT_DIR/派生/派生编辑_<slug>_<YYYYMMDD_HHMMSS>.html 等(_N 防覆盖 · 08 12.A)
#
# payload 契约:
#     derive-edit: {scene_id, scene_title, wake_word, command_cn, occurred_at,
#                   target(新菜名), mother:{name,summary...}, change_summary, relation_type,
#                   fields:[{path,label,value,state,note}],  # 三态: confirmed/guessed/missing
#                   payload:{recipe:{...}, parent_name, relation_type, change_summary}, logs}
#     confirm:     {scene_id, scene_title, wake_word, command_cn, occurred_at,
#                   parent_name, child_name, relation_type, change_summary,
#                   payload:{...}, logs}   # rel-1 确认卡
#     receipt:     {mode: success|failure, scene_id, scene_title, wake_word, command_cn,
#                   occurred_at, operation, target, payload, ...}
#                  success 追加: result, diff[], recipe_id, undo_prompt, next_steps[]
#                  failure 追加: failure_reason, key_data, next_step, retry_prompt, logs
import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 派生 import ops
from output_config import get_output_root

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates" / "派生"
TEMPLATES = {
    "derive-edit": TEMPLATE_DIR / "derive_edit.html",
    "confirm": TEMPLATE_DIR / "relation_confirm.html",
    "receipt": TEMPLATE_DIR / "回执.html",
    "tree": TEMPLATE_DIR / "relation_tree.html",
}

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')


def slugify(name: str) -> str:
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:40] or "untitled"


def inject_data(template_html: str, payload: dict) -> str:
    """注入 payload 到 <!--INJECT-DATA--> 占位符(§04 原则 4 #1,#3)"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


def _pick_output(subdir: str, slug: str, output_path: str = None) -> Path:
    if output_path:
        return Path(output_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = get_output_root() / "派生" / f"{slug}_{ts}.html"
    out = base
    n = 2
    while out.exists():  # _N 防覆盖(08 12.A 精神)
        out = base.with_name(f"{base.stem}_{n}{base.suffix}")
        n += 1
    return out


def render(template_key: str, payload: dict, slug: str, output_path: str = None) -> Path:
    template = TEMPLATES[template_key]
    if not template.exists():
        raise FileNotFoundError(f"模板不存在: {template}")
    html = template.read_text(encoding="utf-8")
    try:
        html = inject_data(html, payload)
    except ValueError as e:
        raise ValueError(f"注入失败: {e}")
    out = _pick_output("派生", slug, output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✅ 已渲染: {out}  ({len(html.encode('utf-8'))/1024:.1f} KB)")
    return out


def _load_json(path: str) -> dict:
    """加载 JSON payload(BOM 容错:Windows 编辑器常带 BOM)"""
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return json.loads(raw.decode("utf-8"))


def cmd_derive_edit(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    slug = "派生编辑_" + slugify(payload.get("target") or payload.get("scene_title") or "表单")
    render("derive-edit", payload, slug, output_path)
    return True


def cmd_confirm(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    slug = "关系确认_" + slugify(
        f"{payload.get('parent_name') or ''}_{payload.get('child_name') or ''}" or "确认卡")
    render("confirm", payload, slug, output_path)
    return True


def cmd_receipt(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    mode = payload.get("mode", "success")
    slug = "派生回执_" + ("成功" if mode == "success" else "失败") + "_" + slugify(
        payload.get("target") or payload.get("operation") or "回执")
    render("receipt", payload, slug, output_path)
    return True


def cmd_tree(recipe_name: str, output_path: str = None) -> bool:
    tree = ops.relation_tree(recipe_name)
    if not tree["found"]:
        print(f"❌ 未找到食谱:「{recipe_name}」(或已废弃)", file=sys.stderr)
        return False
    payload = {
        "scene_id": "view_relation_tree",
        "scene_title": "查看派生关系(家族树)",
        "wake_word": "查看派生关系",
        "command_cn": "查看派生关系",
        "occurred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": tree["root"]["name"],
        "tree": tree,
    }
    slug = "家族树_" + slugify(tree["root"]["name"])
    render("tree", payload, slug, output_path)
    return True


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("""\n用法:
    python scripts/render_派生.py derive-edit <payload.json> [--out <path>]
    python scripts/render_派生.py confirm    <payload.json> [--out <path>]
    python scripts/render_派生.py receipt    <payload.json> [--out <path>]
    python scripts/render_派生.py tree       <菜名或ID>     [--out <path>]

环境变量:
    CHEF_OUTPUT_DIR / SKILLS_DATA_DIR   HTML 输出根目录(默认平台兜底)
""")
        return 0

    action = sys.argv[1]
    arg2 = sys.argv[2] if len(sys.argv) > 2 else ""
    output_path = None
    for i, a in enumerate(sys.argv):
        if a == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    dispatch = {
        "derive-edit": lambda: cmd_derive_edit(arg2, output_path),
        "confirm": lambda: cmd_confirm(arg2, output_path),
        "receipt": lambda: cmd_receipt(arg2, output_path),
        "tree": lambda: cmd_tree(arg2, output_path),
    }
    if action not in dispatch:
        print(f"❌ 未知操作: {action}. 支持: derive-edit / confirm / receipt / tree", file=sys.stderr)
        return 1
    try:
        ok = dispatch[action]()
    except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
        print(f"❌ {action} 失败: {e}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
