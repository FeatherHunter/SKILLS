#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_cwd_sentry_integration.py — #404 L3 cwd 哨兵集成验收

验证 卡路里/scripts/db.py 接入 cwd 哨兵后的三个验收场景:
  1. demo 路径(.scratch/ 或 demo_/scratch_/_demo 脚本名)→ 自动隔离到 temp + 打印 🔒
  2. CALORIE_FORCE_PROD=1 → 绕过哨兵走生产 + 打印 ⚠️
  3. 正常调用(仓库根 + 普通脚本名)→ 不拦截不警告

用 subprocess 跑真实 python(cwd/argv 可控),验证隔离行为与输出。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PROD_DIR = Path(r"D:\2Study\StudyNotes\.db")


def _run_python(cwd: Path, argv0: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """在指定 cwd + argv0 下跑真实 python,返回 CompletedProcess

    argv0: 通过 sys.argv[0] 在子进程内设置(cwd 哨兵检测脚本名前缀)。
    """
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(PROD_DIR)  # 模拟用户 shell 持久生产 env
    env.pop("CALORIE_FORCE_PROD", None)
    if extra_env:
        env.update(extra_env)
    scripts_esc = str(SCRIPTS_DIR).replace("\\", "\\\\")
    skill_esc = str(SKILL_DIR).replace("\\", "\\\\")
    argv0_esc = argv0.replace("\\", "\\\\")
    code = (
        "import sys; "
        f"sys.argv = [r'{argv0_esc}']; "
        f"sys.path.insert(0, r'{scripts_esc}'); "
        "import db; from pathlib import Path; "
        f"print(db.find_db_path(Path(r'{skill_esc}')))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    return proc


def test_demo_in_scratch_isolated(tmp_path):
    """.scratch/ 子目录跑 scripts/*.py → 解析到 temp,stdout 含 🔒 已自动隔离"""
    scratch = tmp_path / ".scratch" / "demo"
    scratch.mkdir(parents=True)
    proc = _run_python(scratch, "demo_render_meal.py")
    assert proc.returncode == 0, f"exit={proc.returncode} stderr={proc.stderr}"
    # stdout 含隔离提示
    assert "🔒 已自动隔离到" in proc.stdout + proc.stderr + proc.stderr + proc.stderr, f"缺隔离提示: out={proc.stdout} err={proc.stderr}"
    # 解析到 temp(非生产)
    resolved = proc.stdout.strip().splitlines()[-1]
    assert resolved != str(PROD_DIR / "calorie_data.db"), f"应隔离到 temp,却解析到生产: {resolved}"
    assert "iso_db_demo_" in resolved, f"解析路径不像哨兵 temp: {resolved}"


def test_demo_by_script_name(tmp_path):
    """脚本名 demo_ 前缀(即使 cwd 正常)→ 隔离"""
    proc = _run_python(tmp_path, "demo_render_meal.py")
    assert proc.returncode == 0, proc.stderr
    assert "🔒 已自动隔离到" in proc.stdout + proc.stderr
    resolved = proc.stdout.strip().splitlines()[-1]
    assert "iso_db_demo_" in resolved


def test_force_prod_bypass_sentry(tmp_path):
    """CALORIE_FORCE_PROD=1 时 cwd 哨兵失效 → 解析到生产 + ⚠️ 警告"""
    scratch = tmp_path / ".scratch" / "prod"
    scratch.mkdir(parents=True)
    proc = _run_python(scratch, "demo_x.py", extra_env={"CALORIE_FORCE_PROD": "1"})
    assert proc.returncode == 0, proc.stderr
    assert "⚠️ CALORIE_FORCE_PROD=1" in proc.stdout + proc.stderr, f"缺 FORCE_PROD 警告: out={proc.stdout} err={proc.stderr}"
    resolved = proc.stdout.strip().splitlines()[-1]
    assert resolved == str(PROD_DIR / "calorie_data.db"), f"FORCE_PROD 应走生产: {resolved}"


def test_normal_call_unaffected():
    """仓库根目录正常调用 → 不拦截不警告,走 env 生产"""
    proc = _run_python(SKILL_DIR.parent, "calorie_tracker.py")
    assert proc.returncode == 0, proc.stderr
    # 无隔离/警告输出(仅解析路径)
    assert "🔒" not in proc.stdout + proc.stderr, f"正常调用不应隔离: {proc.stdout}"
    assert "⚠️" not in proc.stdout + proc.stderr, f"正常调用不应警告: {proc.stdout}"
    resolved = proc.stdout.strip().splitlines()[-1]
    assert resolved == str(PROD_DIR / "calorie_data.db"), f"正常调用应走 env 生产: {resolved}"


def test_non_demo_path_not_isolated(tmp_path):
    """非 .scratch/ 目录 + 正常脚本名 → 不隔离"""
    proc = _run_python(tmp_path, "weight.py")
    assert proc.returncode == 0, proc.stderr
    assert "🔒" not in proc.stdout + proc.stderr, f"非 demo 不应隔离: {proc.stdout}"
    resolved = proc.stdout.strip().splitlines()[-1]
    assert resolved == str(PROD_DIR / "calorie_data.db"), f"应走 env: {resolved}"


def test_demo_isolation_dir_cleaned_after_exit(tmp_path):
    """M2 对抗审查:demo 隔离目录在子进程退出后已被 atexit 清理(防 %TEMP% 泄漏)

    子进程内隔离到 iso_db_demo_* 目录 → 进程正常退出(atexit 触发)→
    父进程侧断言该目录已消失。
    """
    scratch = tmp_path / ".scratch" / "demo"
    scratch.mkdir(parents=True)
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(PROD_DIR)
    env.pop("CALORIE_FORCE_PROD", None)
    scripts_esc = str(SCRIPTS_DIR).replace("\\", "\\\\")
    skill_esc = str(SKILL_DIR).replace("\\", "\\\\")
    code = (
        "import sys; "
        f"sys.argv = [r'demo_cleanup_check.py']; "
        f"sys.path.insert(0, r'{scripts_esc}'); "
        "import db; from pathlib import Path; "
        f"r = db.find_db_path(Path(r'{skill_esc}')); "
        "import os; print(os.environ.get('SKILLS_DB_PATH', ''))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(scratch), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    isolated = proc.stdout.strip().splitlines()[-1]
    assert isolated and "iso_db_demo_" in isolated, f"未隔离: {isolated}"
    isolated_dir = Path(isolated)
    # 子进程已退出(atexit 应清理),父进程侧断言目录消失
    assert not isolated_dir.exists(), f"隔离目录未被 atexit 清理: {isolated_dir}"
