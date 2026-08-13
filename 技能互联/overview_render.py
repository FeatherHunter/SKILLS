#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能互联 · 互联总览渲染器（#276）

职责: 读 skill_registry.yaml（已接入登记簿）→ 对目标技能逐个探测接入状态
（与 check_public_contract 同口径）→ 组织 payload（公共组件信封）→
公共组件注入管线（INJECT-DATA / SHARED-HELPERS / SHARED-CSS 硬拦截）→
落盘 $SKILLS_DB_PATH/skilllink_html/技能互联_HELP_<YYYYMMDD>_<HHMMSS>.html。

状态判定（#276 · 与 #273 校验器同口径）:
  connected（绿 · statusBadge ok）: registry 已登记 + PUBLIC_DOMAINS.py 存在
                                     + skilllink.py --what 跑通（契约一致）
  pending（灰 · statusBadge empty）: 未登记 —— 公开「还没接」状态，促使开发时补上
  broken（红 · statusBadge danger）: 已登记但缺注册表 / 契约失效 —— 校验器会在
                                     commit 前拦住的 drift，正常仓库不应出现；出现即公示

红线: 本脚本不执行任何 fetch / 不碰任何 .db 文件（数据库隔离红线 · AGENTS.md）。
只做: yaml 读取 + 注册表 import + --what 子进程（--what 不执行 fetch，天然安全）。
--what 输出里的 domains 即「该技能能提供什么域」——总览页直接展示。

用法:
  python overview_render.py                          # 默认输出 + 默认 registry
  python overview_render.py --out X.html             # 指定输出（测试用）
  python overview_render.py --registry <yaml> --repo-root <root>   # 测试用
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_REGISTRY = BASE_DIR / "skill_registry.yaml"
INJECTOR_DIR = REPO_ROOT / "公共组件"
TEMPLATE_PATH = BASE_DIR / "templates" / "overview.html"

# 目标技能（map #270 Destination 定死的 6 技能 · 本 map 范围）
# 未登记 = 灰显「还没接」，接入时在 skill_registry.yaml 补行即自动变绿。
TARGET_SKILLS = ["卡路里", "饼干记账", "作息管家", "居家管家", "备忘录", "私家大厨"]


def _db_base_dir() -> Path:
    """统一 DB 基目录（Q6 链: SKILLS_DB_PATH env > 平台 fallback）。

    HTML 输出与其它技能 HELP 同约定（作息管家 schedule_html/ · 饼干记账
    biscuit_accountant_html/）——只写 HTML 视图文件，绝不碰 .db 数据文件。
    """
    env_path = os.environ.get("SKILLS_DB_PATH")
    if env_path:
        return Path(env_path)
    if sys.platform == "win32":
        return Path("D:/") / ".db"
    return Path.home() / ".local" / "share" / "schedule-guardian" / "db"


def default_out_path() -> Path:
    """默认输出路径: $SKILLS_DB_PATH/skilllink_html/技能互联_HELP_<TS>[_N].html

    命名对标跨技能 HELP 约定（{技能名}_HELP_<YYYYMMDD>_<HHMMSS>.html ·
    作息管家/饼干记账同款），同秒冲突保护 _2/_3。
    """
    command = "技能互联_HELP"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = _db_base_dir() / "skilllink_html"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{command}_{stamp}.html"
    if not target.exists():
        return target
    n = 2
    while n < 1000:
        candidate = base / f"{command}_{stamp}_{n}.html"
        if not candidate.exists():
            return candidate
        n += 1
    raise RuntimeError(f"冲突保护超过 1000 次: {command}_{stamp}")


def _load_registry(registry_path: Path) -> dict:
    """读 registry；空登记簿 = {}（尚无技能接入，合法状态）。"""
    import yaml

    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    skills = data.get("skills")
    if skills is None:
        return {}
    return skills if isinstance(skills, dict) else {}


def _skill_dir(entry: dict, repo_root: Path) -> Path:
    """技能目录：registry path 相对仓库根；绝对路径直接使用（测试 --registry 指向 tmp）"""
    p = Path(entry["path"])
    return p if p.is_absolute() else repo_root / p


def probe_skill(skill: str, entry: dict, registry_path: Path, repo_root: Path) -> dict:
    """逐技能探测接入状态（与 check_public_contract 同口径）。

    返回: {status: connected|broken, reason?, domains?}
    domains = --what 输出的域清单 [{name, cn, desc, fields}]。
    """
    skill_dir = _skill_dir(entry, repo_root)
    module_name = entry.get("module", "PUBLIC_DOMAINS")
    mod_file = skill_dir / f"{module_name}.py"
    if not mod_file.exists():
        return {
            "status": "broken",
            "reason": f"已登记但缺 {module_name}.py（登记 = 承诺提供数据，未兑现）",
        }
    # --what 端到端（不执行 fetch，天然安全）；与校验器 B.7 同款子进程约定
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(
            [sys.executable, str(BASE_DIR / "skilllink.py"), "--skill", skill,
             "--registry", str(registry_path), "--what"],
            cwd=str(BASE_DIR), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, timeout=30,
        )
    except Exception as e:
        return {"status": "broken", "reason": f"--what 子进程启动失败: {type(e).__name__}: {e}"}
    if r.returncode != 0:
        tail = (r.stdout or r.stderr or "").strip().splitlines()
        return {"status": "broken",
                "reason": f"--what exit={r.returncode}: {tail[-1] if tail else '无输出'}"}
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"status": "broken", "reason": "--what 输出非 JSON"}
    if not out.get("ok"):
        return {"status": "broken", "reason": f"--what ok=false: {out.get('error', '无 error')}"}
    domains = [
        {"name": d.get("name", ""), "cn": d.get("cn", ""), "desc": d.get("desc", ""),
         "fields": d.get("fields", [])}
        for d in out.get("domains", [])
    ]
    return {"status": "connected", "domains": domains}


