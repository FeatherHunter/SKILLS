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
from align_08 import (build_copy_data, build_copy_log, inject_08_layer, unique_output_path)


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


# ── 查看域场景映射(view-1..8 · G3 决策)──────────────────────────
# scene_id / command_cn / wake_word 随 --focus/--swap 参数切换
FOCUS_SCENE = {
    "食材": ("view-4", "查看食材", "查看食材"),
    "步骤": ("view-6", "查看步骤", "查看步骤"),
    "营养": ("view-7", "查看营养", "查看营养"),
    "背景": ("view-8", "查看背景", "查看背景"),
}


def parse_swap(spec: str) -> list:
    """解析 --swap 参数(可多次):'原:替换' 或 '原:替换:用量'

    例: --swap 五花肉:鸡胸肉 --swap 螺丝椒:青椒:300
    """
    result = []
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for p in parts:
        seg = [s.strip() for s in p.split(":")]
        if len(seg) >= 2 and seg[0] and seg[1]:
            entry = {"from": seg[0], "to": seg[1]}
            if len(seg) >= 3 and seg[2]:
                try:
                    entry["qty"] = float(seg[2])
                except ValueError:
                    entry["qty"] = seg[2]
            result.append(entry)
    return result


def build_view_config(args: dict) -> dict:
    """构造 view 配置(focus 只看 X / swap 替换食材预览 · 均不落库)"""
    view = {}
    focus = args.get("--focus")
    if focus in FOCUS_SCENE:
        view["focus"] = focus
    swaps = []
    for key, val in args.items():
        if key.startswith("--swap") and val:
            swaps.extend(parse_swap(str(val)))
    if swaps:
        view["swap"] = swaps
    return view


def scene_meta(view: dict) -> tuple:
    """根据 view 配置选场景元数据(scene_id/command_cn/wake_word)"""
    if view.get("swap"):
        return ("view-3", "查看食谱", "查看食谱(替换食材预览)")
    if view.get("focus"):
        sid, cn, ww = FOCUS_SCENE[view["focus"]]
        return (sid, cn, ww)
    return ("view-1", "查看食谱", "查看食谱 / 查看食材 / 查看步骤 / 查看营养 / 查看背景")


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
        view = build_view_config(args)
        scene_id, command_cn, wake_word = scene_meta(view)
        payload = {
            "recipe": recipe,
            "view": view,
            "chef_output_dir": str(get_output_root()),
        }
        html = inject_data(template, payload)
        # 08 对齐:复制数据(5 段)/复制日志(6 段)
        copy_data = build_copy_data(
            scene_id=scene_id,
            command_cn=command_cn,
            target=recipe.get("name") or name_or_id,
            payload={
                "recipe_id": recipe.get("id"),
                "name": recipe.get("name"),
                "servings": recipe.get("servings"),
                "total_time": recipe.get("total_time"),
                "difficulty": recipe.get("difficulty"),
                "ingredients_count": len(recipe.get("ingredients") or []),
                "steps_count": len(recipe.get("steps") or []),
                "view": view,
            },
        )
        copy_log = build_copy_log(
            scene_id=scene_id,
            command_cn=command_cn,
            wake_word=wake_word,
            thinking=f"意图理解 → {command_cn} → 调 export-json 取 {recipe.get('name')} 全量数据 → 注入 recipe_view.html",
            data_structure="window.__RECIPE__(recipe/view/chef_output_dir)· 读库(只读)",
            call_chain=f"python recipe_manager.py export-json {name_or_id} --compact ; python recipe_render.py render {name_or_id}",
        )
        html = inject_08_layer(html, copy_data, copy_log)
    except ValueError as e:
        print(f"渲染失败:{e}", file=sys.stderr)
        return False

    # 3. 输出路径
    output_arg = args.get("--output")
    if output_arg:
        output_path = Path(output_arg)
    else:
        # 默认:$CHEF_OUTPUT_DIR/recipes/<slug>.html(尊重环境变量)
        # _N 防覆盖:同秒连跑互不覆盖(SKILL.md 12.X 冲突处理)
        base_dir = get_output_root()
        recipes_dir = base_dir / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(recipe.get("name") or "") or recipe.get("id", "untitled")[:8]
        output_path = unique_output_path(recipes_dir, slug)

    # 4. 覆盖保护
    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    # 5. 写文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ 已渲染:{output_path}  ({len(html)} bytes)")
    print(f"   复制数据/复制日志: 页面底部动作栏(08 硬标准)")
    return True


# ── CLI───────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("""用法:
    python recipe_render.py render <菜名或ID> [--output <path>] [--no-clobber]
                          [--focus 食材|步骤|营养|背景] [--swap 原食材:替换食材[:用量]]

示例:
    python recipe_render.py render 宫保虾球
    python recipe_render.py render 宫保虾球 --output ./preview.html
    python recipe_render.py render <UUID> --no-clobber
    python recipe_render.py render 辣椒炒肉 --focus 食材        # 只看食材(其他 section 隐藏)
    python recipe_render.py render 辣椒炒肉 --swap 五花肉:鸡胸肉   # 替换食材预览(不落库)
    python recipe_render.py render 辣椒炒肉 --swap 五花肉:鸡胸肉:250 --swap 螺丝椒:青椒

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
                # 可重复参数(--swap):自动 _N 去重,保留全部
                if arg.startswith("--swap"):
                    n = 0
                    while f"{arg}_{n}" in args:
                        n += 1
                    args[f"{arg}_{n}"] = sys.argv[i + 1]
                else:
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