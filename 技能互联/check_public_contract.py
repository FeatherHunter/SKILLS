#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_public_contract.py — 技能互联 · 公开数据契约校验器（#273）

守护目标（第一性原理，2026-08-11 用户拍板 D1-D5）:
  技能互联的「真相」散在 3 处：技能侧注册表（PUBLIC_DOMAINS.py）· Base 侧登记簿
  （skill_registry.yaml）· 消费侧组合表（combos.yaml，v1.1 待 #275 落库后接入）。
  本校验器 = commit 前静态闸门：在 drift 进主线前拦住，而不是等用户触发联动时
  才由 skilllink 运行时兜底报错。

检查项（v1.0 · 提供方契约守卫）:
  A. 反向扫描（文件 → 登记）: 仓库根一级目录有 PUBLIC_DOMAINS.py 但未在
     skill_registry.yaml 登记 → 红（半接入悬空态，skilllink 按登记簿查不到）
  B. 正向校验（登记 → 文件/结构）: registry 每个技能必须满足
     1. 技能目录存在
     2. PUBLIC_DOMAINS.py 存在（复用 skilllink.load_domains，与运行时同一套加载逻辑）
     3. PUBLIC_DOMAINS 是 dict
     4. 每域必含: name / desc / fields(list) / fetch(callable)
     5. 每字段必含: name / type / unit / desc；type ∈ {date, number, text, text_free}
        （机器标识枚举 · #273 D4 拍板 · 契约 v1 §4 补注）
     6. fetch 签名可绑定 (start, end)（inspect 静态验，**绝不调用 fetch**——
        调用 = 碰技能 DB，可能碰生产库 · 数据库隔离红线 / #257 事故教训）
     7. `skilllink.py --skill <技能> --what` 子进程跑通（exit 0 + ok=true，
        端到端验证 import + 序列化；--what 不执行 fetch，天然安全）

红线: 本校验器只做静态契约检查，不执行任何 fetch / 不碰任何 DB。

用法:
    python check_public_contract.py
    python check_public_contract.py --registry <path> --repo-root <path>   # 测试用
    # 退出码: 0 = 一致, 1 = 有 drift

后续（v1.1 · #275 组合表落库后接入）: 以 combos.yaml 为输入，验「引用技能 ∈
registry + 引用域 ∈ 该技能注册表 + 引用字段 ⊆ fields」（消费方需求 ⊆ 提供方能力）。
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_REGISTRY = BASE_DIR / "skill_registry.yaml"

# 字段类型机器标识枚举（#273 D4 拍板 · 契约 v1 §4 四类）:
#   date 日期 / number 数字 / text 文字 / text_free 自由文本（黑盒，AI 读 + 用户确认）
VALID_FIELD_TYPES = {"date", "number", "text", "text_free"}


def _load_registry(registry_path: Path) -> dict | None:
    """读 registry；失败返回 None（调用方记红）"""
    try:
        import yaml

        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return None
    if not isinstance(data, dict):
        return None
    skills = data.get("skills")
    if skills is None:
        # 空登记簿（`skills:` 无条目）= 尚无技能接入，合法状态——反向扫描仍要工作
        return {}
    return skills if isinstance(skills, dict) else None


def _skill_dir(entry: dict, repo_root: Path) -> Path:
    """技能目录：registry path 相对仓库根；绝对路径直接使用（测试 --registry 指向 tmp）"""
    p = Path(entry["path"])
    return p if p.is_absolute() else repo_root / p


def scan_unregistered(repo_root: Path, registry: dict, issues: list[str]) -> None:
    """A. 反向扫描：仓库根一级目录有 PUBLIC_DOMAINS.py 但未登记 → 红

    跳过以 `.` 开头的目录（.git / .scratch / .worktrees / .pytest_cache 等噪音）。
    技能目录都在仓库根一级（6 技能均为一级目录），深层不扫（子模块会引入噪音）。
    """
    found = []
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / "PUBLIC_DOMAINS.py").is_file():
            found.append(child.name)
    unregistered = [name for name in found if name not in registry]
    if unregistered:
        issues.append(
            f"[反向·有注册表未登记] {len(unregistered)} 个技能目录有 PUBLIC_DOMAINS.py "
            f"但未在 skill_registry.yaml 登记（半接入悬空态 · skilllink 查不到）:"
        )
        for name in sorted(unregistered):
            issues.append(f"  - {name}（正在接入请先登记；废弃请删除文件）")


