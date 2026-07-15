#!/usr/bin/env python3
"""卡路里复盘 CLI - 独立入口(② 契约层)

按 5 层架构定位:
- ② 契约层:argparse + JSON 三段式输出
- subcommand: gen / send / archive / full
- 不依赖 calorie_tracker.py(独立,符合 Q23=A)

用法:
    python review_cli.py gen [--range X:Y] [--type day|week|month|year]
    python review_cli.py archive --html-path <path>
    python review_cli.py send --html-path <path> [--feishu-url <url>]
    python review_cli.py full [--range X:Y] [--type day|week|month|year]
"""

import argparse
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

# ③ 业务层模块
import review_engine
import review_prompts
# ⑤ 集成层模块
import review_feishu


# ==================== subcommand handlers ====================

def cli_gen(args):
    """生成复盘 HTML(LLM 装填)

    Returns:
        (status, data, message) tuple
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

    # 4. LLM 装填
    prompt = review_prompts.build_html_prompt(enriched)
    print("→ 调 LLM 装填 review.html...")
    try:
        html_output = review_prompts.call_llm(prompt)
    except Exception as e:
        return ('error', None, f"LLM 调用失败: {e}")

    # 5. 保存到 temp(Q17=C)
    temp_dir = Path(tempfile.gettempdir()) / 'calorie_reviews'
    temp_dir.mkdir(parents=True, exist_ok=True)
    # 文件名带 idempotency_key(同一天多次跑会覆盖,不重复)
    idempotency_key = uuid.uuid4().hex[:8]
    html_path = temp_dir / f'review_{start}_{end}_{idempotency_key}.html'
    html_path.write_text(html_output, encoding='utf-8')

    return (
        'ok',
        {
            'html_path': str(html_path),
            'start': start,
            'end': end,
            'tdee': enriched['tdee'],
            'weekly_deficit': enriched['weekly_deficit'],
        },
        f"HTML 已生成: {html_path}",
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
    """从 HTML 提取摘要,LLM 生成飞书消息,发送

    Returns:
        (status, data, message) tuple
    """
    html_path = Path(args.html_path)
    if not html_path.exists():
        return ('error', None, f"HTML 文件不存在: {html_path}")

    feishu_url = args.feishu_url or ''

    # 1. 提取摘要
    try:
        html_output = html_path.read_text(encoding='utf-8')
        summary = review_engine.extract_summary(html_output)
    except Exception as e:
        return ('error', None, f"摘要提取失败: {e}")

    print(f"→ 摘要提取: {summary.get('date_range', '(无)')}")

    # 2. LLM 生成飞书消息
    feishu_prompt = review_prompts.build_feishu_prompt(summary, feishu_url)
    print("→ 调 LLM 生成飞书消息...")
    try:
        feishu_text_template = review_prompts.call_llm(feishu_prompt)
    except Exception as e:
        return ('error', None, f"飞书消息生成失败: {e}")

    # 3. 替换占位符
    final_text = _fill_template(feishu_text_template, summary, feishu_url)

    # 4. 发送(失败降级)
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
    """全跑:gen → archive → send

    Returns:
        (status, data, message) tuple
    """
    # 1. gen
    status, data, msg = cli_gen(args)
    if status != 'ok':
        return (status, data, msg)
    html_path = data['html_path']

    # 2. archive
    archive_status, archive_data, archive_msg = cli_archive(
        type('Args', (), {'html_path': html_path})()
    )
    if archive_status != 'ok':
        return (archive_status, archive_data, f"archive 失败: {archive_msg}")
    feishu_url = archive_data['url']

    # 3. send
    return cli_send(
        type('Args', (), {'html_path': html_path, 'feishu_url': feishu_url})()
    )


def _fill_template(template, summary, feishu_url):
    """替换 {{xxx}} 占位符"""
    result = template
    for key, value in summary.items():
        result = result.replace('{{' + key + '}}', str(value))
    result = result.replace('{{feishu_url}}', feishu_url)
    return result


# ==================== argparse + main ====================

def build_parser():
    parser = argparse.ArgumentParser(
        prog='review_cli',
        description='卡路里复盘 CLI(独立,符合 5 层契约层)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s gen --type week
  %(prog)s gen --range 2026-07-08:2026-07-14
  %(prog)s archive --html-path /tmp/review.html
  %(prog)s send --html-path /tmp/review.html
  %(prog)s full --type week
        ''',
    )
    sub = parser.add_subparsers(dest='command', required=True, metavar='SUBCOMMAND')

    # gen
    gen_p = sub.add_parser('gen', help='生成复盘 HTML(LLM 装填)')
    gen_p.add_argument('--range', help='日期范围 X:Y(例 2026-07-08:2026-07-14)')
    gen_p.add_argument('--type', choices=['day', 'week', 'month', 'year'],
                       default='week', help='时间粒度(默认 week = 过去 7 天)')

    # archive
    archive_p = sub.add_parser('archive', help='上传 HTML 到飞书云盘')
    archive_p.add_argument('--html-path', required=True, help='本地 HTML 文件路径')

    # send
    send_p = sub.add_parser('send', help='发飞书摘要(targets 从 env 读)')
    send_p.add_argument('--html-path', required=True, help='本地 HTML 文件路径')
    send_p.add_argument('--feishu-url', help='飞书云盘链接(可选)')

    # full
    full_p = sub.add_parser('full', help='全跑:gen + archive + send')
    full_p.add_argument('--range', help='日期范围 X:Y')
    full_p.add_argument('--type', choices=['day', 'week', 'month', 'year'],
                        default='week', help='时间粒度(默认 week)')

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