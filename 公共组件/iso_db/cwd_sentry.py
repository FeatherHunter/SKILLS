# -*- coding: utf-8 -*-
"""iso_db cwd sentry · #404 L3 cwd 哨兵 + opt-in 机制

检测 cwd 是否在 .scratch/ 下 或 脚本名以 demo_/scratch_/_demo 开头 → 自动临时
opt-out: CALORIE_FORCE_PROD=1 env → 强制生产

可被卡路里 scripts/db.py 的 find_db_path 直接调用(import 复用,不重复实现)。
"""
from __future__ import annotations
import atexit
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


_SCRATCH_SENTINEL = ".scratch"
_DEMO_PREFIXES = ("demo_", "scratch_", "_demo")
_FORCE_PROD_ENV = "CALORIE_FORCE_PROD"

# 已隔离的临时目录集合(进程退出时统一清理 · #404 对抗审查:防 %TEMP% 残留)
_ISOLATED_DIRS: set[str] = set()


def _cleanup_isolated_dirs():
    import shutil
    for d in list(_ISOLATED_DIRS):
        shutil.rmtree(d, ignore_errors=True)
    _ISOLATED_DIRS.clear()


atexit.register(_cleanup_isolated_dirs)

# 已知生产 DB 目录候选(#400 对抗审查 C5):env 指向其中任一且 cwd 是 demo 路径时,
# 哨兵仍须隔离——否则用户 shell 持久生产 env 会让 demo 路径直写生产(事故场景)。
_KNOWN_PROD_DIRS = [
    Path("D:/2Study/StudyNotes/.db"),   # 本仓库主生产库目录
    Path("D:/.db"),                     # find_db_path fallback(Windows)
    Path("/mnt/d/.db"),                 # WSL fallback
    Path("/mnt/d/2Study/StudyNotes/.db"),  # WSL 主生产
    Path.home() / ".db",               # macOS/Linux fallback
]


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


def env_points_to_known_prod() -> bool:
    """SKILLS_DB_PATH 是否指向已知生产 DB 目录(C5 修复:生产 env 不得豁免 demo 隔离)"""
    env = os.environ.get("SKILLS_DB_PATH", "")
    if not env:
        return False
    try:
        p = Path(env).resolve()
    except Exception:
        return False
    return any(str(p) == str(d.resolve()) for d in _KNOWN_PROD_DIRS)


def ensure_isolation(verbose: bool = True) -> Optional[Path]:
    """demo 路径下自动 setenv SKILLS_DB_PATH → mktemp.

    返回 temp dir 路径,或 None (= 不隔离,生产路径生效)。
    调用方应在 scripts/*.db.py 的 find_db_path 内调用本函数。

    决策顺序(#400 对抗审查 C5 修正):
      1. CALORIE_FORCE_PROD=1 → 强制生产,不隔离
      2. cwd 非 demo → 不隔离(真实调用路径)
      3. cwd 是 demo:
         - env 已设且**非生产**(调用方显式自定义隔离) → 尊重,不重复覆盖
         - env 已设且**指向生产** → 仍隔离(用户 shell 持久生产 env 不豁免 demo)
         - env 未设 → 自动 mktemp
    """
    if force_prod_enabled():
        if verbose:
            print(f"[{_FORCE_PROD_ENV}=1] 强制生产路径生效,不隔离")
        return None
    if not is_demo_path():
        return None
    if "SKILLS_DB_PATH" in os.environ and not env_points_to_known_prod():
        # caller 已显式设非生产路径(自定义 temp),不重复覆盖
        return None
    tmp = Path(tempfile.mkdtemp(prefix="iso_db_demo_"))
    os.environ["SKILLS_DB_PATH"] = str(tmp)
    _ISOLATED_DIRS.add(str(tmp))  # 进程退出清理
    if verbose:
        print(f"[iso_db] demo path detected; isolated to {tmp}")
    return tmp


def detect_and_set() -> Optional[Path]:
    """顶层入口: 给 scripts/db.py 的 find_db_path 调。

    返回隔离后的 db dir,或 None (= 不隔离,生产路径)。
    """
    return ensure_isolation(verbose=True)
