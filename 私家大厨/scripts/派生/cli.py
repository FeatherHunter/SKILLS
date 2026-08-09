# cli.py - 私家大厨 · 派生域(relation)CLI 入口
# 命令: mother(母本读取)/ derive-commit(同事务写库·rel-3)/ tree(家族树·rel-2)
# 输出: 结构化 JSON(08 规范 · 原则 1 CLI 阻塞;AI 解析执行)
# rel-1 添加派生关系沿用 relation_manager.py add(底层已具备,不重复造)
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

from 派生 import ops


def _emit(payload, exit_ok=0):
    print(json.dumps(payload, ensure_ascii=False))
    return exit_ok if payload.get("status") in ("ok", "success") else 1


def main():
    parser = argparse.ArgumentParser(
        description="私家大厨 · 派生域(relation): 母本读取/同事务派生/家族树",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    p_mother = sub.add_parser("mother", help="rel-3 母本读取: 拉母本全字段(导入契约)")
    p_mother.add_argument("name", metavar="<菜名或ID>", help="母本菜名或 ID(不存在/已废弃 → 拒绝)")

    p_tree = sub.add_parser("tree", help="rel-2 家族树: 根=当前菜,向上祖先/向下后代")
    p_tree.add_argument("name", metavar="<菜名或ID>", help="当前菜名或 ID")

    p_commit = sub.add_parser("derive-commit", help="rel-3 同事务写库: 新菜谱+派生关系一次建成")
    p_commit.add_argument("payload", metavar="<payload.json>", help="JSON 文件: {recipe, parent_name, relation_type, change_summary}")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "mother":
        try:
            mother = ops.get_mother(args.name)
        except ValueError as e:
            return _emit({"status": "error", "error": "mother_rejected", "message": str(e)}, 1)
        summary = {
            "name": mother.get("name"),
            "difficulty": mother.get("difficulty"),
            "servings": mother.get("servings"),
            "total_time": mother.get("total_time"),
            "status": mother.get("status"),
            "description": mother.get("description"),
        }
        return _emit({"status": "ok", "mother": mother, "mother_summary": summary,
                      "message": f"母本读取完成:「{summary['name']}」"})

    if args.command == "tree":
        tree = ops.relation_tree(args.name)
        if not tree["found"]:
            return _emit({"status": "error", "error": "recipe_not_found",
                          "message": f"未找到食谱「{args.name}」(或已废弃)", "tree": tree}, 1)
        return _emit({"status": "ok", "tree": tree,
                      "message": f"家族树组装完成: 根=「{tree['root']['name']}」· {tree['count']} 个关联"})

    if args.command == "derive-commit":
        try:
            with open(args.payload, "r", encoding="utf-8-sig") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return _emit({"status": "error", "error": "payload_invalid",
                          "message": f"payload 加载失败: {e}"}, 1)
        result = ops.derive_commit(payload)
        return _emit(result, 0 if result.get("status") == "success" else 1)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
