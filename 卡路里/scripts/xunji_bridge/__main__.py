#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xunji_bridge CLI 入口。

8 个子命令:
    verify <动作名>...            校验动作名是否在训记官方库
    fetch --date YYYY-MM-DD       拉训记数据,纯 JSON 输出
    upsert --json <res[]>         训记 upsert API 原子封装(增/改,client_request_id 唯一性兜底)
    push-plan --date YYYY-MM-DD   推送当天的 plan 到训记(45s 限频,新建,localid=0)
    overlay-plan --date YYYY-MM-DD  覆盖当天的 plan 到训记(localid 已有,start/end=0)
    backfill --date YYYY-MM-DD    拉 + 写 exercise_log(幂等)
    key status|set|clear [--legacy]  KEY 管理
    run-sync --days N             后台串行 N 天同步训记(写状态文件)

用法示例:
    python scripts/xunji_bridge.py --help
    python scripts/xunji_bridge.py verify 哑铃弯举
    python scripts/xunji_bridge.py key status
    python scripts/xunji_bridge.py key set <YOUR_KEY>
    python scripts/xunji_bridge.py fetch --date 2026-07-13
    python scripts/xunji_bridge.py upsert --json '[{"datestr":"2026-07-13","localid":1783908000,...}]'
    python scripts/xunji_bridge.py upsert --json-file /tmp/res.json --dry-run
    python scripts/xunji_bridge.py backfill --date 2026-07-13
    python scripts/xunji_bridge.py backfill --days 2
    python scripts/xunji_bridge.py push-plan --date 2026-07-13 --dry-run
    python scripts/xunji_bridge.py overlay-plan --date 2026-07-13 --dry-run
    python scripts/xunji_bridge.py overlay-plan --date 2026-07-13

退出码:
    0  成功
    1  一般错误
    2  鉴权失败(无 KEY)
    3  API 报错
    4  校验失败(verify 有动作不在库)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import auth, catalog, fetch, upsert, push, overlay, backfill as backfill_mod, run_sync, errors
from . import __version__

EXIT_OK = 0
EXIT_ERR = 1
EXIT_AUTH = 2
EXIT_API = 3
EXIT_VERIFY = 4


