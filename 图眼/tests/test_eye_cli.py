# -*- coding: utf-8 -*-
"""CLI 结构测试:不调网络;只验证 argparse 契约与错误路径。"""
import os
import subprocess
import sys

import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
EYE = os.path.join(SCRIPTS, "eye.py")

# 保证中文路径/参数走列表传参
def run(*args):
    return subprocess.run([sys.executable, EYE, *args],
                          capture_output=True, text=True, encoding="utf-8")


def test_help_exits_zero():
    r = run("--help")
    assert r.returncode == 0
    for cmd in ("look", "scan", "ocr", "ask", "audit"):
        assert cmd in r.stdout


def test_each_subcommand_has_help():
    for cmd in ("look", "scan", "ocr", "ask", "audit"):
        r = run(cmd, "--help")
        assert r.returncode == 0, f"{cmd} --help 失败: {r.stderr}"


def test_missing_command_fails():
    r = run()
    assert r.returncode != 0


def test_missing_image_fails():
    r = run("look")
    assert r.returncode != 0
    r = run("scan")
    assert r.returncode != 0


def test_nonexistent_image_errors(tmp_path):
    """早失败:图片不存在 → 非零退出 + stderr 有字段信息。"""
    fake = str(tmp_path / "不存在.png")
    r = run("look", "--image", fake)
    assert r.returncode != 0
    assert "图片不存在" in r.stderr
    assert fake in r.stderr


def test_ask_requires_question():
    r = run("ask", "--image", "x.png")
    assert r.returncode != 0
    assert "--question" in r.stderr or "required" in r.stderr


def test_brain_choices_validated():
    r = run("ask", "--image", "x.png", "--question", "q", "--brain", "gpt5")
    assert r.returncode != 0
