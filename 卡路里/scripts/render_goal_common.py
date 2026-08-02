#!/usr/bin/env python3
"""目标管理渲染器共享工具(R1-R8 规则族 · 2026-08-02 对齐 #8 经验)

- R3 思考链校验:_chain_valid(与 render_crud_view 同规则,避免重复实现)
- R4 自描述:build_meta(唤醒词/来源/时间/渲染命令)
- R5 命名:scene_path(统一 html_scene_path)
"""
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa: E402


def chain_valid(chain) -> bool:
    """思考链有效性校验(R3 · 2026-08-02 用户拍板):非空 + 含步骤特征 + 拒绝偷懒占位"""
    chain = (chain or '').strip()
    if len(chain) < 8:
        return False
    if not any(m in chain for m in ('→', '->', '1.', '1、', '2.', '第一步')):
        return False
    if chain.lower() in ('x', 'xx', 'xxx', '思考链', 'chain', '无', 'none'):
        return False
    return True


def build_meta(wake_word: str, source: str, chain=None, extra=None) -> dict:
    """组装排障 meta(R4):唤醒词/来源/时间/思考链/渲染命令

    Args:
        wake_word: 场景名(自描述)
        source: 数据来源说明(如 'daily_goal + food_log')
        chain: AI 思考链(可选)
        extra: 附加字段 dict(可选)
    """
    meta = {
        'wake_word': wake_word,
        'source': source,
        'fetched_at': datetime.now().isoformat(timespec='seconds')[:16].replace('T', ' '),
        'render_cmd': _render_cmd(),
    }
    if chain:
        meta['chain'] = chain
    if extra:
        meta.update(extra)
    return meta


def _render_cmd() -> str:
    """完整可复现命令:python scripts/<name>.py <args>(过滤 --output)"""
    argv = sys.argv[1:]
    if '--output' in argv:
        i = argv.index('--output')
        argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
    return f"python scripts/{Path(sys.argv[0]).name} " + ' '.join(argv)


def scene_path(scene_name: str, output_type: str):
    """R5 命名:<场景名>_<类型中文>_<TS>.html(统一入口,禁止手拼)"""
    return html_scene_path(SKILL_DIR, scene_name, output_type)