def _print_json(data: dict) -> None:
    """统一 JSON 输出(保证中文不乱码、indent 友好)。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ── 子命令实现 ──────────────────────────────────────

def cmd_verify(args) -> int:
    if not args.names:
        print("用法:xunji_bridge.py verify <动作名> [<动作名> ...]", file=sys.stderr)
        return EXIT_ERR
    result = catalog.verify_many(args.names)
    _print_json(result)
    # 如果有任何不合法,退出码 = EXIT_VERIFY
    if result["invalid_count"] > 0:
        return EXIT_VERIFY
    return EXIT_OK


def cmd_fetch(args) -> int:
    try:
        resp = fetch.fetch_trains(
            args.date,
            full_data=args.full,
            respect_rate_limit=args.respect_rate_limit,
        )
    except RuntimeError as e:  # auth.require_key 抛的
        print(f"鉴权失败:{e}", file=sys.stderr)
        return EXIT_AUTH
    if resp.get("err"):
        _print_json(resp)
        return EXIT_API
    # 成功:输出可读格式(如果 --raw 不指定)
    if args.raw:
        _print_json(resp)
    else:
        trains = fetch.parse_trains(resp)
        _print_json({
            "date": args.date,
            "trains_count": len(trains),
            "trains": trains,
        })
    return EXIT_OK


def cmd_backfill(args) -> int:
    try:
        if args.days and args.days > 1:
            result = backfill_mod.backfill_range(end_datestr=args.date, days=args.days)
        else:
            result = backfill_mod.backfill_date(args.date, full_data=True)
    except RuntimeError as e:
        print(f"鉴权失败:{e}", file=sys.stderr)
        return EXIT_AUTH
    # backfill_range 返 end_date 字段,backfill_date 返 date 字段;统一一下显示
    if "end_date" in result and "date" not in result:
        result = {"date": result["end_date"], **result}
    _print_json(result)
    # 任何一天 fetch 失败 → 退出码 EXIT_API
    for r in result.get("results", [result]):
        if r.get("fetch_ok") is False:
            return EXIT_API
    return EXIT_OK


def cmd_push_plan(args) -> int:
    try:
        result = push.push_day_plan(args.date, dry_run=args.dry_run)
    except RuntimeError as e:
        print(f"鉴权失败:{e}", file=sys.stderr)
        return EXIT_AUTH
    _print_json(result)
    if result.get("fail_count", 0) > 0:
        return EXIT_API
    return EXIT_OK


def cmd_key(args) -> int:
    sub = args.key_action
    if sub == "status":
        _print_json(auth.status())
        return EXIT_OK
    if sub == "set":
        try:
            written = auth.set_key(args.value, legacy=args.legacy)
        except ValueError as e:
            print(f"错误:{e}", file=sys.stderr)
            return EXIT_ERR
        print(f"✅ 已写入 {written}（用户级，新开终端生效）")
        return EXIT_OK
    if sub == "clear":
        cleared = auth.clear_key(legacy=args.legacy)
        if cleared:
            print(f"✅ 已删除 {cleared}")
        else:
            print(f"⚠ {cleared or ('XUNJI_TRAINS_KEY' if not args.legacy else 'XUNJI_API_KEY')} 未设置，无需删除")
        return EXIT_OK
    print(f"未知子命令: {sub}", file=sys.stderr)
    return EXIT_ERR


def cmd_run_sync(args) -> int:
    """后台串行 N 天同步训记(写状态文件,可被 mavis cron self 唤醒)。"""
    result = run_sync.run_sync(
        days=args.days,
        start_offset=args.start_offset,
        dry_run=args.dry_run,
    )
    _print_json(result)
    if result.get("status") == "failed":
        return EXIT_API
    return EXIT_OK


def cmd_upsert(args) -> int:
    """训记 upsert API 原子调用(增/改)。"""
    # 收 res[] 列表:--json 字符串 OR --json-file 文件
    if bool(args.json) == bool(args.json_file):
        print("用法:upsert 必须二选一传 --json <res[]> 字符串 或 --json-file <path>", file=sys.stderr)
        return EXIT_ERR
    try:
        if args.json_file:
            with open(args.json_file, "r", encoding="utf-8") as f:
                res_list = json.load(f)
        else:
            res_list = json.loads(args.json)
    except (OSError, json.JSONDecodeError) as e:
        print(f"res[] 解析失败:{e}", file=sys.stderr)
        return EXIT_ERR

    if not isinstance(res_list, list):
        print(f"res[] 必须是 JSON 数组(实际:{type(res_list).__name__})", file=sys.stderr)
        return EXIT_ERR

    # dry-run 时打印对账报告(stderr),方便用户预览将要推什么
    if args.dry_run:
        print(f"  → 准备 upsert {len(res_list)} 条训练(训记单次最多 4 条):", file=sys.stderr, flush=True)
        for i, item in enumerate(res_list, 1):
            datestr = item.get("datestr", "?")
            localid = item.get("localid", 0)
            title = item.get("title", "")
            start = item.get("start", 0)
            end = item.get("end", 0)
            n_moves = len(item.get("movements", []) or [])
            kind = "新建" if localid == 0 else f"更新(localid={localid})"
            print(
                f"    [{i}/{len(res_list)}] {datestr}  {kind}  "
                f"title={title!r}  start={start}  end={end}  movements={n_moves}",
                file=sys.stderr, flush=True,
            )

    try:
        resp = upsert.upsert_trains(
            res_list,
            client_request_id=args.client_request_id,
            dry_run=args.dry_run,
            include_full_data=args.include_full_data,
        )
    except RuntimeError as e:  # auth.require_key 抛的
        print(f"鉴权失败:{e}", file=sys.stderr)
        return EXIT_AUTH
    _print_json(resp)
    if resp.get("err"):
        return EXIT_API
    return EXIT_OK


def cmd_overlay_plan(args) -> int:
    """用卡路里 plan 覆盖训记某天的训练(localid 已有,start/end=0)。"""
    from . import overlay as _overlay
    try:
        result = _overlay.overlay_day_plan(
            args.date,
            dry_run=args.dry_run,
            missing=args.missing,
        )
    except RuntimeError as e:
        print(f"鉴权失败:{e}", file=sys.stderr)
        return EXIT_AUTH
    _print_json(result)
    if result.get("err"):
        # 区分:missing=fail 报"err"是业务报错,不是 API 错;走 EXIT_ERR
        if "missing=fail" in str(result.get("err", "")):
            return EXIT_ERR
        return EXIT_API
    if result.get("fail_count", 0) > 0:
        return EXIT_API
    return EXIT_OK


# ── argparse 装配 ──────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xunji_bridge",
        description="训记 ↔ 卡路里 适配桥 CLI(卡路里技能训记训练拓展功能)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # verify
    p_verify = sub.add_parser("verify", help="校验动作名是否在训记官方库")
    p_verify.add_argument("names", nargs="+", help="一个或多个动作名")
    p_verify.set_defaults(func=cmd_verify)

    # fetch
    p_fetch = sub.add_parser("fetch", help="拉取某天的训记训练数据")
    p_fetch.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_fetch.add_argument("--full", action="store_true", help="用 include_full_data=True(30s 限频)")
    p_fetch.add_argument("--raw", action="store_true", help="输出原始 JSON,不整理")
    p_fetch.add_argument("--respect-rate-limit", action="store_true",
                          help="尊重限频:30s/15s 内二次调用自动 sleep(跨进程,默认关)")
    p_fetch.set_defaults(func=cmd_fetch)

    # backfill
    p_back = sub.add_parser("backfill", help="回写某天的训记数据到 exercise_log(幂等)")
    p_back.add_argument("--date", help="YYYY-MM-DD(默认今天)")
    p_back.add_argument("--days", type=int, default=0, help="回写 [date-N+1, date] 区间(与 --date 配合;不传 --date 则用今天)")
    p_back.set_defaults(func=cmd_backfill)

    # push-plan
    p_push = sub.add_parser("push-plan", help="推送某天的 plan 到训记(45s 限频)")
    p_push.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_push.add_argument("--dry-run", action="store_true", help="只转换不调 API")
    p_push.set_defaults(func=cmd_push_plan)

    # key
    p_key = sub.add_parser("key", help="KEY 管理(status / set / clear)")
    p_key.add_argument("key_action", choices=["status", "set", "clear"], help="子动作")
    p_key.add_argument("value", nargs="?", help="key set 时要写入的 KEY 值")
    p_key.add_argument("--legacy", action="store_true", help="操作 XUNJI_API_KEY(兼容名),默认操作 XUNJI_TRAINS_KEY")
    p_key.set_defaults(func=cmd_key)

    # run-sync(后台长跑批处理)
    p_sync = sub.add_parser("run-sync", help="后台串行 N 天同步训记(写状态文件,适合 Popen + cron self)")
    p_sync.add_argument("--days", type=int, default=3, help="同步天数(默认 3)")
    p_sync.add_argument("--start-offset", type=int, default=0, help="起始日偏移(0=今天,1=明天,...)")
    p_sync.add_argument("--dry-run", action="store_true", help="只创建状态文件,不实际跑")
    p_sync.set_defaults(func=cmd_run_sync)

    # upsert(原子:训记 upsert API 1:1)
    p_upsert = sub.add_parser("upsert", help="训记 upsert API 原子调用(增/改,res[] 透传)")
    p_upsert.add_argument("--json", help='res[] JSON 字符串,例: \'[{"datestr":"2026-07-13","localid":0,"title":"x","start":0,"end":0,"movements":[]}]\'')
    p_upsert.add_argument("--json-file", help="res[] JSON 文件路径(优先于 --json)")
    p_upsert.add_argument("--client-request-id", help="幂等键(缺则自动 uuid4)")
    p_upsert.add_argument("--include-full-data", action="store_true", help="传 include_full_data=true(改 RPE/difficulty/note 时建议)")
    p_upsert.add_argument("--dry-run", action="store_true", help="只构造 payload 不发请求")
    p_upsert.set_defaults(func=cmd_upsert)

    # overlay-plan(应用层:用卡路里 plan 覆盖训记某天训练,localid 已有,start/end=0)
    p_overlay = sub.add_parser(
        "overlay-plan",
        help="用卡路里 plan 覆盖训记某天的训练(localid 已有,start/end=0)",
    )
    p_overlay.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_overlay.add_argument("--dry-run", action="store_true", help="只构造 payload 不发请求")
    p_overlay.add_argument("--missing", choices=["fail", "skip"], default="fail",
                           help="卡路里有但训记没的 title 处理策略(默认 fail)")
    p_overlay.set_defaults(func=cmd_overlay_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