def validate_domain_structure(domains: dict, skill: str, issues: list[str]) -> None:
    """B.4/B.5/B.6 结构断言：每域/每字段必填 + type 枚举 + fetch 可调"""
    prefix = f"[结构·{skill}]"
    for name, d in sorted(domains.items()):
        # 域级必填
        for field in ("name", "desc"):
            if not isinstance(d.get(field), str) or not d[field].strip():
                issues.append(f"{prefix} 域 {name} 缺非空 {field}（契约 v1 §3）")
        fields = d.get("fields")
        if not isinstance(fields, list):
            issues.append(f"{prefix} 域 {name} 的 fields 必须是列表")
            fields = []
        # 字段级必填 + type 枚举
        for i, f in enumerate(fields):
            if not isinstance(f, dict):
                issues.append(f"{prefix} 域 {name} 第 {i + 1} 个字段不是对象")
                continue
            for fk in ("name", "type", "unit", "desc"):
                if not isinstance(f.get(fk), str):
                    issues.append(f"{prefix} 域 {name} 字段 #{i + 1} 缺 {fk}（契约 v1 §3）")
            ftype = f.get("type")
            if isinstance(ftype, str) and ftype not in VALID_FIELD_TYPES:
                issues.append(
                    f"{prefix} 域 {name} 字段 #{i + 1} type={ftype!r} 不在枚举 "
                    f"{sorted(VALID_FIELD_TYPES)}（#273 D4 · 契约 v1 §4 机器标识）"
                )
        # fetch 可调用 + 签名 (start, end)
        fetch = d.get("fetch")
        if not callable(fetch):
            issues.append(f"{prefix} 域 {name} 缺可调用 fetch(start, end)（契约 v1 §8）")
            continue
        try:
            inspect.signature(fetch).bind(None, None)
        except TypeError:
            issues.append(f"{prefix} 域 {name} fetch 签名须为 (start, end)（#273 静态验，不执行）")


def check_what_runs(skill: str, registry_path: Path, issues: list[str]) -> None:
    """B.7 端到端：skilllink.py --skill <技能> --what 跑通（exit 0 + ok=true）

    --what 不执行 fetch（只 import + 序列化注册表），天然不碰 DB。
    子进程设 PYTHONIOENCODING=utf-8，规避 Windows GBK 控制台编码崩。
    """
    script = BASE_DIR / "skilllink.py"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(
            [sys.executable, str(script), "--skill", skill,
             "--registry", str(registry_path), "--what"],
            cwd=str(BASE_DIR), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, timeout=30,
        )
    except Exception as e:
        issues.append(f"[--what·{skill}] 子进程启动失败: {type(e).__name__}: {e}")
        return
    if r.returncode != 0:
        tail = (r.stdout or r.stderr or "").strip().splitlines()
        issues.append(f"[--what·{skill}] skilllink --what exit={r.returncode}: {tail[-1] if tail else '无输出'}")
        return
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        issues.append(f"[--what·{skill}] 输出非 JSON: {r.stdout[:200]}")
        return
    if not out.get("ok"):
        issues.append(f"[--what·{skill}] ok=false: {out.get('error', '无 error 字段')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_public_contract",
        description="技能互联 · 公开数据契约校验器（#273 · commit 前静态闸门）",
    )
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY),
                        help="登记簿路径（默认 技能互联/skill_registry.yaml）")
    parser.add_argument("--repo-root", default=str(REPO_ROOT),
                        help="仓库根（反向扫描基准；测试指向 tmp）")
    args = parser.parse_args(argv)

    registry_path = Path(args.registry)
    repo_root = Path(args.repo_root)
    issues: list[str] = []

    # 加载登记簿
    registry = _load_registry(registry_path)
    if registry is None:
        print(f"⚠ 登记簿加载失败: {registry_path}")
        sys.exit(1)
    print(f"登记簿技能数: {len(registry)}")

    # A. 反向：有注册表未登记
    scan_unregistered(repo_root, registry, issues)

    # B. 正向：登记技能逐个校验
    sys.path.insert(0, str(BASE_DIR))
    import skilllink

    for skill, entry in sorted(registry.items()):
        skill_dir = _skill_dir(entry, repo_root)
        if not skill_dir.is_dir():
            issues.append(f"[正向·{skill}] 技能目录不存在: {skill_dir}")
            continue
        mod_file = skill_dir / "PUBLIC_DOMAINS.py"
        if not mod_file.exists():
            issues.append(
                f"[正向·{skill}] 已登记但缺 PUBLIC_DOMAINS.py（登记 = 承诺提供数据，"
                f"未兑现必须红 · #273 D5）——接入中请先补注册表，或从登记簿移除"
            )
            continue
        domains, error = skilllink.load_domains(skill, entry)
        if error:
            issues.append(f"[正向·{skill}] 注册表加载失败: {error}")
            continue
        validate_domain_structure(domains, skill, issues)
        check_what_runs(skill, registry_path, issues)

    # 汇总
    print(f"反向扫描发现 PUBLIC_DOMAINS.py 目录: ", end="")
    pub_dirs = [
        c.name for c in sorted(repo_root.iterdir())
        if c.is_dir() and not c.name.startswith(".") and (c / "PUBLIC_DOMAINS.py").is_file()
    ]
    print(len(pub_dirs))

    if not issues:
        print("✅ 全部已接入技能契约一致（登记 ↔ 注册表双向兑现 + 结构合规 + --what 跑通）")
        return 0

    n_classes = sum(1 for x in issues if x.startswith("["))
    print(f"⚠ 发现 {n_classes} 类 drift:")
    for x in issues:
        print(x)
    return 1


if __name__ == "__main__":
    # Windows GBK 控制台兜底：输出统一 UTF-8（对齐仓库 _io_guard 精神 · #242）
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
