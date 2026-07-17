#!/usr/bin/env python3
"""卡路里复盘 CLI - 独立入口(② 契约层)

按 5 层架构定位:
- ② 契约层:argparse + JSON 三段式输出
- subcommand: gen / send / archive / full
- 不依赖 calorie_tracker.py(独立,符合 Q23=A)

设计决策(用户 2026-07-16 拍板):
- **手动复盘 = agent(我)直接处理**,不调用户态 LLM
- gen 只查数据,agent 自己读数据 + 自己写 HTML
- send 接受 --text,agent 自己写飞书摘要
- full 接受 --html-path --text(由 agent 写好后传入)
- **不调 llm_call.py**:用户态 401,token 不会被 mavis 框架自动注入

用法:
    python review_cli.py gen [--range X:Y] [--type day|week|month|year]
    python review_cli.py archive --html-path <path>
    python review_cli.py send --text "..." [--feishu-url <url>]
    python review_cli.py full --html-path <path> --text "..." [--feishu-url <url>]
"""

import argparse
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Windows 上 Python 默认 stdout 是 GBK(cp936),calorie_tracker 委托时用 utf-8 读会崩
# 统一改成 UTF-8 输出(对齐 calorie_history.py / nutrition_goal.py 等其他模块)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ③ 业务层模块
import review_engine
import review_prompts
# ⑤ 集成层模块
import review_feishu


# ==================== subcommand handlers ====================

def cli_gen(args):
    """只查数据 + 衍生计算(不调 LLM)

    agent 拿到 data_path 后,自己读 JSON + 自己写 HTML。

    Returns:
        (status, data, message) tuple
        data: { data_path, prompt_path, start, end, tdee, weekly_deficit }
    """
    try:
        # 1. 解析时间范围
        start, end = review_engine.parse_range(args.range, args.type)
    except review_engine.RangeParseError as e:
        return ('error', None, str(e))

    print(f"→ 时间范围: {start} 至 {end}")

    # 2. 5 维查询
    try:
        skill_dir = Path(__file__).parent.parent  # scripts/ 的父级
        raw_data = review_engine.query_5dims(start, end, skill_dir)
    except review_engine.DataNotFoundError as e:
        return ('error', None, str(e))
    except Exception as e:
        return ('error', None, f"数据查询失败: {e}")

    print(
        f"→ 数据: {len(raw_data['daily_intake'])} 天摄入, "
        f"{len(raw_data['daily_burn'])} 天运动, "
        f"{len(raw_data['weight_logs'])} 条体重"
    )

    # 3. 衍生
    enriched = review_engine.derive(raw_data)
    print(
        f"→ 衍生: TDEE={enriched['tdee']}, "
        f"周缺口={enriched['weekly_deficit']}, "
        f"理论减重={enriched['theoretical_weight_loss']}kg"
    )

    # 4. 保存 raw_data + enriched 到 temp
    temp_dir = Path(tempfile.gettempdir()) / 'calorie_reviews'
    temp_dir.mkdir(parents=True, exist_ok=True)
    # idempotency_key(同一天多次跑会覆盖,不重复)
    idempotency_key = uuid.uuid4().hex[:8]
    data_path = temp_dir / f'data_{start}_{end}_{idempotency_key}.json'
    data_path.write_text(
        json.dumps(
            {'raw_data': raw_data, 'enriched': enriched},
            ensure_ascii=False, indent=2,
        ),
        encoding='utf-8',
    )

    # 5. 也保存 prompt 模板给 agent 参考(可选,agent 可以自己写 prompt)
    prompt = review_prompts.build_html_prompt(enriched)
    prompt_path = temp_dir / f'prompt_{start}_{end}_{idempotency_key}.txt'
    prompt_path.write_text(prompt, encoding='utf-8')

    return (
        'ok',
        {
            'data_path': str(data_path),
            'prompt_path': str(prompt_path),
            'start': start,
            'end': end,
            'tdee': enriched['tdee'],
            'weekly_deficit': enriched['weekly_deficit'],
        },
        f"数据已生成: {data_path}",
    )


def cli_archive(args):
    """上传 HTML 到飞书云盘

    Returns:
        (status, data, message) tuple
    """
    html_path = Path(args.html_path)
    if not html_path.exists():
        return ('error', None, f"文件不存在: {html_path}")

    try:
        url = review_feishu.upload_to_feishu_drive(html_path)
    except review_feishu.FeishuError as e:
        return ('error', None, f"上传失败: {e}")

    return ('ok', {'url': url, 'html_path': str(html_path)}, f"飞书链接: {url}")


