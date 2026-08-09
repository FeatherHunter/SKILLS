#!/usr/bin/env python3
"""饼干记账 · 目标域 HTML 渲染器(4 场景 · scenes/goal.yaml)

采集型(表单,用户填写 → 复制确认 prompt 发回 AI → AI 调 CLI 写入):
    set-budget --amount X [--month YYYY-MM] [--category 分类] → 目标/budget_form.html
    set-saving --name X --amount Y [--deadline YYYY-MM-DD]   → 目标/saving_form.html
结果型(进度条视图,AI 交付):
    budget [--month YYYY-MM]  → 目标/budget_view.html(预算 vs 实际/剩余/超支)
    saving [--name X]         → 目标/saving_view.html(已存/目标/百分比/预计达成日)

隔离契约(票面):scripts/goal/ + templates/目标/ + tests/test_goal.py,不动公共层。
输出:html_paths.html_path(设定预算|看预算|设定目标|看目标) → $DATA_DIR/biscuit_accountant_html/。

用法:
    python3 scripts/goal/render.py set-budget --amount 3000
    python3 scripts/goal/render.py budget
    python3 scripts/goal/render.py set-saving --name 换手机 --amount 10000 --deadline 2026-12-31
    python3 scripts/goal/render.py saving
"""

import sys
import os
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()  # scripts/goal/
_SCRIPTS = _SCRIPT_DIR.parent  # scripts/(公共层模块:html_paths / cli.py 同目录)
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

SKILL_DIR = _SCRIPT_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates" / "目标"
SKILL_VERSION = "2.0"

# 场景 meta(对齐 scenes/goal.yaml · 门禁 A 层 1 数据源)
GOAL_META = {
    "set-budget": {"scene_id": "goal_set_budget",    "wake_word": "设定预算",
                   "command_cn": "设定预算", "title": "设定月度预算",
                   "subtitle": "采集确认 · 写入 goals.json"},
    "budget":     {"scene_id": "goal_budget_status", "wake_word": "看预算",
                   "command_cn": "看预算", "title": "查看预算执行",
                   "subtitle": "预算 vs 实际 · 剩余/超支提示"},
    "set-saving": {"scene_id": "goal_set_saving",    "wake_word": "设定目标",
                   "command_cn": "设定目标", "title": "设定储蓄目标",
                   "subtitle": "采集确认 · 写入 goals.json"},
    "saving":     {"scene_id": "goal_saving_status", "wake_word": "看目标",
                   "command_cn": "看目标", "title": "查看目标进度",
                   "subtitle": "已存/目标/百分比/预计达成日"},
}

# 模式 → 模板文件(隔离契约内 · 与 scenes/goal.yaml html.template 对齐)
MODE_TEMPLATE = {
    "set-budget": "budget_form.html",
    "budget":     "budget_view.html",
    "set-saving": "saving_form.html",
    "saving":     "saving_view.html",
}

# 模式 → 输出文件名(中文 command)
MODE_CN = {"set-budget": "设定预算", "budget": "看预算",
           "set-saving": "设定目标", "saving": "看目标"}


def run_cli_json(mode: str, extra_args: list) -> dict:
    """调用 goal/cli.py <mode> --json <extra>…,解析 JSON 输出"""
    cli = _SCRIPT_DIR / "cli.py"
    cmd = [sys.executable, str(cli), mode, "--json"] + list(extra_args)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", env=env, timeout=30)
    except subprocess.TimeoutExpired:
        return {"status": "error", "data": None, "message": f"CLI 调用超时(30s): {' '.join(cmd)}"}
    except FileNotFoundError as e:
        return {"status": "error", "data": None, "message": f"找不到 CLI: {e}"}

    if result.returncode != 0 and not result.stdout.strip():
        return {"status": "error", "data": None,
                "message": f"CLI 调用失败(exit={result.returncode}): {result.stderr.strip() or '(无 stderr)'}"}
    out = result.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        return {"status": "error", "data": None,
                "message": f"CLI 输出不是合法 JSON: {e} | 原始输出: {out[:200]}"}


def _meta(mode: str, extra_args: list) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    m = GOAL_META[mode]
    return {
        "scene_id": m["scene_id"], "command_cn": m["command_cn"],
        "wake_word": m["wake_word"], "occurred_at": now,
        "chain": "(未注入 · AI 可在日志覆盖)",
        "render_cmd": f"goal/render.py {mode} {' '.join(extra_args)}".strip(),
        "version": SKILL_VERSION,
    }


