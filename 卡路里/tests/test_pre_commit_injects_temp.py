#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_pre_commit_injects_temp.py — #402 L4 钩子隔离验收

验证 .githooks/pre-commit 注入 L4 测试隔离层:
  1. 钩子代码含强制 SKILLS_DB_PATH → mktemp 逻辑(静态)
  2. 模拟钩子运行:钩子内的 pytest 进程实际收到注入的 temp SKILLS_DB_PATH(动态)

动态测试用「假 python3」拦截钩子里的 pytest 调用(记录环境变量后退出 0),
避免真的跑全量测试;只验证注入这一层。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # SKILLS 仓库根
HOOK = REPO_ROOT / ".githooks" / "pre-commit"

_BASH = shutil.which("bash")


def _require_bash():
    if not _BASH:
        pytest.skip("无 bash(WSL/git-bash),跳过钩子动态测试")


# ---------------------------------------------------------------------------
# 1. 静态:钩子含 L4 注入块
# ---------------------------------------------------------------------------

def test_hook_has_l4_isolation_block():
    """钩子必须含 L4 隔离块:强制 SKILLS_DB_PATH → mktemp + trap 清理"""
    assert HOOK.exists(), f"找不到 .githooks/pre-commit: {HOOK}"
    text = HOOK.read_text(encoding="utf-8", errors="replace")

    assert "SKILLS_DB_PATH" in text, "钩子未涉及 SKILLS_DB_PATH"
    assert 'HOOK_TEMP_DIR_MSYS="$(mktemp -d)"' in text, "缺少 mktemp 注入"
    assert "cygpath -w" in text, "缺少 cygpath 转 Windows 路径(防 MSYS /tmp 误解析)"
    assert 'export SKILLS_DB_PATH="$HOOK_TEMP_DIR"' in text, "缺少 export"
    assert "trap cleanup_hook_temp EXIT" in text, "缺少 trap 清理"
    assert 'rm -rf "$HOOK_TEMP_DIR_MSYS"' in text, "缺少 mktemp 目录清理"


def test_hook_injects_before_pytest():
    """注入必须在 pytest 调用之前(否则隔离不生效)"""
    text = HOOK.read_text(encoding="utf-8", errors="replace")
    inject_pos = text.index("export SKILLS_DB_PATH")
    pytest_pos = text.index("python3 -m pytest")
    assert inject_pos < pytest_pos, (
        f"注入位置在 pytest 之后!inject@{inject_pos} > pytest@{pytest_pos}"
    )


# ---------------------------------------------------------------------------
# 2. 动态:假 python3 拦截,验证注入真实生效
# ---------------------------------------------------------------------------

def test_pre_commit_injects_temp(tmp_path):
    """模拟 .githooks/pre-commit 在临时仓库跑 → SKILLS_DB_PATH 已被注入到 mktemp

    端到端:临时 git 仓库真实 git commit,让 git 用自身 sh.exe(git-bash)
    调用真实 .githooks/pre-commit;钩子内的 pytest 用假 python3 拦截,
    记录收到的 SKILLS_DB_PATH 环境变量。

    构造:
      - 临时 git 仓库(git init + core.hooksPath=.githooks),复制真实钩子
      - 临时 bin/ 里放"假 python3"(bash 脚本):记录 env 到 env_dump.txt 后 exit 0
      - PATH 前置临时 bin → 钩子里的 python3 解析到假脚本
      - 制造卡路里改动 + git commit(触发 pre-commit)
    断言:
      - 假 python3 收到的 SKILLS_DB_PATH 是 mktemp 目录(非生产)
      - 该 mktemp 目录在钩子退出后已被 trap 清理
    """
    _require_bash()
    # 假 python3:记录 env 后退出 0(模拟 pytest 成功)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    env_dump = tmp_path / "env_dump.txt"
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        textwrap.dedent(f"""        #!/bin/bash
        # 只记录非空 SKILLS_DB_PATH 的调用(pre-commit 注入的);
        # commit-msg 钩子也会调 python3(格式检查),但那是独立进程无注入,
        # 记录空值会污染断言 —— 忽略它。
        if [ -n "$SKILLS_DB_PATH" ]; then
            echo "$SKILLS_DB_PATH" > "{env_dump.as_posix()}"
        fi
        exit 0
        """),
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    # 临时 git 仓库
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    # 与真实仓库一致:core.quotepath=false,否则 git diff 输出中文路径为 \345 字节转义,
    # 导致钩子 case 匹配失败(诊断:临时仓库默认 true 时 NEED_TEST 为空,钩子提前 exit)
    subprocess.run(["git", "config", "core.quotepath", "false"], cwd=repo, check=True)
    shutil.copytree(REPO_ROOT / ".githooks", repo / ".githooks")
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)

    # 制造卡路里改动(触发 NEED_TEST[卡路里]=1)
    cal_dir = repo / "卡路里"
    cal_dir.mkdir()
    # 钩子需要 $skill/tests 目录存在才跑 pytest
    (cal_dir / "tests").mkdir()
    (cal_dir / "x.py").write_text("x = 1\\n", encoding="utf-8")
    subprocess.run(["git", "add", "卡路里/x.py"], cwd=repo, check=True)

    # git commit 触发真实 pre-commit 钩子
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    # 清掉外部 SKILLS_DB_PATH,模拟"钩子必须自己注入"的语义
    env.pop("SKILLS_DB_PATH", None)

    # 合规 commit message: [技能名] 主题 + Tested-By 行(否则 commit-msg 钩子拒绝)
    msg = "[卡路里] 测试钩子注入 \u00b7 Tested-By: exempt(\u65e0 fresh agent)"
    proc = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )

    # 假 python3 必须被钩子调用(证明钩子跑了 pytest 路径并注入 env)
    assert env_dump.exists(), (
        f"假 python3 未被调用!commit stdout={proc.stdout} stderr={proc.stderr}"
    )
    injected = env_dump.read_text(encoding="utf-8").strip()
    assert injected, "SKILLS_DB_PATH 为空,注入未生效"

    # 注入的是 mktemp 目录,且是 Windows 原生路径(cygpath -w 转换,防 MSYS /tmp
    # 被 Windows python 误解析为 D:\\tmp 的对抗审查缺陷):
    # 1) 是 Windows 绝对路径(盘符:\\ 或 / 开头)  2) 非生产  3) 形如 mktemp
    assert re.match(r"^[A-Za-z]:[\\/]", injected) or injected.startswith("//"), (
        f"注入路径不是 Windows 绝对路径(cygpath 转换应生效): {injected}"
    )
    assert "iso_db" not in injected, (
        f"注入路径不应是 iso_db 前缀(L2 conftest 用的),而是钩子自己的 mktemp: {injected}"
    )
    name = injected.replace("\\", "/").rsplit("/", 1)[-1]
    assert name.startswith("tmp."), f"注入路径不像 mktemp: {injected}"

    # 钩子已退出,trap EXIT 应已清理 mktemp 目录(git-bash 里 rm MSYS 路径)
    if _BASH:
        msys_path = subprocess.run(
            [_BASH, "-c", f'cygpath -u "{injected}"'],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        if msys_path:
            gone = subprocess.run(
                [_BASH, "-c", f'test ! -d "{msys_path}" && echo gone || echo exists'],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            ).stdout.strip()
            assert gone == "gone", f"mktemp 目录未被 trap 清理: {injected} (msys: {msys_path})"
