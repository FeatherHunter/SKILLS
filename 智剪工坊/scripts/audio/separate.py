# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/separate 子技能（v1.5 迁移版本）

调用 lib/demucs 的声源分离能力。
本文件作为用户入口 CLI + 业务参数封装。

链路位置: L4 分离

用法:
  # 完整分离（vocals + drums + bass + other）
  python scripts/audio/separate.py -i audio.wav --output-dir ./separated

  # 只提取人声
  python scripts/audio/separate.py -i audio.wav --output vocals.wav --stem vocals

  # 指定模型
  python scripts/audio/separate.py -i audio.wav --output-dir ./separated --model htdemucs_ft

依赖: demucs (pip install demucs)
底层: lib.demucs (v1.5 新增)
"""
import argparse
import sys
from pathlib import Path

# 设置 sys.path：保证 SKILL_ROOT 和 lib 都在 path（但 append，不覆盖）
_SKILL_ROOT = Path(__file__).parent.parent.parent  # SKILL_ROOT/
_LIB_DIR = _SKILL_ROOT / "lib"

# 用 append（不会覆盖），并且只在路径里不存在时才加入
def _ensure_in_path(p):
    p = str(p)
    if p not in sys.path:
        sys.path.append(p)

_ensure_in_path(str(_SKILL_ROOT))
_ensure_in_path(str(_LIB_DIR))

from common import (
    ensure_dir, log_info, log_warn, log_section, log_error, safe_run,
)
from lib.demucs import separate_vocals, separate_full, check_demucs


def separate(input_path, output_dir, model="htdemucs", stem=None):
    """声源分离（v1.5 迁移版本：调 lib/demucs）。

    Args:
        input_path: 输入音频/视频
        output_dir: 输出目录
        model: Demucs 模型名
        stem: 只提取指定音轨（vocals / drums / bass / other）

    Returns:
        str (vocals 路径) / dict (完整分离) / None
    """
    log_section(f"声源分离: {Path(input_path).name} (model={model})")
    ensure_dir(output_dir)

    if not check_demucs():
        log_error("demucs 未安装")
        log_error("安装: pip install demucs")
        return None

    if stem == "vocals":
        # 只提取人声（推荐，节省一半空间）
        result = separate_vocals(input_path, output_dir, model=model)
        if result:
            log_info(f"人声输出: {result}")
        return result
    elif stem:
        log_warn(f"--stem={stem} 暂不支持单独提取（仅 vocals），输出完整 4 轨")
        return None
    else:
        # 完整 4 轨分离
        result = separate_full(input_path, output_dir, model=model)
        if result:
            log_info(f"分离完成: {len(result)} 轨")
        return result


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 声源分离（Demucs）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法:
  完整分离（4 轨）: %(prog)s -i audio.wav --output-dir ./separated
  只提取人声:    %(prog)s -i audio.wav --output vocals.wav --stem vocals
  指定模型:      %(prog)s -i audio.wav --output-dir ./out --model htdemucs_ft

Demucs 模型:
  htdemucs      默认（精度 + 速度平衡）
  htdemucs_ft   精调版（更慢但更准）
  mdx_extra     MDX 系列
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频/视频")
    parser.add_argument("--output", help="输出文件（--stem vocals 时必填）")
    parser.add_argument("--output-dir", help="分离输出目录")
    parser.add_argument("--model", default="htdemucs",
                        help="模型（默认 htdemucs）")
    parser.add_argument("--stem",
                        choices=["vocals", "drums", "bass", "other"],
                        help="只提取指定音轨（仅 vocals 可单独输出）")

    args = parser.parse_args()

    if args.stem and not args.output:
        log_error("--stem 必须配合 --output 使用")
        sys.exit(1)
    if not args.stem and not args.output_dir:
        log_error("完整分离需要 --output-dir，或单独提取需要 --stem + --output")
        sys.exit(1)

    output_dir = args.output_dir or str(Path(args.output).parent)
    result = separate(args.input, output_dir, args.model, args.stem)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)