#!/usr/bin/env python3
"""
私家大厨 · 录入域渲染器(T5 · v4.0 录入域实施)

职责: 渲染录入域的 2 个模板(08-HTML交互规范 · 采集+回执):
    templates/录入/采集.html   三态采集表单(AI 确认 / AI 推测标色 / 缺失红补 · G2 决策)
    templates/录入/回执.html   成功回执(结果+diff+撤销)/ 失败回执(原因+重试 · 08 §6.1)

数据流:
    AI 收集/校验 → payload JSON 文件 → 本脚本注入模板 → HTML(输出双通道:文字一句话 + HTML)

用法:
    python scripts/render_add.py collect  <payload.json> [--out <path>]
    python scripts/render_add.py receipt <payload.json> [--out <path>]

输出:
    $CHEF_OUTPUT_DIR/录入/录入采集_<slug>_<YYYYMMDD_HHMMSS>.html
    $CHEF_OUTPUT_DIR/录入/录入回执_<slug>_<YYYYMMDD_HHMMSS>.html
    同秒重复渲染 → _N 后缀防覆盖(08 12.A 精神)

payload 契约:
    collect:  {scene_id, scene_title, wake_word, command_cn, occurred_at, stage,
               target, fields: [{path, label, value, state, note}], payload}
              state ∈ confirmed(正常) / guessed(标色+角标) / missing(红补)
    receipt:  {mode: success|failure, scene_id, scene_title, wake_word, command_cn,
               occurred_at, stage, operation, payload, ...}
              success 追加: result, diff[], recipe_id, undo_prompt, next_steps[]
              failure 追加: failure_reason, key_data, next_step, retry_prompt, logs
"""
import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
from output_config import get_output_dir

TEMPLATE_COLLECT = SKILL_DIR / "templates" / "录入" / "采集.html"
TEMPLATE_RECEIPT = SKILL_DIR / "templates" / "录入" / "回执.html"

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


def _pick_output(slug: str, output_path: str = None) -> Path:
    if output_path:
        return Path(output_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = get_output_dir("录入") / f"{slug}_{ts}.html"
    out = base
    n = 2
    while out.exists():  # _N 防覆盖(08 12.A 精神)
        out = base.with_name(f"{base.stem}_{n}{base.suffix}")
        n += 1
    return out


def render(template: Path, payload: dict, slug: str, output_path: str = None) -> Path:
    if not template.exists():
        raise FileNotFoundError(f"模板不存在: {template}")
    html = template.read_text(encoding="utf-8")
    try:
        html = inject_data(html, payload)
    except ValueError as e:
        raise ValueError(f"注入失败: {e}")
    out = _pick_output(slug, output_path)
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


def cmd_collect(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    slug = "录入采集_" + slugify(payload.get("target") or payload.get("scene_title") or "表单")
    render(TEMPLATE_COLLECT, payload, slug, output_path)
    return True


def cmd_receipt(payload_path: str, output_path: str = None) -> bool:
    payload = _load_json(payload_path)
    mode = payload.get("mode", "success")
    slug = "录入回执_" + ("成功" if mode == "success" else "失败") + "_" + slugify(payload.get("target") or payload.get("operation") or "回执")
    render(TEMPLATE_RECEIPT, payload, slug, output_path)
    return True


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("""\n用法:
    python scripts/render_add.py collect <payload.json> [--out <path>]
    python scripts/render_add.py receipt <payload.json> [--out <path>]

环境变量:
    CHEF_OUTPUT_DIR / SKILLS_DATA_DIR   HTML 输出根目录(默认平台兜底)
""")
        return

    subcommand = sys.argv[1]
    payload_path = sys.argv[2]
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    dispatch = {"collect": cmd_collect, "receipt": cmd_receipt}
    if subcommand not in dispatch:
        print(f"❌ 未知子命令: {subcommand}. 支持: collect / receipt", file=sys.stderr)
        sys.exit(1)
    try:
        ok = dispatch[subcommand](payload_path, output_path)
    except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
        print(f"❌ {subcommand} 失败: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
