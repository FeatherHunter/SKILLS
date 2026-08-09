#!/usr/bin/env python3
"""
私家大厨 - 做菜模式 HTML 渲染器

数据流:
    recipe_manager.py show <菜名或ID> --json → 注入 templates/cooking_mode.html → HTML 文件

设计:
    - 不直连数据库,所有数据通过 recipe_manager.py 拿(单一数据源)
    - 不修改原始模板,只生成注入后的副本
    - 输出文件名遵守:做菜模式_<recipe_slug>_<YYYYMMDD_HHMMSS>.html
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
from output_config import get_output_root, get_output_dir
from align_08 import (build_copy_data, build_copy_log, inject_08_layer, unique_output_path)
TEMPLATE_PATH = SKILL_DIR / "templates" / "cooking_mode.html"
RECIPE_MANAGER = SCRIPT_DIR / "recipe_manager.py"


_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')


def slugify(name: str) -> str:
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:60] or "untitled"


def fetch_recipe_payload(name_or_id: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(RECIPE_MANAGER), "show", name_or_id, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"recipe_manager 调用失败:{result.stderr.strip()}")
    if not result.stdout.strip():
        raise RuntimeError(f"未找到食谱:{name_or_id}")
    payload = json.loads(result.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(payload.get("message") or f"未找到食谱:{name_or_id}")
    return payload


def render(args):
    name_or_id = args.get("<菜名>") or args.get("<recipe_id>")
    if not name_or_id:
        print("错误:请提供菜名或 recipe_id", file=sys.stderr)
        return False

    if not TEMPLATE_PATH.exists():
        print(f"错误:模板不存在:{TEMPLATE_PATH}", file=sys.stderr)
        return False

    try:
        payload = fetch_recipe_payload(name_or_id)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"错误:{e}", file=sys.stderr)
        return False

    data = payload.get("data") or {}
    recipe = data.get("recipe") or {}
    recipe_id = recipe.get("id") or ""
    recipe_name = recipe.get("name") or name_or_id
    steps = data.get("steps") or recipe.get("steps") or []

    # T8 cook-4 断点续做: --step N(AI 会话记忆为主,localStorage 仅增强)
    # AI 凭会话记忆「做到第 N 步」→ 生成从第 N 步开始的做菜页(URL 带 #step=N 定位)
    start_step = 1
    step_arg = args.get("--step")
    if step_arg is not None:
        try:
            start_step = int(step_arg)
        except (ValueError, TypeError):
            print(f"错误:--step 必须是正整数,收到:{step_arg!r}", file=sys.stderr)
            return False
        if start_step < 1:
            start_step = 1
        if steps:
            total = len(steps)
            if start_step > total:
                print(f"⚠ 提示:--step {start_step} 超过总步数 {total},按 {total}(最后一步)处理", file=sys.stderr)
                start_step = total
            print(f"   断点续做:从第 {start_step} / {total} 步开始", file=sys.stderr)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    recipe_id_json = json.dumps(recipe_id, ensure_ascii=False).replace("</", "<\\/")
    inject = (
        "<body>\n"
        "<script>\n"
        f"window.__RECIPE__ = {payload_json};\n"
        f"window.__RECIPE_ID__ = {recipe_id_json};\n"
        f"window.__START_STEP__ = {start_step};\n"
        "</script>"
    )
    html = template.replace("<body>", inject, 1)

    # 08 对齐:复制数据(5 段)/复制日志(6 段)
    copy_data = build_copy_data(
        scene_id="cook-4" if start_step > 1 else "cook-1",
        command_cn="做菜模式",
        target=recipe_name,
        payload={
            "recipe_id": recipe_id,
            "name": recipe_name,
            "servings": recipe.get("servings"),
            "steps_count": len(steps),
            "total_time_minutes": recipe.get("total_time_minutes"),
            "start_step": start_step,
            "mode": "断点续做" if start_step > 1 else "全新开始",
        },
    )
    copy_log = build_copy_log(
        scene_id="cook-4" if start_step > 1 else "cook-1",
        command_cn="做菜模式",
        wake_word="开始做菜 / 做菜模式",
        thinking=f"意图理解 → 开始做菜 → 调 show 取 {recipe_name} 全量数据 → 注入 cooking_mode.html"
                 + (f" → 断点续做:从第 {start_step} 步开始(--step {start_step})" if start_step > 1 else ""),
        data_structure="window.__RECIPE__(recipe/steps/ingredients)· 读库(只读)",
        call_chain=f"python recipe_manager.py show {name_or_id} --json ; python cooking_render.py render {name_or_id}"
                   + (f" --step {start_step}" if start_step > 1 else ""),
    )
    html = inject_08_layer(html, copy_data, copy_log)

    output_arg = args.get("--output")
    if output_arg:
        output_path = Path(output_arg)
    else:
        base_dir = get_output_root()
        cooking_dir = base_dir / "cooking"
        cooking_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = unique_output_path(cooking_dir, f"做菜模式_{slugify(recipe_name)}_{ts}")

    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ 已渲染:{output_path}  ({len(html)} bytes)")
    print(f"   复制数据/复制日志: 页面底部动作栏(08 硬标准)")
    if start_step > 1:
        print(f"   断点续做: 页面已从第 {start_step} 步开始(URL 锚点 #step={start_step})")
    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python cooking_render.py render <菜名或ID> [--step N] [--output <path>] [--no-clobber]

示例:
    python cooking_render.py render 辣椒炒肉
    python cooking_render.py render 辣椒炒肉 --step 3   # 断点续做:从第 3 步开始
    python cooking_render.py render 辣椒炒肉 --output C:/Users/辰辰洋洋/AppData/Local/Temp/opencode/做菜模式_辣椒炒肉_debug_20260723_183000.html  # 仅调试

环境变量:
    CHEF_OUTPUT_DIR   HTML 输出目录(默认:D:/CookHub)
    输出子目录: $CHEF_OUTPUT_DIR/cooking/

断点续做(T8 cook-4):
    AI 凭会话记忆「做到第 N 步」→ render 时加 --step N → 页面从第 N 步开始
    (URL 锚点 #step=N;localStorage 仅作增强,系统浏览器可用则用,不可用不阻塞)
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
            if action == "render" and "<菜名>" not in args:
                args["<菜名>"] = arg
            i += 1

    if action == "render":
        if render(args) is False:
            sys.exit(1)
    else:
        print(f"未知操作:{action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
