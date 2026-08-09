# cli.py - 私家大厨 · 搜索筛选域(search)CLI 入口
# 命令: search(关键词/排除/维度筛选·7 字段) / suggest(错字纠错候选) / list-all(查看全部)
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

from 搜索筛选 import ops


def _emit(payload, exit_ok=0):
    print(json.dumps(payload, ensure_ascii=False))
    return exit_ok if payload.get("status") == "ok" else 1


def _common_search_args(sub):
    sub.add_argument("keyword", nargs="?", default="", metavar="<关键词>", help="菜名/食材关键词(可空=全部)")
    sub.add_argument("--exclude", action="append", default=[], help="排除食材/口味(可多次;不吃/不要/忌 X)")
    sub.add_argument("--cuisine", default="", help="菜系筛选(川/粤/湘,LIKE)")
    sub.add_argument("--time-max", default="", help="时间上限(分钟)")
    sub.add_argument("--difficulty", default="", help="难度(简单/快手菜,可逗号多值)")
    sub.add_argument("--status", default="", help="状态(未做/已做/熟练,可逗号多值)")
    sub.add_argument("--cookware", default="", help="炊具筛选(砂锅/高压锅,LIKE)")
    sub.add_argument("--flavor", default="", help="口味筛选(辣/甜/鲜,LIKE)")
    sub.add_argument("--season", default="", help="季节筛选(春/夏/秋/冬,LIKE)")
    sub.add_argument("--sort", choices=["rating", "updated", "name"], default="rating",
                     help="排序: rating(评分降序·默认)/ updated(更新时间倒序)/ name")


def _filters_from_args(a) -> dict:
    return {
        "cuisine": a.cuisine, "time_max": a.time_max, "difficulty": a.difficulty,
        "status": a.status, "cookware": a.cookware, "flavor": a.flavor, "season": a.season,
    }


def main():
    parser = argparse.ArgumentParser(
        description="私家大厨 · 搜索筛选域(search): 7 字段检索/排除/维度筛选/错字纠错",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    p_search = sub.add_parser("search", help="搜索/筛选(检索契约 7 字段,支持排除与维度组合)")
    _common_search_args(p_search)

    p_suggest = sub.add_parser("suggest", help="无结果时的错字纠错候选(同音/形近)")
    p_suggest.add_argument("keyword", metavar="<关键词>", help="未命中的关键词")
    p_suggest.add_argument("--limit", type=int, default=5, help="候选上限(默认 5)")

    p_list = sub.add_parser("list-all", help="查看全部(search-13): 全部未废弃菜")
    p_list.add_argument("--sort", choices=["rating", "updated", "name"], default="updated",
                        help="排序(默认 updated=更新时间倒序)")
    p_list.add_argument("--exclude", action="append", default=[], help="排除食材/口味(可多次)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "search":
        filters = _filters_from_args(args)
        results = ops.search_recipes(
            keyword=args.keyword or "",
            exclude=[x for x in args.exclude if x.strip()],
            filters=filters,
            sort=args.sort,
        )
        return _emit({
            "status": "ok",
            "keyword": args.keyword or "",
            "exclude": [x for x in args.exclude if x.strip()],
            "filters": filters,
            "sort": args.sort,
            "count": len(results),
            "results": results,
        })

    if args.command == "suggest":
        suggestions = ops.suggest(args.keyword, limit=args.limit)
        return _emit({
            "status": "ok",
            "keyword": args.keyword,
            "count": len(suggestions),
            "suggestions": suggestions,
        })

    if args.command == "list-all":
        results = ops.list_all_recipes(sort=args.sort)
        return _emit({
            "status": "ok",
            "exclude": [x for x in args.exclude if x.strip()],
            "sort": args.sort,
            "count": len(results),
            "results": results,
        })
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
