#!/usr/bin/env python3
"""
私家大厨 - 食谱渲染器
数据流: recipe_manager.py export-json  →  占位符注入模板  →  HTML 文件

设计原则:
- 不直连数据库,所有数据通过 recipe_manager.py 拿(单一数据源)
- 模板用 <!--INJECT-DATA--> 占位符 + window.__RECIPE__ 注入(去 Jinja2 · T1)
- 输出文件名 slugify(防 Windows 非法字符)
- 输出目录: output_config 统一解析(env 优先 + 平台感知兜底)
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

from output_config import get_output_root, get_output_dir


# 路径常量 - 跨平台,基于 __file__
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
from output_config import get_output_root, get_output_dir
TEMPLATE_PATH = SKILL_DIR / "templates" / "recipe_view.html"
RECIPE_MANAGER = SCRIPT_DIR / "recipe_manager.py"


# ── 文件名清洗(slugify)──────────────────────────────────────────
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')

def slugify(name: str) -> str:
    """Windows-safe 文件名:去除非法字符,空格转下划线,限制长度"""
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:80] or "untitled"


# ── 数据获取(走 recipe_manager 子进程)───────────────────────────
def fetch_recipe_json(name_or_id: str) -> dict:
    """调用 recipe_manager.py export-json,返回 dict"""
    result = subprocess.run(
        [sys.executable, str(RECIPE_MANAGER), "export-json", name_or_id, "--compact"],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(f"recipe_manager 调用失败: {result.stderr.strip()}")
    if not result.stdout.strip():
        raise RuntimeError(f"未找到食谱: {name_or_id}")
    return json.loads(result.stdout)


# ── 占位符注入(去 Jinja2 · T1 · 对齐 data_view/shopping 范式)──
def inject_data(template_html: str, payload: dict) -> str:
    """注入 payload 到 <!--INJECT-DATA--> 占位符(唯一 1 次)"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__RECIPE__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


# ── 渲染主函数────────────────────────────────────────────────────
def render(args):
    """渲染单道食谱为 HTML"""
    name_or_id = args.get("<菜名>")
    if not name_or_id:
        print("错误:请提供菜名或 recipe_id", file=sys.stderr)
        return False

    # 1. 拿数据
    try:
        recipe = fetch_recipe_json(name_or_id)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"错误:{e}", file=sys.stderr)
        return False

    # 2. 渲染(占位符注入)
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        html = inject_data(template, {"recipe": recipe})
    except ValueError as e:
        print(f"渲染失败:{e}", file=sys.stderr)
        return False

    # 3. 输出路径
    output_arg = args.get("--output")
    if output_arg:
        output_path = Path(output_arg)
    else:
        # 默认:$CHEF_OUTPUT_DIR/recipes/<slug>.html(尊重环境变量)
        base_dir = get_output_root()
        recipes_dir = base_dir / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(recipe.get("name") or "") or recipe.get("id", "untitled")[:8]
        output_path = recipes_dir / f"{slug}.html"

    # 4. 覆盖保护
    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    # 5. 写文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ 已渲染:{output_path}  ({len(html)} bytes)")
    return True


# ── CLI───────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("""用法:
    python recipe_render.py render <菜名或ID> [--output <path>] [--no-clobber]

示例:
    python recipe_render.py render 宫保虾球
    python recipe_render.py render 宫保虾球 --output ./preview.html
    python recipe_render.py render <UUID> --no-clobber

环境变量:
    CHEF_OUTPUT_DIR   HTML 输出目录(默认:output)
""")
        return

    action = sys.argv[1]
    args = {}

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        else:
            if action == "render" and i == 2:
                args["<菜名>"] = arg
            else:
                args[f"arg{i}"] = arg
            i += 1

    if action == "render":
        render(args)
    else:
        print(f"未知操作:{action}", file=sys.stderr)


if __name__ == "__main__":
    main()