#!/usr/bin/env python3
"""
私家大厨 · HELP HTML 渲染器(§07 §1 HELP 唤醒词契约)

数据流:
    references/scenarios.yaml ─┐
                                ├─→ 聚合(wake_word + aliases 展开)
                                ↓
    templates/help.html ──→ 占位符注入(<!--INJECT-DATA--> → <script>window.__HELP__ = {...}</script>)
                                ↓
    $CHEF_OUTPUT_DIR/help/私家大厨_HELP_<YYYYMMDD_HHMMSS>.html

设计:
    - 唯一事实源: references/scenarios.yaml(§07 §2.1)
    - 不调 CLI(场景资产不是菜谱数据)
    - 模板用占位符注入(§04 原则 4 · <!--INJECT-DATA--> 唯一)
    - 输出文件名带时间戳(与 cooking/shopping HTML 一致)
    - 尊重 CHEF_OUTPUT_DIR 环境变量(默认 D:/CookHub)
"""
import sys
import os
import re
import json
import yaml
from pathlib import Path
from datetime import datetime


# ── 路径常量 ──
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE_PATH = SKILL_DIR / "templates" / "help.html"


# ── 文件名清洗(slugify,防 Windows 非法字符) ──
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


# ── 解析场景资产 ──
def load_scenarios() -> dict:
    """读 references/scenarios.yaml,返回结构化 dict"""
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"场景资产不存在: {SCENARIOS_PATH}")
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def aggregate_wake_words(data: dict) -> list:
    """
    把 aliases 展开到 wake_words 列表
    返回 [{name, scenarios: [...], pending_count: N}, ...]
    """
    raw = data.get("scenarios") or []
    aliases = data.get("aliases") or []

    # 建立 main → list of all names(含 aliases)
    alias_map = {}  # main_name → [all_names]
    for a in aliases:
        main = a["main"]
        if isinstance(a["alias"], list):
            alias_map[main] = [main] + a["alias"]
        else:
            alias_map[main] = [main, a["alias"]]

    aggregated = []
    for entry in raw:
        main_name = entry["wake_word"]
        all_names = alias_map.get(main_name, [main_name])
        # 把 main 放在第 1 个,aliases 后续(便于 §07 §5 不展示 HELP 自身的反向校验)
        # 但这里都展示(场景共享)
        pending_count = sum(1 for s in entry["scenarios"] if s.get("status") == "【待开发】")

        # 每场景添加 wake_word 字段(供前端使用)
        for sc in entry["scenarios"]:
            sc["wake_word"] = main_name

        aggregated.append({
            "name": main_name,
            "alias_names": all_names[1:] if len(all_names) > 1 else [],
            "scenarios": entry["scenarios"],
            "pending_count": pending_count,
        })

    # aliases 扩展后的总唤醒词数
    expanded_count = sum(len(a["alias"]) + 1 if isinstance(a["alias"], list) else 2
                        for a in aliases)
    # 加上非别名唤醒词
    non_aliased = len(raw) - len(aliases)
    expanded_count += non_aliased

    return aggregated, expanded_count


# ── 注入数据到模板 ──
def inject_data(template_html: str, payload: dict) -> str:
    """
    把 payload 注入到模板的 <!--INJECT-DATA--> 占位符

    §04 原则 4:
      #1 占位符唯一(下方 assert 强制)
      #2 </ 转义(防 script 提前闭合)
      #3 typeof 守卫(模板内已实现)
      #4 5 状态 fallback(模板内已实现)
      #5 escapeHTML 函数(模板内 esc() 已实现)
    """
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(
            f"占位符 {placeholder} 必须唯一 1 次,实际 {count} 次。"
            f"检查 templates/help.html 是否被手工编辑过。"
        )

    # 转义 </ 防 script 提前闭合
    # default=str 处理 YAML date/datetime 对象
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")

    script_tag = f'<script>window.__HELP__ = {payload_json};</script>'
    injected = template_html.replace(placeholder, script_tag, 1)
    return injected


# ── 渲染主函数 ──
def render(args) -> bool:
    """
    渲染 HELP HTML

    Args:
        args["--out"]: 指定输出文件路径(可选)
        args["--output-dir"]: 指定输出目录(可选,默认 $CHEF_OUTPUT_DIR/help)
        args["--no-clobber"]: 已存在则跳过
    """
    # 1. 读场景资产
    try:
        data = load_scenarios()
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"❌ 场景资产加载失败: {e}", file=sys.stderr)
        return False

    wake_words, expanded_count = aggregate_wake_words(data)

    if not wake_words:
        print("⚠️ 场景资产为空(0 个唤醒词),HELP HTML 仍生成但无内容", file=sys.stderr)

    # 2. 构造注入 payload
    payload = {
        "meta": data.get("meta", {}),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wake_words": wake_words,
        "scenarios": [sc for ww in wake_words for sc in ww["scenarios"]],
        "aliases_expanded_count": expanded_count,
    }

    # 3. 读模板
    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板不存在: {TEMPLATE_PATH}", file=sys.stderr)
        return False

    template_html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 4. 注入
    try:
        output_html = inject_data(template_html, payload)
    except ValueError as e:
        print(f"❌ 注入失败: {e}", file=sys.stderr)
        return False

    # 5. 决定输出路径
    output_arg = args.get("--out")
    if output_arg:
        output_path = Path(output_arg)
    else:
        # 默认:$CHEF_OUTPUT_DIR/help/私家大厨_HELP_<YYYYMMDD_HHMMSS>.html
        base_dir = Path(os.environ.get("CHEF_OUTPUT_DIR", "D:/CookHub"))
        help_dir = base_dir / "help"
        help_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = help_dir / f"私家大厨_HELP_{ts}.html"

    # 6. 覆盖保护
    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    # 7. 写副本(原模板不动)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_html, encoding="utf-8")
    size_kb = len(output_html) / 1024
    print(f"✅ 已渲染:{output_path}  ({size_kb:.1f} KB)")
    print(f"   唤醒词: {len(wake_words)} (aliases 展开后 {expanded_count})")
    print(f"   场景: {len(payload['scenarios'])} "
          f"(可用 {sum(1 for s in payload['scenarios'] if s.get('status') != '【待开发】')}, "
          f"待开发 {sum(1 for s in payload['scenarios'] if s.get('status') == '【待开发】')})")
    return True


# ── CLI ──
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("""\n用法:
    python scripts/render_help.py
    python scripts/render_help.py --out ./preview.html
    python scripts/render_help.py --output-dir ./help
    python scripts/render_help.py --no-clobber

环境变量:
    CHEF_OUTPUT_DIR   HTML 输出目录(默认 D:/CookHub)
    输出子目录: $CHEF_OUTPUT_DIR/help/
""")
        return

    args = {}
    i = 1
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
            args[arg] = True
            i += 1

    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    ok = render(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()