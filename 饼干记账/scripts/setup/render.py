#!/usr/bin/env python3
"""饼干记账 · 开始使用域 HTML 渲染器(6 场景 · scenes/setup.yaml)

交互契约(yaml type):
    首次使用向导(向导)   → init_wizard.html(4 步零决策:环境检测→目录确认→建库→验证;
                           完成页「记第一笔」引导按钮)
    初始化状态(查看)     → init_status.html(三重判定卡:存在/schema/版本 + 迁移提示)
    一键备份(回执)       → backup.html(备份回执:路径/时间/内容)
    查看备份(查看)       → backup_list.html(备份列表:时间/大小/内容;空态引导一键备份)
    从备份恢复(向导)     → restore.html(备份详情预览→确认→恢复→验证)
    导入 CSV(向导)       → import.html(列映射:前几行预览 + 自动猜测映射可改)

meta.scene_id/wake_word/command_cn 对齐 scenes/setup.yaml(门禁 A 层 1 数据源)。

用法:
    python3 scripts/setup/render.py init-wizard
    python3 scripts/setup/render.py init-status
    python3 scripts/setup/render.py backup-create
    python3 scripts/setup/render.py backup-list
    python3 scripts/setup/render.py restore [--name X]
    python3 scripts/setup/render.py import --file x.csv

输出:默认 $DATA_DIR/biscuit_accountant_html/<中文名>_<TS>.html(§12.A,可用 --out 指定)
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).resolve().parent
_SCRIPTS = _SCRIPT_DIR.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# #300 Base 管线共享层:统一信封 + Base 注入器 + utf-8-sig BOM
from _base_render import envelope, error_envelope, inject_base, write_html

SKILL_DIR = _SCRIPTS.parent
TEMPLATES = SKILL_DIR / "templates" / "开始使用"
SKILL_VERSION = "2.0"

SCENE_META = {
    "init-wizard":   {"scene_id": "setup_init_wizard",   "wake_word": "初始化",
                      "command_cn": "初始化向导", "template": "init_wizard.html", "cn": "初始化向导"},
    "init-status":   {"scene_id": "setup_init_status",   "wake_word": "初始化状态",
                      "command_cn": "初始化状态", "template": "init_status.html", "cn": "初始化状态"},
    "backup-create": {"scene_id": "setup_backup_create", "wake_word": "备份",
                      "command_cn": "一键备份", "template": "backup.html", "cn": "一键备份"},
    "backup-list":   {"scene_id": "setup_backup_list",   "wake_word": "备份",
                      "command_cn": "查看备份", "template": "backup_list.html", "cn": "查看备份"},
    "restore":       {"scene_id": "setup_restore",       "wake_word": "恢复备份",
                      "command_cn": "从备份恢复", "template": "restore.html", "cn": "从备份恢复"},
    "import":        {"scene_id": "setup_import",        "wake_word": "导入",
                      "command_cn": "导入CSV", "template": "import.html", "cn": "导入CSV"},
}

# 恢复向导:备份列表数据源 = backup-list;导入向导:预览数据源 = import --preview
CLI_SUBCMD = {
    "init-wizard":   ("init", ["--check"]),
    "init-status":   ("init-status", []),
    "backup-create": ("backup-create", []),
    "backup-list":   ("backup-list", []),
    "restore":       ("backup-list", []),
    "import":        ("import", ["--preview"]),
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_cli_json(subcmd: str, extra_args: list) -> dict:
    """调用 setup/cli.py <subcmd> --json <extra>…,解析 JSON 输出"""
    cli = _SCRIPT_DIR / "cli.py"
    cmd = [sys.executable, str(cli), subcmd, "--json"] + list(extra_args)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", env=env, timeout=60)
    except subprocess.TimeoutExpired:
        return {"status": "error", "data": None, "message": f"CLI 调用超时(60s): {' '.join(cmd)}"}
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


def _meta(mode: str, render_cmd: str) -> dict:
    m = SCENE_META[mode]
    now = _now()
    return {
        "scene_id": m["scene_id"],
        "wake_word": m["wake_word"],
        "command_cn": m["command_cn"],
        "occurred_at": now,
        "chain": "(未注入 · AI 可在日志覆盖)",
        "render_cmd": render_cmd,
        "version": SKILL_VERSION,
    }


def _write_html(payload: dict, mode: str, out_arg: str = None) -> Path:
    template_path = TEMPLATES / SCENE_META[mode]["template"]
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    html = inject_base(template, payload)
    from html_paths import html_path
    out = Path(out_arg) if out_arg else html_path(SCENE_META[mode]["cn"])
    return write_html(html, out)


# ── 首次使用向导(4 步零决策 · 完成页「记第一笔」引导) ─────────────────────────

def build_init_wizard_payload() -> dict:
    cli_json = run_cli_json("init", ["--check"])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "环境检测失败")}

    cli = cli_json.get("data") or {}
    env = cli.get("env") or {}
    st = cli.get("status") or {}
    ready = bool(st.get("ready"))
    now = _now()

    steps = []
    for s in cli.get("steps") or []:
        steps.append({
            "name": s["step"], "status": s["status"],
            "detail": s["detail"], "done": s["status"] == "ok",
        })
    if not ready:
        steps += [
            {"name": "建库(幂等自愈)", "status": "pending",
             "detail": "自动创建数据库与表结构,重复执行安全", "done": False},
            {"name": "只读验证", "status": "pending",
             "detail": "校验表结构完整、可正常读取", "done": False},
        ]
    else:
        steps = steps[:2] + [
            {"name": "建库(幂等自愈)", "status": "ok",
             "detail": "数据库已就绪", "done": True},
            {"name": "只读验证", "status": "ok",
             "detail": f"schema v2.0 完整 · 现有记录 {st.get('records', 0)} 条", "done": True},
        ]

    data = {
        "type": "init-wizard",
        "title": "首次使用向导",
        "subtitle": "4 步零决策 · 自动检测 · 一次成功",
        "generated_at": now,
        "meta": _meta("init-wizard", "setup/render.py init-wizard"),
        "ready": ready,
        "db_path": st.get("db_path", ""),
        "records": st.get("records", 0),
        "env": env,
        "status": st,
        "steps": steps,
    }
    # #300 统一信封
    envelope(data, "初始化向导", "初始化", "setup_init_wizard",
             "setup/render.py init-wizard",
             [f"就绪 {ready} · 数据库 {st.get('db_path', '')} · 现有记录 {st.get('records', 0)} 条"],
             [{"heading": "检测步骤", "rows": [
                 f"{s['name']} · {s['status']} · {s['detail']}" for s in steps
             ]}],
             data_structure="biscuit_accountant.db（幂等自愈建库 · 只读验证）")
    return {"status": "ok", "data": data, "message": "初始化向导" if not ready else "初始化完成"}


# ── 初始化状态(三重判定) ─────────────────────────────────────────────────────

def build_init_status_payload() -> dict:
    cli_json = run_cli_json("init-status", [])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "初始化状态查询失败")}
    cli = cli_json.get("data") or {}
    now = _now()
    data = dict(cli)
    data["type"] = "init-status"
    data["title"] = "初始化状态"
    data["subtitle"] = "就绪" if cli.get("ready") else "未就绪 · 见下方引导"
    data["generated_at"] = now
    data["meta"] = _meta("init-status", "setup/render.py init-status")
    # #300 统一信封
    envelope(data, "初始化状态", "初始化状态", "setup_init_status",
             "setup/render.py init-status",
             [f"就绪 {cli.get('ready')}", f"数据库 {cli.get('db_path', '')}",
              f"schema {cli.get('schema_version', '')} · 记录 {cli.get('records', 0)} 条"],
             [{"heading": "三重判定", "rows": [
                 f"存在: {'是' if cli.get('exists') else '否'} · "
                 f"schema: {cli.get('schema_version') or '(缺失)'} · 就绪: {cli.get('ready')}"
             ]}],
             data_structure="biscuit_accountant.db（只读判定）")
    return {"status": "ok", "data": data, "message": cli_json.get("message", "初始化状态")}


# ── 一键备份(回执) ──────────────────────────────────────────────────────────

def build_backup_create_payload() -> dict:
    cli_json = run_cli_json("backup-create", [])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "一键备份失败")}
    cli = cli_json.get("data") or {}
    now = _now()
    data = dict(cli)
    data["type"] = "backup-create"
    data["title"] = "一键备份"
    data["subtitle"] = "数据库 + 目标(goals.json)已归档"
    data["generated_at"] = now
    data["meta"] = _meta("backup-create", "setup/render.py backup-create")
    # #300 统一信封
    envelope(data, "一键备份", "备份", "setup_backup_create",
             "setup/render.py backup-create",
             [f"备份路径 {cli.get('target', '')}", f"时间 {cli.get('time', '')}",
              f"内容 {cli.get('content', '')}"],
             [{"heading": "备份文件", "rows": [
                 f"{f.get('name')} {f.get('size', 0)} B" for f in (cli.get("files") or [])[:15]
             ]}],
             data_structure="备份目录（db + goals.json 副本 · 只写备份目录）")
    return {"status": "ok", "data": data, "message": cli_json.get("message", "一键备份完成")}


# ── 查看备份(列表 + 空态引导) ───────────────────────────────────────────────

def build_backup_list_payload() -> dict:
    cli_json = run_cli_json("backup-list", [])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "查看备份失败")}
    cli = cli_json.get("data") or {}
    now = _now()
    data = dict(cli)
    data["type"] = "backup-list"
    data["title"] = "查看备份"
    data["subtitle"] = f"共 {cli.get('count', 0)} 个备份"
    data["generated_at"] = now
    data["meta"] = _meta("backup-list", "setup/render.py backup-list")
    # #300 统一信封
    envelope(data, "查看备份", "备份", "setup_backup_list",
             "setup/render.py backup-list",
             [f"共 {cli.get('count', 0)} 个备份"],
             [{"heading": "备份列表", "rows": [
                 f"{b.get('name')} · {b.get('time', '')} · {b.get('size', 0)} B"
                 for b in (cli.get("backups") or [])[:15]
             ] or ["暂无备份 · 可一键备份"]}],
             data_structure="备份目录（只读列表）")
    return {"status": "ok", "data": data, "message": cli_json.get("message", "查看备份")}


# ── 从备份恢复(向导:详情预览→确认) ──────────────────────────────────────────

def build_restore_payload(name: str) -> dict:
    cli_json = run_cli_json("backup-list", [])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "恢复向导数据源失败")}
    backups = cli_json.get("data", {}).get("backups") or []
    if not backups:
        return {"status": "error", "data": None, "message": "暂无备份可恢复(先执行一键备份)"}

    # 选中项:显式 name > 默认最新
    selected = name if (name and any(b["name"] == name for b in backups)) else backups[0]["name"]
    detail = next((b for b in backups if b["name"] == selected), backups[0])

    now = _now()
    data = {
        "type": "restore",
        "title": "从备份恢复",
        "subtitle": "预览详情 → 确认 → 恢复 → 验证(恢复前自动备份现状)",
        "generated_at": now,
        "meta": _meta("restore", "setup/render.py restore"),
        "backups": backups,
        "selected": detail,
    }
    # #300 统一信封
    envelope(data, "从备份恢复", "恢复备份", "setup_restore", "setup/render.py restore",
             [f"选中备份 {detail.get('name')} · {detail.get('time', '')}",
              f"共 {len(backups)} 个可用备份"],
             [{"heading": "选中备份详情", "rows": [
                 f"{k}: {v}" for k, v in detail.items() if k not in ("files",)
             ]},
              {"heading": "全部备份", "rows": [
                  f"{b.get('name')} · {b.get('time', '')}" for b in backups[:15]
              ]}],
             data_structure="备份目录（恢复前自动备份现状 · 待确认后执行）")
    return {"status": "ok", "data": data, "message": "恢复向导 · 备份详情预览"}


# ── 导入 CSV(列映射向导) ────────────────────────────────────────────────────

def build_import_payload(file_arg: str) -> dict:
    if not (file_arg or "").strip():
        return {"status": "error", "data": None, "message": "缺少文件路径: 请先告知要导入的 CSV 文件路径"}
    cli_json = run_cli_json("import", ["--preview", "--file", file_arg.strip()])
    if cli_json.get("status") != "ok":
        return {"status": "error", "data": None, "message": cli_json.get("message", "CSV 解析失败")}
    cli = cli_json.get("data") or {}
    now = _now()
    data = dict(cli)
    data["type"] = "import"
    data["title"] = "导入 CSV 账单"
    data["subtitle"] = "列映射向导 · 前几行预览,映射可修改"
    data["generated_at"] = now
    data["meta"] = _meta("import", f"setup/render.py import --file {cli.get('name', '')}")
    # #300 统一信封
    envelope(data, "导入CSV", "导入", "setup_import",
             data["meta"]["render_cmd"],
             [f"文件 {cli.get('name', '')} · {cli.get('rows', 0)} 行",
              f"列 {cli.get('columns', [])}"],
             [{"heading": "预览(前几行)", "rows": [
                 str(r) for r in (cli.get("preview") or [])[:10]
             ] or ["(无预览)"]}],
             data_structure="CSV 文件（列映射预览 · 待确认后导入）")
    return {"status": "ok", "data": data, "message": "导入向导 · 列映射确认"}


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 开始使用域 HTML 渲染器")
    parser.add_argument("mode", choices=list(SCENE_META.keys()),
                        help="init-wizard | init-status | backup-create | backup-list | restore | import")
    parser.add_argument("--name", default=None, help="恢复备份名(选填,默认最新)")
    parser.add_argument("--file", default=None, help="CSV 文件路径(导入必填)")
    parser.add_argument("--out", default=None, help="输出路径")
    args = parser.parse_args()

    builders = {
        "init-wizard": lambda: build_init_wizard_payload(),
        "init-status": lambda: build_init_status_payload(),
        "backup-create": lambda: build_backup_create_payload(),
        "backup-list": lambda: build_backup_list_payload(),
        "restore": lambda: build_restore_payload(args.name or ""),
        "import": lambda: build_import_payload(args.file or ""),
    }
    payload = builders[args.mode]()
    # #300 错误信封:错误页也带 scene.snapshot(复制数据/日志按钮可用)
    if payload.get("status") == "error":
        payload = error_envelope(payload.get("message", "未知错误"), command_cn=SCENE_META[args.mode]["command_cn"])

    try:
        out = _write_html(payload, args.mode, args.out)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"✗ 注入失败：{e}", file=sys.stderr)
        sys.exit(1)

    if payload.get("status") == "error":
        print(f"⚠ 已生成错误页: {out}")
        print(f"  原因: {payload.get('message', '未知错误')}")
        return 0
    print(f"✓ 已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