def build_form_payload(mode: str, fields: dict, extra_args: list,
                       existing: dict | None = None) -> dict:
    """采集型 payload:form.fields + existing(同月同类预算冲突提示)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    m = GOAL_META[mode]
    data = {
        "type": mode, "title": m["title"], "subtitle": m["subtitle"],
        "generated_at": now,
        "meta": _meta(mode, extra_args),
        "form": {"type": mode, "fields": fields, "existing": existing},
    }
    return {"status": "ok", "data": data, "message": f"{m['command_cn']} 采集"}


def build_view_payload(mode: str, cli_json: dict, extra_args: list) -> dict:
    """结果型 payload:CLI 数据 + type/title/subtitle/meta(复制数据/日志数据源)"""
    if cli_json.get("status") == "error":
        return {"status": "error", "data": None,
                "message": cli_json.get("message", "未知错误")}
    m = GOAL_META[mode]
    data = dict(cli_json.get("data") or {})
    data["type"] = mode
    data["title"] = m["title"]
    data["subtitle"] = m["subtitle"]
    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["meta"] = _meta(mode, extra_args)
    return {"status": "ok", "data": data, "message": cli_json.get("message", "")}


def inject_to_template(payload: dict, mode: str, output_path: Path) -> Path:
    """注入 payload 到 目标/<模板>,写文件(utf-8-sig BOM)"""
    template_path = TEMPLATES_DIR / MODE_TEMPLATE[mode]
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    old = '<script id="payload" type="application/json">{"status":"empty","data":null,"message":"数据未注入"}</script>'
    new = f'<script id="payload" type="application/json">{payload_json}</script>'
    if old not in template:
        raise RuntimeError("模板中找不到 payload 注入点(<script id=\"payload\" ...>)")

    html = template.replace(old, new, 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8-sig")
    return output_path


def default_output_path(mode: str) -> Path:
    """默认输出路径:$DATA_DIR/biscuit_accountant_html/<设定预算|看预算|设定目标|看目标>_<TS>.html"""
    from html_paths import html_path
    return html_path(MODE_CN[mode])


def _find_existing_budget(fields: dict) -> dict | None:
    """采集前查同月同类预算(冲突提示数据源)"""
    month = fields.get("month") or ""
    category = fields.get("category") or ""
    if not month:
        return None
    cli_json = run_cli_json("budget", ["--month", month])
    if cli_json.get("status") != "ok":
        return None
    for b in cli_json.get("data", {}).get("budgets", []):
        if (b.get("category") or "") == category:
            return b
    return None


def main():
    parser = argparse.ArgumentParser(
        description="饼干记账 · 目标域 HTML 渲染器(4 场景)",
        usage="python3 scripts/goal/render.py <mode> [args...] [--out <path>]"
    )
    parser.add_argument("mode", choices=list(GOAL_META.keys()),
                        help="set-budget | budget | set-saving | saving")
    parser.add_argument("--out", default=None, help="输出 HTML 路径(默认 $DATA_DIR/biscuit_accountant_html/)")

    args, extra = parser.parse_known_args()
    # 处理 --out 被透传的可能
    cleaned_extra = []
    skip_next = False
    for i, a in enumerate(extra):
        if skip_next:
            skip_next = False
            continue
        if a == "--out":
            skip_next = True
            continue
        cleaned_extra.append(a)
    extra = cleaned_extra

    def _field(flag: str, default: str = "") -> str:
        if flag in extra:
            return extra[extra.index(flag) + 1]
        return default

    print(f"📥 渲染目标域: {args.mode}")
    print(f"   参数: {' '.join(extra) if extra else '(无)'}")

    try:
        if args.mode in ("set-budget", "set-saving"):
            # 采集型:由 AI 把已解析字段透传,表单回显 + 冲突提示
            fields = {}
            if args.mode == "set-budget":
                fields = {"amount": _field("--amount"), "month": _field("--month"),
                          "category": _field("--category")}
                existing = _find_existing_budget(fields)
            else:
                fields = {"name": _field("--name"), "amount": _field("--amount"),
                          "deadline": _field("--deadline")}
                existing = None
            payload = build_form_payload(args.mode, fields, extra, existing)
        else:
            # 结果型:调 CLI 拿 JSON
            cli_json = run_cli_json(args.mode, extra)
            payload = build_view_payload(args.mode, cli_json, extra)
    except ValueError as e:
        print(f"✗ 参数错误：{e}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.out) if args.out else default_output_path(args.mode)
    try:
        final = inject_to_template(payload, args.mode, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"✗ 注入失败：{e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ 已生成: {final}")
    print(f"  用浏览器打开即可查看。")
    sys.exit(0)


if __name__ == "__main__":
    main()
