#!/usr/bin/env python3
"""
私家大厨 · 批量编辑 HTML 渲染器(场景 2)

调用 9 个 manager CLI 收集某菜的所有数据 → 渲染 1 个 3-tab HTML

设计原则(§04 原则 10 单工铁律):
  HTML 不能直接调 CLI / 写 DB
  用户编辑 → 点"复制修改 prompt" → 复制 prompt 文本到剪贴板
  用户切 AI 对话 → 粘贴 → AI 调 manager CLI 写 DB

类型:
  - 3 tab: 食材 / 步骤 / 标签
  - 每个 tab 末尾"复制 prompt 按钮"

复用 9 个 manager 的数据(让 13 manager 第二次真正"被用"):
  - recipe_manager.py show         (--json)
  - ingredient_manager.py list     (启发式解析)
  - step_manager.py list           (启发式解析)
  - 7 个标签 manager               (启发式解析)
"""
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "batch_edit.html"


def call_cli_raw(*args, json_mode=True):
    """调 scripts/<args>"""
    cmd = ["python3", str(SCRIPT_DIR / args[0])] + list(args[1:])
    if json_mode:
        cmd.append("--json")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def call_cli_fallback(*args):
    """调 scripts/<args> 无 --json"""
    cmd = ["python3", str(SCRIPT_DIR / args[0])] + list(args[1:])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def resolve_recipe_id(query: str):
    """菜名或 recipe_id → recipe_id"""
    raw = call_cli_raw("recipe_manager.py", "show", query, json_mode=True)
    try:
        data = json.loads(raw)
        if data.get("status") == "success":
            r = data.get("data", {}).get("recipe", {})
            return r.get("id"), r.get("name")
    except (json.JSONDecodeError, KeyError):
        pass
    return None, None


def collect_basics(recipe_id: str) -> dict:
    """用 recipe_manager --json 拿菜名 + ID(如已是 recipe_id 则保持)"""
    raw = call_cli_raw("recipe_manager.py", "show", recipe_id, json_mode=True)
    try:
        data = json.loads(raw)
        if data.get("status") == "success":
            r = data.get("data", {}).get("recipe", {})
            return {
                "recipe_id": r.get("id", recipe_id),
                "recipe_name": r.get("name", "?"),
            }
    except (json.JSONDecodeError, KeyError):
        pass
    return {"recipe_id": recipe_id, "recipe_name": "?"}


def collect_ingredients(recipe_id: str) -> list:
    """启发式解析 ingredient_manager.list 输出"""
    raw = call_cli_fallback("ingredient_manager.py", "list", recipe_id)
    items = []
    for line in raw.split("\n"):
        # 格式: "  1. [蔬菜]螺丝椒 250.0g约 4 根  → 可用无替代品代替"
        m = re.match(r'\s+(\d+)\.\s*\[([^\]]+)\]\s*(\S+)\s+(.+?)(?:\s+→\s+(.*))?$', line)
        if m:
            seq, cat, name, qty, sub = m.groups()
            items.append({
                "id": "",
                "name": name.strip(),
                "category": cat.strip(),
                "quantity_text": qty.strip(),
                "substitute": (sub or "").strip() or "无",
            })
    return items


def collect_steps(recipe_id: str) -> list:
    """启发式解析 step_manager.list 输出"""
    raw = call_cli_fallback("step_manager.py", "list", recipe_id)
    items = []
    for line in raw.split("\n"):
        # 格式: "  第1步(5分钟) [中火]:贵州黑山猪五花肉(②)切片不要太薄,..."
        m = re.match(r'\s*第(\d+)步\((\d+)分钟\)\s*\[([^\]]+)\]:\s*(.+?)(?:\s+→\s+(.+))?$', line)
        if m:
            seq, dur, heat, action, expected = m.groups()
            items.append({
                "id": "",
                "sequence": int(seq),
                "action": action.strip(),
                "duration_minutes": int(dur),
                "heat_level": heat.strip(),
                "expected_result": (expected or "").strip(),
            })
    return items


def collect_tags(recipe_id: str) -> dict:
    """7 个标签 manager 启发式解析 + recipe_manager.category 取菜系"""
    tags = {}

    # 菜系 / 地区 / 国家 — 用 recipe_manager --json
    raw = call_cli_raw("recipe_manager.py", "show", recipe_id, json_mode=True)
    try:
        data = json.loads(raw)
        if data.get("status") == "success":
            cat = data.get("data", {}).get("category", {}) or {}
            if cat.get("cuisine"):
                tags["菜系"] = cat["cuisine"]
            if cat.get("region"):
                tags["地区"] = cat["region"]
            if cat.get("country"):
                tags["国家"] = cat["country"]
    except (json.JSONDecodeError, KeyError):
        pass

    # 6 个标签 manager — fallback 解析
    for tag_type, manager_fn in [
        ("适合季节", "season_manager"),
        ("口味", "flavor_manager"),
        ("烹饪方式", "cooking_method_manager"),
        ("饮食标签", "diet_tag_manager"),
        ("用餐类型", "meal_type_manager"),
        ("炊具", "cookware_manager"),
    ]:
        raw = call_cli_fallback(f"{manager_fn}.py", "list", recipe_id)
        if "没有" in raw:
            continue
        values = []
        for line in raw.split("\n"):
            m = re.match(r'\s*-\s*(.+)', line)
            if m:
                values.append(m.group(1).strip())
        if values:
            tags[tag_type] = "/".join(values)

    return tags


def render_batch_edit_html(recipe_id: str, out_path=None) -> str:
    """渲染批量编辑 HTML"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在:{TEMPLATE_PATH}")

    basics = collect_basics(recipe_id)
    ingredients = collect_ingredients(basics["recipe_id"])
    steps = collect_steps(basics["recipe_id"])
    tags = collect_tags(basics["recipe_id"])

    payload = {
        **basics,
        "ingredients": ingredients,
        "steps": steps,
        "tags": tags,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'

    placeholder = "<!--INJECT-DATA-->"
    count = template.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    output = template.replace(placeholder, script_tag, 1)

    if out_path:
        out = Path(out_path)
    else:
        base_dir = Path(os.environ.get("CHEF_OUTPUT_DIR", "D:/CookHub")) / "batch_edit"
        base_dir.mkdir(parents=True, exist_ok=True)
        slug = basics["recipe_id"][:8] if len(basics["recipe_id"]) >= 8 else basics["recipe_id"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = base_dir / f"批量编辑_{slug}_{ts}.html"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("""

用法:
    python scripts/render_batch_edit.py <recipe_id_or_name> [--out <path>]

调用的 9 个 manager(场景 2 让 13 manager 真正"被用"):
    - recipe_manager.py show                (--json)
    - ingredient_manager.py list            (启发式解析)
    - step_manager.py list                  (启发式解析)
    - relation_manager.py list-parent       (未直接调,标签分类综合)
    - season_manager.py list               (启发式)
    - flavor_manager.py list                (启发式)
    - cooking_method_manager.py list        (启发式)
    - diet_tag_manager.py list              (启发式)
    - meal_type_manager.py list             (启发式)
    - cookware_manager.py list              (启发式)
""")
        sys.exit(0)

    recipe_id = sys.argv[1]
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    # 菜名 → recipe_id(ingredient_manager / step_manager 等要求 ID)
    resolved_id, resolved_name = resolve_recipe_id(recipe_id)
    if resolved_id:
        recipe_id = resolved_id
        print(f"已解析菜名: {resolved_name} → {recipe_id[:8]}")

    try:
        out = render_batch_edit_html(recipe_id, output_path)
        print(f"✅ 已渲染: {out}")
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)
