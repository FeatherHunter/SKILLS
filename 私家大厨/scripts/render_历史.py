#!/usr/bin/env python3
"""
私家大厨 · 历史域渲染器(T10 · v4.0 历史域实施)

职责: 渲染历史域的 2 个场景 HTML(08-HTML交互规范 · 采集+回执 / 查看):
    templates/历史/record_receipt.html    hist-1 记录做菜回执(成功=结果+diff+撤销 / 失败=原因+重试 · 08 §6.1)
    templates/历史/data_view_global.html  hist-4 全局统计画像(做过几道菜/总次数/最爱/最近/还没做过 · 单查询)

数据流:
    AI 记录做菜 → history_manager.py add --json → 回执 payload JSON 文件 → 本脚本注入模板 → HTML(输出双通道)
    AI 查看统计(不带菜名) → history_manager.py global-stats --json → 本脚本聚合 → 注入模板 → HTML

用法:
    python scripts/render_历史.py receipt <payload.json> [--out <path>]
    python scripts/render_历史.py global [--out <path>]

输出:
    $CHEF_OUTPUT_DIR/历史/记录做菜回执_<slug>_<YYYYMMDD_HHMMSS>.html
    $CHEF_OUTPUT_DIR/dashboard/数据视图_global_<YYYYMMDD_HHMMSS>.html
    同秒重复渲染 → _N 后缀防覆盖(08 12.A 精装 · N=1 起步)

receipt payload 契约:
    {mode: success|failure, scene_id, scene_title, wake_word, command_cn,
     occurred_at, stage, operation, target, payload, ...}
    success 追加: result, diff[{action,field,summary}], history_id, undo_prompt, next_steps[], reminder
    failure 追加: failure_reason, key_data, next_step, retry_prompt, logs
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
sys.path.insert(0, str(SCRIPT_DIR))
from output_config import get_output_dir

TEMPLATE_RECEIPT = SKILL_DIR / "templates" / "历史" / "record_receipt.html"
TEMPLATE_GLOBAL = SKILL_DIR / "templates" / "历史" / "data_view_global.html"

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
    """注入 payload 到 <!--INJECT-DATA--> 占位符(§04 原则 4 #1,#3 · 军规 11 可执行注入)"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


def _pick_output(subdir: str, slug: str, output_path: str = None) -> Path:
    """输出路径:_N 后缀防覆盖(08 12.A · N=1 起步)"""
    if output_path:
        return Path(output_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = get_output_dir(subdir) / f"{slug}_{ts}.html"
    out = base
    n = 2
    while out.exists():
        out = base.with_name(f"{base.stem}_{n}{base.suffix}")
        n += 1
    return out


def render(template: Path, payload: dict, slug: str, subdir: str, output_path: str = None) -> Path:
    if not template.exists():
        raise FileNotFoundError(f"模板不存在: {template}")
    html = template.read_text(encoding="utf-8")
    try:
        html = inject_data(html, payload)
    except ValueError as e:
        raise ValueError(f"注入失败: {e}")
    out = _pick_output(subdir, slug, output_path)
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


def call_global_stats() -> dict:
    """调 history_manager global-stats --json,返回 data.global(单查询画像)"""
    cmd = [sys.executable, str(SCRIPT_DIR / "history_manager.py"), "global-stats", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"global-stats 失败: {result.stderr.strip() or 'unknown'}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"global-stats 输出非 JSON: {e}\n前 200 字符: {result.stdout[:200]}")
    if data.get("status") != "success":
        raise RuntimeError(f"global-stats 返错: {data.get('message', 'unknown')}")
    return data.get("data", {}).get("global", {})


def cmd_receipt(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    mode = payload.get("mode", "success")
    slug = "记录做菜回执_" + ("成功" if mode == "success" else "失败") + "_" + slugify(payload.get("target") or payload.get("operation") or "回执")
    render(TEMPLATE_RECEIPT, payload, slug, "历史", output_path)
    return True


def cmd_global(output_path: str = None) -> bool:
    g = call_global_stats()
    payload = {
        "type": "global",
        "title": "全局统计(整体画像)",
        "scene_id": "view_stats_global",
        "scene_title": "全局统计(整体画像)",
        "command_cn": "查看统计",
        "wake_word": "查看统计",
        "target": "全部食谱",
        "occurred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "global": g,
        "items_count": g.get("cooked_count", 0),
        "logs": {
            "thought_chain": "意图理解: 查看统计(无菜名) → 路由 hist-4 全局画像(带菜名则走 hist-3 单菜统计) → 调 history_manager global-stats",
            "call_chain": "python scripts/history_manager.py global-stats --json → python scripts/render_历史.py global",
        },
    }
    render(TEMPLATE_GLOBAL, payload, "数据视图_global", "dashboard", output_path)
    return True


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    subcommand = sys.argv[1]
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    try:
        if subcommand == "receipt":
            if len(sys.argv) < 3:
                print("❌ receipt 需要 <payload.json> 参数", file=sys.stderr)
                sys.exit(1)
            ok = cmd_receipt(sys.argv[2], output_path)
        elif subcommand == "global":
            ok = cmd_global(output_path)
        else:
            print(f"❌ 未知子命令: {subcommand}. 支持: receipt / global", file=sys.stderr)
            sys.exit(1)
    except (json.JSONDecodeError, FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"❌ {subcommand} 失败: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
