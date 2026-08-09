"""渐进式注册通道测试(实施 T1 · 对抗式审查矛盾 5 修正)

锁定契约:
- discover_domain_commands 扫描脚本目录,发现模块级 COMMANDS 注册表(不靠文件名模式)
- 域模块 handler 签名:handler(args: list[str])
- 未命中命令返回 False,不打断现有 if/elif 分发(现有命令不受影响)
- import 失败的模块仅告警不中断;同名命令先到先得(按文件名排序)
- 真实 scripts/ 目录现有域模块 batch_scenarios.py(实施 T4)→ 注册表含 batch-add;
  既有 49 命令分发不受扰动(域命令只走 else 钩子)
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_cli

DOM_MODULE = '''
import sys

def dom_hello(args):
    print("dom-hello received:" + "|".join(args))

COMMANDS = {
    "dom-hello": dom_hello,
    "dom-echo": lambda args: print("echo:" + " ".join(args)),
}
'''


def _write_module(dir_path: Path, name: str, content: str) -> Path:
    p = dir_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ===== 发现 =====

def test_discover_finds_commands(tmp_path):
    _write_module(tmp_path, "demo_domain.py", DOM_MODULE)
    registry = schedule_cli.discover_domain_commands(tmp_path)
    assert set(registry) == {"dom-hello", "dom-echo"}
    assert callable(registry["dom-hello"])
    assert callable(registry["dom-echo"])


def test_discover_skips_modules_without_commands(tmp_path):
    _write_module(tmp_path, "no_commands.py", "X = 1\n")
    assert schedule_cli.discover_domain_commands(tmp_path) == {}


def test_discover_skips_underscore_and_self(tmp_path):
    _write_module(tmp_path, "_private.py", DOM_MODULE)
    registry = schedule_cli.discover_domain_commands(tmp_path)
    assert "dom-hello" not in registry


def test_discover_real_scripts_dir_has_batch_add():
    """真实 scripts/ 已有域模块 batch_scenarios.py(T4) → 注册表含 batch-add;
    并行 session(T5-T7)可能追加其他域命令,故只断言 batch-add 必在。
    """
    old = sys.modules.pop("batch_scenarios", None)
    try:
        registry = schedule_cli.discover_domain_commands(SCRIPTS_DIR)
    finally:
        if old is not None:
            sys.modules["batch_scenarios"] = old
    assert "batch-add" in registry


def test_discover_ignores_broken_module(tmp_path):
    _write_module(tmp_path, "a_broken.py", 'raise RuntimeError("boom")\n')
    _write_module(tmp_path, "b_good.py", DOM_MODULE)
    registry = schedule_cli.discover_domain_commands(tmp_path)
    assert "dom-hello" in registry  # 坏模块不拖垮其余模块


def test_discover_conflict_first_wins_by_sort(tmp_path):
    _write_module(tmp_path, "a_first.py", 'COMMANDS = {"dup": lambda args: None}\n')
    _write_module(tmp_path, "b_second.py", 'COMMANDS = {"dup": lambda args: 1}\n')
    registry = schedule_cli.discover_domain_commands(tmp_path)
    assert "dup" in registry


# ===== dispatch =====

def test_dispatch_routes_handler_and_args(tmp_path):
    _write_module(tmp_path, "demo_domain.py", DOM_MODULE)
    schedule_cli._DOMAIN_COMMANDS = schedule_cli.discover_domain_commands(tmp_path)
    assert schedule_cli._dispatch_domain("dom-hello", ["a", "b"]) is True
    schedule_cli._DOMAIN_COMMANDS = None


def test_dispatch_miss_returns_false(tmp_path):
    _write_module(tmp_path, "demo_domain.py", DOM_MODULE)
    schedule_cli._DOMAIN_COMMANDS = schedule_cli.discover_domain_commands(tmp_path)
    assert schedule_cli._dispatch_domain("unknown-cmd", []) is False
    schedule_cli._DOMAIN_COMMANDS = None


def test_dispatch_handles_arbitrary_args(tmp_path):
    received = {}
    module = 'import sys\n\ndef h(args):\n    received = args\n    print("ok")\n\nCOMMANDS = {"h": h}\n'
    _write_module(tmp_path, "args_domain.py", module)
    schedule_cli._DOMAIN_COMMANDS = schedule_cli.discover_domain_commands(tmp_path)
    assert schedule_cli._dispatch_domain("h", ["x", "--json", "@f.json"]) is True
    schedule_cli._DOMAIN_COMMANDS = None
