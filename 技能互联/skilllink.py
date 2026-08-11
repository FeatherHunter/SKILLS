#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能互联 · skilllink-read 命令真身（Base 提供 · #274 试点落地）

契约: docs/契约规范-v1.md（#272 定稿 · 2026-08-11 用户逐条拍板）
形态: 命令真身住本 Base；各技能只放 PUBLIC_DOMAINS.py 注册表（§8）。

用法:
  python skilllink.py --skill 作息管家 --what
  python skilllink.py --skill 作息管家 --domain sleep --from 2026-08-01 --to 2026-08-10

统一信封（§5）:
  {
    "ok": true|false,          # 办成了
    "skill": "作息管家",        # 来自哪个技能
    "domain": "sleep",         # 查的什么
    "meta": {"start":..,"end":..,"generated_at":..},   # 查询情况
    "data": [ {...}, ... ],    # 真正数据（一行一条）
    "error": "...",            # 失败时（§6 降级语义）
    "domains": ["..."]         # 域不存在时的现有域清单（§6 AI 自救）
  }

--what 输出（§7 问能力）:
  { "ok": true, "skill": "...", "meta": {"generated_at":..},
    "domains": [ {"name":.., "cn":.., "desc":.., "fields":[...] } ] }

执行者 = AI（§2）：AI 读契约 → 调本命令 → 理解/合并 → 注入 HTML。
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_REGISTRY = BASE_DIR / "skill_registry.yaml"


def _err(msg: str) -> dict:
    return {"ok": False, "skill": None, "domain": None,
            "meta": {"generated_at": datetime.now().isoformat(timespec="seconds")},
            "data": [], "error": msg}


def _load_registry(registry_path: Path) -> dict:
    with open(registry_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("skills", {})


def _skill_dir(entry: dict) -> Path:
    """技能目录：registry path 相对仓库根；绝对路径直接使用（测试 --registry 指向 tmp）"""
    p = Path(entry["path"])
    return p if p.is_absolute() else REPO_ROOT / p


def load_domains(skill: str, entry: dict) -> tuple[dict | None, str | None]:
    """import 技能 PUBLIC_DOMAINS.py，返回 (PUBLIC_DOMAINS, error)。

    错误语义（§6）：
      - 技能没接入（找不到注册表文件）→ error='未接入'
      - import 失败 → error=具体原因
    """
    skill_dir = _skill_dir(entry)
    module_name = entry.get("module", "PUBLIC_DOMAINS")
    mod_file = skill_dir / f"{module_name}.py"
    if not mod_file.exists():
        return None, f"未接入（{skill} 没有 {module_name}.py 注册表）"
    sys.path.insert(0, str(skill_dir))
    sys.modules.pop(module_name, None)  # 防模块缓存：每次重新 import（多技能目录共用模块名）
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        return None, f"命令执行出错: {type(e).__name__}: {e}"
    domains = getattr(mod, "PUBLIC_DOMAINS", None)
    if not isinstance(domains, dict):
        return None, f"未接入（{skill} 的 PUBLIC_DOMAINS 注册表无效）"
    return domains, None


def cmd_what(skill: str, entry: dict) -> dict:
    """--what：问「你能提供什么」→ 输出注册表（§7）"""
    domains, error = load_domains(skill, entry)
    if error:
        return _err(error)
    return {
        "ok": True,
        "skill": skill,
        "meta": {"generated_at": datetime.now().isoformat(timespec="seconds")},
        "domains": [
            {
                "name": name,
                "cn": d.get("name", name),
                "desc": d.get("desc", ""),
                "fields": d.get("fields", []),
            }
            for name, d in domains.items()
        ],
    }


def cmd_read(skill: str, entry: dict, domain: str, start: str, end: str) -> dict:
    """--domain：实际查数据 → 统一信封（§5/§6）"""
    domains, error = load_domains(skill, entry)
    if error:
        return _err(error)
    if domain not in domains:
        # §6 无此域 → 错误 + 现有域清单（AI 看清单改问正确域·自救路径）
        return {
            "ok": False,
            "skill": skill,
            "domain": domain,
            "meta": {"start": start, "end": end,
                     "generated_at": datetime.now().isoformat(timespec="seconds")},
            "data": [],
            "error": f"没有这个域（{domain}）",
            "domains": list(domains.keys()),
        }
    fetch = domains[domain].get("fetch")
    if not callable(fetch):
        return _err(f"命令执行出错: 域 {domain} 未提供 fetch 取数函数")
    try:
        data = fetch(start, end) or []
    except Exception as e:
        return {
            "ok": False,
            "skill": skill,
            "domain": domain,
            "meta": {"start": start, "end": end,
                     "generated_at": datetime.now().isoformat(timespec="seconds")},
            "data": [],
            "error": f"命令执行出错: {type(e).__name__}: {e}",
        }
    return {
        "ok": True,
        "skill": skill,
        "domain": domain,
        "meta": {"start": start, "end": end,
                 "generated_at": datetime.now().isoformat(timespec="seconds")},
        "data": data,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skilllink-read",
        description="技能互联 · 跨技能数据契约层命令（Base 提供 · 契约 v1）",
    )
    parser.add_argument("--skill", required=True, help="技能名（注册表里的键，如 作息管家）")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="注册表路径（默认技能互联/skill_registry.yaml）")
    parser.add_argument("--what", action="store_true", help="问能力：输出该技能注册表")
    parser.add_argument("--domain", help="查的域（如 sleep）")
    parser.add_argument("--from", dest="from_", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--to", help="结束日期 YYYY-MM-DD")
    args = parser.parse_args(argv)

    try:
        registry = _load_registry(Path(args.registry))
    except Exception as e:
        print(json.dumps(_err(f"注册表加载失败: {type(e).__name__}: {e}"),
                         ensure_ascii=False))
        return 1

    entry = registry.get(args.skill)
    if not entry:
        # §6 对方没接入互联 → 错误（降级：告知用户 / 尝试对方唤醒词对话式查）
        result = {
            "ok": False,
            "skill": args.skill,
            "domain": None,
            "meta": {"generated_at": datetime.now().isoformat(timespec="seconds")},
            "data": [],
            "error": f"未接入（注册表无 {args.skill}）",
            "skills": list(registry.keys()),
        }
        print(json.dumps(result, ensure_ascii=False))
        return 1

    if args.what:
        result = cmd_what(args.skill, entry)
    elif args.domain:
        if not args.from_ or not args.to:
            result = _err("查数据需要 --from 与 --to（YYYY-MM-DD）")
            print(json.dumps(result, ensure_ascii=False))
            return 1
        result = cmd_read(args.skill, entry, args.domain, args.from_, args.to)
    else:
        result = _err("缺少参数：--what 或 --domain（+--from/--to）")
        print(json.dumps(result, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
