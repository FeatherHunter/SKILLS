"""lib.cli_args — v1.1 共享 CLI 参数解析

各 step 脚本独立可调，但用同一个 argparse 模板确保参数一致。
不需要分发层 (zhijian.py)。

设计原则:
- 每个 step 脚本独立入口 (AI 工作流友好)
- 共享 base 参数: --workspace, --target-aspect
- step-specific 参数由各脚本自己加
- aspect 解析逻辑统一: CLI > intent > default
"""
import argparse


# 支持的目标比例 (与 processing.TARGET_RESOLUTIONS 对齐)
ASPECT_CHOICES = ['16:9', '9:16', '1:1', '4:3', '3:4']


def make_base_parser(description: str) -> argparse.ArgumentParser:
    """创建基础 argparse，含 v1.1 所有 step 共享的参数。

    Args:
        description: 命令描述

    Returns:
        argparse.ArgumentParser，可继续 add_argument() 加 step-specific 参数
    """
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--workspace', required=True, help='工作区根目录')
    p.add_argument(
        '--target-aspect',
        choices=ASPECT_CHOICES,
        default=None,
        help='覆盖 intent.output.aspect_ratio (默认从 intent.json 读)'
    )
    return p


def resolve_aspect(args, intent: dict) -> str:
    """根据 CLI 参数和 intent 决定最终 aspect_ratio。

    优先级: CLI --target-aspect > intent.output.aspect_ratio > 默认 '16:9'

    Args:
        args: parse_args() 结果 (含 target_aspect 字段)
        intent: 解析后的 intent.json dict

    Returns:
        最终 aspect_ratio 字符串
    """
    return (
        getattr(args, 'target_aspect', None)
        or (intent.get('output', {}) or {}).get('aspect_ratio')
        or '16:9'
    )