#!/usr/bin/env python3
"""
私家大厨 - 采购清单 HTML 渲染器

数据流:
    shopping_manager.py generate → JSON → 占位符注入模板 → HTML 文件

设计:
    - 不直连数据库,所有数据通过 shopping_manager.py 拿(单一数据源)
    - 模板用 <!--INJECT-DATA--> 占位符 + window.__DATA__ 注入(去 Jinja2 · T1)
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


# 路径常量
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
from output_config import get_output_root, get_output_dir
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


# ── 库存核对(G6 已有vs需买 · 联动居家管家 · 禁写死 CLI)──
STOCK_ITEMS_KEYS = ("name", "qty", "unit")

def parse_stock(args: dict) -> dict:
    """解析 --stock-check / --stock-json / --stock-file

    库存数据由 AI 会话内调用「居家管家」(囤货盘点/查物品)获取,
    并完成同名/同义匹配后传入;name 对应购物清单食材名。
    返回: {"checked": bool, "items": [{"name","qty","unit"|""}, ...]}
    """
    checked = bool(args.get("--stock-check"))
    raw = args.get("--stock-json")
    if not raw and args.get("--stock-file"):
        try:
            raw = Path(args["--stock-file"]).read_text(encoding="utf-8-sig")
        except OSError as e:
            raise ValueError(f"库存文件读取失败: {e}")
    items = []
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"库存 JSON 解析失败: {e}")
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
            items = parsed["items"]
        else:
            raise ValueError("库存 JSON 结构错误,应为 [{'name','qty',...}] 或 {'items':[...]}")
    return {"checked": checked, "items": items}


def attach_stock(data: dict, stock: dict) -> dict:
    """把库存按食材名精确匹配并入清单(G6 3b:同名/同义匹配由 AI 完成)

    - 命中食材 → 项上挂 stock: {"qty", "unit"}(已有项:灰勾+双量标注)
    - data.stock: {"checked", "unavailable", "count"}
      - unavailable = 核对开启且 0 匹配(居家管家无数据/无匹配 → 淡提示,不打勾)
      - count = 已有项数(摘要「已有 N 项」)
    """
    items = stock.get("items") or []
    stock_map = {str(it.get("name")): it for it in items if it.get("name")}
    matched = 0
    for cat, ings in (data.get("ingredients_by_category") or {}).items():
        for ing in ings:
            s = stock_map.get(str(ing.get("name")))
            if s:
                ing["stock"] = {
                    "qty": s.get("qty"),
                    "unit": s.get("unit") or "",
                }
                matched += 1
    checked = bool(stock.get("checked"))
    data["stock"] = {
        "checked": checked,
        "unavailable": bool(checked and matched == 0),
        "count": matched,
    }
    return data


# ── 占位符注入(去 Jinja2 · T1 · 对齐 data_view 范式)──
def inject_data(template_html: str, payload: dict) -> str:
    """注入 payload 到 <!--INJECT-DATA--> 占位符(唯一 1 次)"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


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
        # 库存核对(联动居家管家 · G6):无数据时页面顶部淡提示
        stock = parse_stock(args)
        data = attach_stock(data, stock)
    except (RuntimeError, ValueError, json.JSONDecodeError) as e:
        print(f"错误:{e}", file=sys.stderr)
        return False

    # 2. 渲染(占位符注入)
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        html = inject_data(template, {"data": data})
        # 08 对齐:复制数据(5 段)/复制日志(6 段)
        names = data.get("recipe_names", [])
        copy_data = build_copy_data(
            scene_id="shop-1",
            command_cn="生成清单",
            target="、".join(names) if names else "",
            payload={
                "recipe_names": names,
                "summary": data.get("summary"),
                "ingredients_count": len(data.get("ingredients_by_category", {}).keys()) or 0,
            },
        )
        copy_log = build_copy_log(
            scene_id="shop-1",
            command_cn="生成清单",
            wake_word="生成清单 / 排除可选",
            thinking=f"意图理解 → 生成清单 → 解析 {len(names)} 道菜 → 合并去重食材",
            data_structure="window.__DATA__.data(ingredients_by_category/summary)· 读库(只读)",
            call_chain=f"python shopping_manager.py generate {args.get('<recipe_id>') or args.get('<recipe_ids>')} --json ; "
                       f"python shopping_render.py render {args.get('<recipe_id>') or args.get('<recipe_ids>')}",
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
        # 默认:$CHEF_OUTPUT_DIR/shopping/<slug>.html
        base_dir = get_output_root()
        shopping_dir = base_dir / "shopping"
        shopping_dir.mkdir(parents=True, exist_ok=True)

        # 文件名: 采购清单_<菜名连接>_<时间戳>.html(_N 防覆盖 · 12.X)
        if not names:
            slug = "untitled"
        elif len(names) == 1:
            slug = slugify(names[0])
        else:
            slug = "+".join(slugify(n) for n in names)[:50]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = unique_output_path(shopping_dir, f"采购清单_{slug}_{ts}")

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

库存核对(联动居家管家 · G6 已有vs需买):
    --stock-check                 本次已请求核对居家管家库存(无数据 → 顶部淡提示)
    --stock-json '<json>'         库存数据(需 AI 完成同名/同义匹配后传入)
    --stock-file <path>           同 --stock-json,从文件读
    库存 JSON 格式: {"items": [{"name": "鸡蛋", "qty": 2, "unit": "盒"}]}
    (name = 购物清单食材名;qty = 库存原文数量;unit = 物品名里的单位线索,无线索省略)

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