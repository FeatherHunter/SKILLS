# -*- coding: utf-8 -*-
"""iso_db cwd sentry · #404 L3 cwd 哨兵 + opt-in 机制

检测 cwd 是否在 .scratch/ 下 或 脚本名以 demo_/scratch_/_demo 开头 → 自动临时
opt-out: CALORIE_FORCE_PROD=1 env → 强制生产

可被卡路里 scripts/db.py 的 find_db_path 直接调用(import 复用,不重复实现)。
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


_SCRATCH_SENTINEL = ".scratch"
_DEMO_PREFIXES = ("demo_", "scratch_", "_demo")
_FORCE_PROD_ENV = "CALORIE_FORCE_PROD"


def is_demo_path() -> bool:
    """检测 cwd 是否在 .scratch/ 下 或 脚本名以 demo_/scratch_/_demo 开头"""
    try:
        cwd = Path.cwd()
        if _SCRATCH_SENTINEL in cwd.parts:
            return True
    except Exception:
        pass
    script = sys.argv[0] if sys.argv else ""
    name = Path(script).name if script else ""
    return any(name.startswith(p) for p in _DEMO_PREFIXES)


def force_prod_enabled() -> bool:
    """检测 opt-out env CALORIE_FORCE_PROD=1"""
    return os.environ.get(_FORCE_PROD_ENV) == "1"


def ensure_isolation(verbose: bool = True) -> Optional[Path]:
    """demo 路径下自动 setenv SKILLS_DB_PATH → mktemp.

    返回 temp dir 路径,或 None (= 不隔离,生产路径生效)。
    调用方应在 scripts/*.db.py 的 find_db_path 内调用本函数。

    决策顺序:
      1. CALORIE_FORCE_PROD=1 → 强制生产,不隔离
      2. cwd 非 demo → 不隔离(真实调用路径)
      3. cwd 是 demo → 自动 mktemp
    """
    if force_prod_enabled():
        if verbose:
            print(f"[{_FORCE_PROD_ENV}=1] 强制生产路径生效,不隔离")
        return None
    if not is_demo_path():
        return None
    if "SKILLS_DB_PATH" in os.environ:
        # caller 已设,不重复覆盖
        return None
    tmp = Path(tempfile.mkdtemp(prefix="iso_db_demo_"))
    os.environ["SKILLS_DB_PATH"] = str(tmp)
    if verbose:
        print(f"[iso_db] demo path detected; isolated to {tmp}")
    return tmp


def detect_and_set() -> Optional[Path]:
    """顶层入口: 给 scripts/db.py 的 find_db_path 调。

    返回隔离后的 db dir,或 None (= 不隔离,生产路径)。
    """
    return ensure_isolation(verbose=True)
