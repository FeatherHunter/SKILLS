# cli.py - SM8 开始使用域 CLI 入口
# 命令: check(环境检测) / init-status(初始化状态) / init(建库+建分类)
#       lint(数据检查) / backup(备份) / backup-list / backup-delete / export / import-preview / import
# 输出: 结构化 JSON(08 规范 · 原则 1 CLI 阻塞)
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
        description="居家管家 · 开始使用域(SM8):初始化/数据检查/备份导出/导入恢复",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    sub.add_parser("check", help="环境检测(OS/Python/目录可写)")
    sub.add_parser("init-status", help="初始化状态(幂等判定)")

    p_init = sub.add_parser("init", help="初始化:建库(幂等)+ 建分类种子(幂等)")
    p_init.add_argument("--seed-file", default=None, help="种子文件路径(默认 references/seed_categories.yaml)")

    p_lint = sub.add_parser("lint", help="数据检查(8 检查项)")
    p_lint.add_argument("--days-status", default=None, help="状态时效阈值 JSON,如 '{\"快递中\":7}'")

    sub.add_parser("backup", help="备份:db+照片全量打包(保留 N 份)")
    p_bl = sub.add_parser("backup-list", help="备份历史列表")
    p_bl.add_argument("--keep-n", type=int, default=None, help="保留份数(默认 5)")
    p_bd = sub.add_parser("backup-delete", help="删除旧备份(确认式)")
    p_bd.add_argument("--file", required=True, help="备份文件名(home_backup_*.zip)")

    p_ex = sub.add_parser("export", help="导出:JSON(全表)/CSV(便携)")
    p_ex.add_argument("--format", default="json", choices=["json", "csv"], help="导出格式")
    p_ex.add_argument("--output", default=None, help="输出路径(默认 backups/ 目录)")

    p_ip = sub.add_parser("import-preview", help="导入校验 + 冲突预览")
    p_ip.add_argument("--file", required=True, help="导入文件(JSON 导出/备份)")
    p_ie = sub.add_parser("import", help="确认导入(导入前自动备份,失败回滚)")
    p_ie.add_argument("--file", required=True, help="导入文件(JSON 导出/备份)")
    p_ie.add_argument("--mode", default="skip", choices=["skip", "overwrite"],
                      help="同名冲突处理:skip=跳过(默认) / overwrite=覆盖")
    p_ie.add_argument("--no-backup", action="store_true", help="跳过导入前自动备份")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "check":
        return _emit(ops.env_check_payload())
    if args.command == "init-status":
        return _emit(ops.init_status_payload())
    if args.command == "init":
        return _emit(ops.init_db_and_seed(seed_file=args.seed_file))
    if args.command == "lint":
        days = None
        if args.days_status:
            try:
                days = json.loads(args.days_status)
            except json.JSONDecodeError:
                days = None
        return _emit(ops.lint_health_payload(days_status=days))
    if args.command == "backup":
        return _emit(ops.backup_payload())
    if args.command == "backup-list":
        return _emit(ops.backup_list_payload(keep_n=args.keep_n or ops.BACKUP_KEEP_N))
    if args.command == "backup-delete":
        return _emit(ops.delete_backup_payload(args.file))
    if args.command == "export":
        return _emit(ops.export_payload(fmt=args.format, output_path=args.output))
    if args.command == "import-preview":
        return _emit(ops.import_preview_payload(args.file))
    if args.command == "import":
        return _emit(ops.import_execute_payload(
            args.file, mode=args.mode, auto_backup=not args.no_backup))
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
