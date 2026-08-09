# cli.py - 私家大厨 · 开始使用域(setup-1 首次使用)CLI 入口
# 命令: check(环境检测) / install(自动安装命令) / env-config(持久化引导) / init(建库幂等)
# 输出: 结构化 JSON(08 规范 · 原则 1 CLI 阻塞;AI 解析执行)
import sys
import os
import json
import argparse

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

_scripts = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from 开始使用 import ops


def _emit(payload, exit_ok=0):
    print(json.dumps(payload, ensure_ascii=False))
    return exit_ok if payload.get("status") == "ok" else 1


def main():
    parser = argparse.ArgumentParser(
        description="私家大厨 · 开始使用域(setup-1): 首次使用 4 步向导底层工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    sub.add_parser("check", help="环境检测(OS/Python/pyyaml/DB 状态/目录可写)")
    sub.add_parser("install", help="自动安装命令(缺失时: 装前展示 → 确认 → 执行 → 重检)")
    sub.add_parser("env-config", help="环境变量持久化引导(Windows setx / Linux export)")
    sub.add_parser("init", help="建库(幂等: 老库 17 表跳过,空库/部分库补全)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "check":
        return _emit(ops.env_check_payload())
    if args.command == "install":
        return _emit(ops.install_cmds_payload())
    if args.command == "env-config":
        return _emit(ops.env_persist_payload())
    if args.command == "init":
        return _emit(ops.init_payload())
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