def cli_send(args):
    """发飞书纯文本(接受 --text,不调 LLM)

    agent 自己在对话里生成飞书摘要文本,通过 --text 传入。

    Returns:
        (status, data, message) tuple
    """
    text = args.text
    if not text or not text.strip():
        return ('error', None, "--text 不能为空(由 agent 生成飞书摘要后传入)")

    feishu_url = args.feishu_url or ''

    # 把飞书 URL 追加到文本末尾(如果有)
    final_text = text
    if feishu_url and 'http' not in text[-100:]:
        final_text = f"{text}\n\n📊 详细报告: {feishu_url}"

    print(f"→ 文本长度: {len(final_text)} 字")

    # 发送(失败降级)
    results = review_feishu.send_feishu(final_text)
    print(
        f"→ 飞书发送: sent={results['sent']}, "
        f"failed={results['failed']}"
    )

    # 全部失败才报错,部分失败仍 ok
    if results['sent'] == 0 and results['failed'] > 0:
        return ('error', results, '所有 target 发送失败')

    return ('ok', results, f"已发 {results['sent']} 个目标,失败 {results['failed']} 个")


def cli_full(args):
    """archive + send(假设 HTML 和 text 都已存在)

    agent 流程:
    1. 跑 gen 拿数据
    2. agent 自己写 HTML,保存到 temp
    3. agent 自己写飞书文本
    4. 跑 full 传入 --html-path --text,自动 archive + send

    Returns:
        (status, data, message) tuple
    """
    html_path = args.html_path
    text = args.text

    if not html_path:
        return ('error', None, "--html-path 必填(agent 先写好 HTML 再传)")
    if not text or not text.strip():
        return ('error', None, "--text 必填(agent 先写好飞书文本再传)")

    # 1. archive
    archive_status, archive_data, archive_msg = cli_archive(
        type('Args', (), {'html_path': html_path})()
    )
    if archive_status != 'ok':
        return (archive_status, archive_data, f"archive 失败: {archive_msg}")
    feishu_url = archive_data['url']

    # 2. send(用传入的 text + archive 拿到的 url)
    return cli_send(
        type('Args', (), {'text': text, 'feishu_url': feishu_url})()
    )


# ==================== argparse + main ====================

def build_parser():
    parser = argparse.ArgumentParser(
        prog='review_cli',
        description='卡路里复盘 CLI(独立,符合 5 层契约层)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
设计:手动复盘由 agent 直接处理(不调 LLM)。
  1. python review_cli.py gen --type week  → 拿数据
  2. agent 读数据,自己写 HTML,保存到 temp
  3. python review_cli.py full --html-path <temp.html> --text "飞书摘要"
     → 自动 archive + send

示例:
  %(prog)s gen --type week
  %(prog)s gen --range 2026-07-08:2026-07-14
  %(prog)s archive --html-path /tmp/review.html
  %(prog)s send --text "🍱 卡路里周复盘..." [--feishu-url <url>]
  %(prog)s full --html-path <temp.html> --text "..." [--feishu-url <url>]
        ''',
    )
    sub = parser.add_subparsers(dest='command', required=True, metavar='SUBCOMMAND')

    # gen —— 只查数据,不调 LLM
    gen_p = sub.add_parser('gen', help='查询复盘数据(不调 LLM,由 agent 自己写 HTML)')
    gen_p.add_argument('--range', help='日期范围 X:Y(例 2026-07-08:2026-07-14)')
    gen_p.add_argument('--type', choices=['day', 'week', 'month', 'year'],
                       default='week', help='时间粒度(默认 week = 过去 7 天)')

    # archive —— 上传 HTML
    archive_p = sub.add_parser('archive', help='上传 HTML 到飞书云盘')
    archive_p.add_argument('--html-path', required=True, help='本地 HTML 文件路径')

    # send —— 发飞书纯文本(接受 --text)
    send_p = sub.add_parser('send', help='发飞书文本(由 agent 写好传入,不调 LLM)')
    send_p.add_argument('--text', required=True, help='飞书消息文本(必填)')
    send_p.add_argument('--feishu-url', help='可选,附加到文本末尾(详细报告链接)')

    # full —— archive + send(需要 HTML 和 text 都已存在)
    full_p = sub.add_parser('full', help='archive + send(HTML 和 text 必填)')
    full_p.add_argument('--html-path', required=True, help='HTML 文件路径(agent 已写好)')
    full_p.add_argument('--text', required=True, help='飞书文本(agent 已写好)')
    full_p.add_argument('--feishu-url', help='可选,自定义飞书 URL(不传则走 archive)')

    return parser


HANDLERS = {
    'gen': cli_gen,
    'archive': cli_archive,
    'send': cli_send,
    'full': cli_full,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    handler = HANDLERS[args.command]
    status, data, message = handler(args)

    # JSON 三段式输出(契约层规范)
    output = {
        'status': status,
        'data': data,
        'message': message,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if status == 'ok' else 1)


if __name__ == '__main__':
    main()