def build_payload(skills: list[dict], registry_path: Path) -> dict:
    """技能状态列表 → 公共组件信封 payload（契约 §4 + scene.snapshot）。

    snapshot 为纯文本镜像（复制场景用）; overview.skills 为结构化真源（页面渲染用）。
    """
    connected = [s for s in skills if s["status"] == "connected"]
    broken = [s for s in skills if s["status"] == "broken"]
    total_domains = sum(len(s.get("domains", [])) for s in connected)
    now = datetime.now().isoformat(timespec="seconds")

    summary = [
        f"{len(connected)}/{len(skills)} 技能已接入 · 可用域 {total_domains} 个",
        f"生成时间 {now}",
    ]
    sections = []
    if connected:
        sections.append({"heading": "已接入（绿）", "rows": [
            f"{s['name']} · 域: {' / '.join(d['cn'] for d in s['domains'])}" for s in connected]})
    pending = [s for s in skills if s["status"] == "pending"]
    if pending:
        sections.append({"heading": "未接入（灰 · 待开发接入）", "rows": [s["name"] for s in pending]})
    if broken:
        sections.append({"heading": "登记异常（红 · 需修复）", "rows": [
            f"{s['name']}: {s['reason']}" for s in broken]})

    return {
        "status": "ok",
        "data": {
            "meta": {
                "command_cn": "技能互联 · 互联总览",
                "occurred_at": now,
                "skill_name": "技能互联",
                "wake_word": "互联总览",
            },
            "scene": {
                "scene_id": "overview",
                "snapshot": {
                    "title": "技能互联 · 接入状态总览",
                    "summary": summary,
                    "sections": sections,
                },
                "buttons": [],
            },
            "overview": {
                "generated_at": now,
                "registry": str(registry_path),
                "target_total": len(skills),
                "connected_count": len(connected),
                "pending_count": len(pending),
                "broken_count": len(broken),
                "domain_count": total_domains,
                "skills": skills,
            },
            "copy_log": {
                "thinking": "互联总览: 逐技能判定接入状态（登记 + PUBLIC_DOMAINS.py + --what 跑通），"
                            "灰显未接入技能促使开发时补上。",
                "data_structure": f"skills[{len(skills)}]{{name,status,domains[{total_domains}]}}",
                "call_chain": "overview_render → skill_registry.yaml + skilllink --what（不执行 fetch）",
                "timestamp": now,
                "exception": "",
            },
        },
    }


def render(out_path: Path, registry_path: Path, repo_root: Path) -> dict:
    """主渲染: registry 探测 → payload → 注入管线 → 落盘。返回三段式 {status, data, message}。"""
    registry = _load_registry(registry_path)

    skills = []
    for name in TARGET_SKILLS:
        entry = registry.get(name)
        if not entry:
            skills.append({"name": name, "status": "pending",
                           "reason": "未接入 · 开发联动时在 skill_registry.yaml 登记"})
            continue
        item = probe_skill(name, entry, registry_path, repo_root)
        item["name"] = name
        skills.append(item)

    payload = build_payload(skills, registry_path)

    # ── 注入管线（公共组件 · 硬拦截占位符校验）──
    if not TEMPLATE_PATH.exists():
        return {"status": "error", "data": None,
                "message": f"模板不存在: {TEMPLATE_PATH}"}
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 公共组件资产按「脚本所在仓库」解析（对齐作息管家 help_render _load_base_assets）：
    # registry 的 repo-root 只用于技能路径基准（测试可指向 tmp），Base 资产不动。
    injector_dir = REPO_ROOT / "公共组件"
    js_path = injector_dir / "assets" / "base.js"
    css_path = injector_dir / "assets" / "base.css"
    if not js_path.exists() or not css_path.exists():
        return {"status": "error", "data": None,
                "message": f"公共组件资产缺失: {js_path} / {css_path}（先装本基础包）"}
    sys.path.insert(0, str(injector_dir))
    import injector  # noqa: E402

    html, err = injector.inject(
        template_text, payload,
        js_asset=js_path.read_text(encoding="utf-8").strip(),
        css_asset=css_path.read_text(encoding="utf-8").strip(),
        strict=True,
    )
    if err:
        return {"status": "error", "data": None, "message": f"注入失败: {err}"}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    p = payload["data"]["overview"]
    return {
        "status": "ok",
        "data": {
            "file_path": str(out_path),
            "size_kb": size_kb,
            "connected_count": p["connected_count"],
            "pending_count": p["pending_count"],
            "broken_count": p["broken_count"],
            "domain_count": p["domain_count"],
        },
        "message": (
            f"✓ 互联总览已生成: 已接入 {p['connected_count']}/{p['target_total']} · "
            f"可用域 {p['domain_count']} 个 · 未接入 {p['pending_count']} · "
            f"登记异常 {p['broken_count']} ({size_kb} KB)"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="overview_render",
                                     description="技能互联 · 互联总览渲染器（#276）")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（默认 $SKILLS_DB_PATH/skilllink_html/技能互联_HELP_<TS>.html）")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="登记簿路径（默认 技能互联/skill_registry.yaml）")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="仓库根（registry 相对路径基准；测试指向 tmp）")
    args = parser.parse_args(argv)

    out_path = Path(args.out) if args.out else default_out_path()
    result = render(out_path, Path(args.registry), Path(args.repo_root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    # Windows GBK 控制台兜底：输出统一 UTF-8（对齐仓库 _io_guard 精神 · #242）
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
