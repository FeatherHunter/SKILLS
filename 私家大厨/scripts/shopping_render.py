#!/usr/bin/env python3
"""
私家大厨 - 采购清单 HTML 渲染器

数据流:
    shopping_manager.py generate → JSON → Jinja2 模板 → HTML 文件

设计:
    - 不直连数据库,所有数据通过 shopping_manager.py 拿(单一数据源)
    - 模板用 Jinja2 + autoescape 防 XSS
    - 输出文件名 slugify(防 Windows 非法字符)
    - 尊重 CHEF_OUTPUT_DIR 环境变量
    - 输出目录:CookHub/shopping/(与 recipes/ 分离)
"""
import sys
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

# 依赖:Jinja2
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("错误:缺少依赖 jinja2。请运行:pip install jinja2", file=sys.stderr)
    sys.exit(1)


# 路径常量
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "shopping_view.html"
SHOPPING_MANAGER = SCRIPT_DIR / "shopping_manager.py"
RECIPE_MANAGER = SCRIPT_DIR / "recipe_manager.py"


# ── 文件名清洗(slugify)──
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')

def slugify(name: str) -> str:
    """Windows-safe 文件名"""
    if not name:
        return "untitled"
    s = _ILLEGAL.sub('_', name)
    s = _WHITESPACE.sub('_', s)
    s = s.strip('_.')
    return s[:60] or "untitled"


# ── 数据获取(走 shopping_manager 子进程)──
def resolve_recipe_ids(recipe_ids_or_names: str) -> str:
    """允许传 recipe_id 或菜名;菜名先走 recipe_manager.py show --json 解析成稳定 ID"""
    values = [v.strip() for v in recipe_ids_or_names.split(",") if v.strip()]
    resolved = []
    for value in values:
        result = subprocess.run(
            [sys.executable, str(RECIPE_MANAGER), "show", value, "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            raise RuntimeError(f"recipe_manager 调用失败: {result.stderr.strip()}")
        data = json.loads(result.stdout)
        if data.get("status") != "success":
            raise RuntimeError(data.get("message") or f"未找到食谱:{value}")
        recipe_id = ((data.get("data") or {}).get("recipe") or {}).get("id")
        if not recipe_id:
            raise RuntimeError(f"无法解析 recipe_id:{value}")
        resolved.append(recipe_id)
    return ",".join(resolved)


def fetch_shopping_json(recipe_ids_str: str, exclude_optional: bool = False) -> dict:
    """调用 shopping_manager.py generate,返回 dict"""
    stable_ids = resolve_recipe_ids(recipe_ids_str)
    cmd = [
        sys.executable, str(SHOPPING_MANAGER), "generate", stable_ids, "--json"
    ]
    if exclude_optional:
        cmd.append("--exclude-optional")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"shopping_manager 调用失败: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if data.get("status") != "success":
        raise RuntimeError(f"shopping_manager 返回错误: {data.get('message')}")
    return data.get("data", {})


# ── Jinja2 环境──
def make_env() -> Environment:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在: {TEMPLATE_PATH}")
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


# ── 渲染主函数──
def render(args):
    """渲染采购清单为 HTML"""
    recipe_ids_str = args.get("<recipe_id>") or args.get("<recipe_ids>")
    if not recipe_ids_str:
        print("错误:请提供 recipe_id(逗号分隔)", file=sys.stderr)
        return False

    exclude_optional = bool(args.get("--exclude-optional"))

    # 1. 拿数据
    try:
        data = fetch_shopping_json(recipe_ids_str, exclude_optional)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"错误:{e}", file=sys.stderr)
        return False

    # 2. 渲染
    try:
        env = make_env()
        template = env.get_template(TEMPLATE_PATH.name)
        html = template.render(data=data)
    except Exception as e:
        print(f"渲染失败:{e}", file=sys.stderr)
        return False

    # 3. 输出路径
    output_arg = args.get("--output")
    if output_arg:
        output_path = Path(output_arg)
    else:
        # 默认:$CHEF_OUTPUT_DIR/shopping/<slug>.html
        base_dir = Path(os.environ.get("CHEF_OUTPUT_DIR", "D:/CookHub"))
        shopping_dir = base_dir / "shopping"
        shopping_dir.mkdir(parents=True, exist_ok=True)

        # 文件名: 采购清单_<菜名连接>_<时间戳>.html
        names = data.get("recipe_names", [])
        if not names:
            slug = "untitled"
        elif len(names) == 1:
            slug = slugify(names[0])
        else:
            slug = "+".join(slugify(n) for n in names)[:50]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = shopping_dir / f"采购清单_{slug}_{ts}.html"

    # 4. 覆盖保护
    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    # 5. 写文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ 已渲染:{output_path}  ({len(html)} bytes)")
    return True


# ── CLI──
def main():
    if len(sys.argv) < 2:
        print("""用法:
    python shopping_render.py render <recipe_id>[,<recipe_id2>,...] [选项]

示例:
    python shopping_render.py render 宫保虾球
    python shopping_render.py render 宫保虾球,辣炒虾球
    python shopping_render.py render 宫保虾球 --exclude-optional
    python shopping_render.py render 宫保虾球 --output ./preview.html

环境变量:
    CHEF_OUTPUT_DIR   HTML 输出目录(默认:D:/CookHub)
    输出子目录: $CHEF_OUTPUT_DIR/shopping/
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
            if "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            i += 1

    if action == "render":
        render(args)
    else:
        print(f"未知操作:{action}", file=sys.stderr)


if __name__ == "__main__":
    main()