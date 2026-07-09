# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/voice 子技能（v1.5 迁移版本）

调用 lib/ffmpeg/audio/transform.py 的变声能力。
本文件作为用户入口 CLI + 业务参数封装（变声预设）。

音频链路层级: L2 变换

用法:
  python audio/voice.py --input in.mp4 --type old_man --output out.mp4
  python audio/voice.py --input in.mp4 --pitch 1.5 --output out.mp4

依赖: lib.ffmpeg.audio.transform
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
    ensure_dir, log_info, log_section, log_warn, log_error, safe_run,
)
from ffmpeg.audio.transform import change_pitch, add_tremolo


# ========== 变声预设 → lib 参数映射 ==========
PRESETS = {
    "old_man": {
        "description": "老人（低沉）",
        "pitch": 0.7,
    },
    "child": {
        "description": "小孩（高音）",
        "pitch": 1.5,
    },
    "robot": {
        "description": "机器人（颤音）",
        "pitch": 1.0,
        "robot": True,
    },
    "female": {
        "description": "女声",
        "pitch": 1.2,
    },
    "male": {
        "description": "男声（低沉）",
        "pitch": 0.85,
    },
    "whisper": {
        "description": "耳语（颤音）",
        "pitch": 0.95,
        "whisper": True,
    },
    "chipmunk": {
        "description": "花栗鼠（超高音）",
        "pitch": 2.0,
    },
    "deep": {
        "description": "极低沉",
        "pitch": 0.5,
    },
}


def change_voice(input_path, output_path, pitch=1.0, robot=False, whisper=False):
    """变声（v1.5 迁移版本：调 lib/ffmpeg/audio/transform）。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频/视频
        pitch: 音调倍数（0.5-2.0）
        robot: 是否机器人声（叠加 tremolo）
        whisper: 是否耳语（叠加 tremolo）
    Returns:
        output 路径（成功）；None（失败）
    """
    log_section(f"变声 pitch={pitch} robot={robot} whisper={whisper}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 步骤 1: 变调（输出到临时文件）
    import tempfile
    pitch_output = Path(tempfile.gettempdir()) / f"voice_pitch_{Path(output_path).stem}.wav"
    try:
        success, _ = change_pitch(input_path, str(pitch_output), pitch=pitch)
    except ValueError as e:
        log_error(f"参数错误: {e}")
        return None
    except Exception as e:
        log_error(f"变调失败: {e}")
        return None

    if not success:
        log_error("变调失败（lib 返回失败）")
        try:
            pitch_output.unlink()
        except Exception:
            pass
        return None

    # 步骤 2: 是否需要叠加 tremolo
    try:
        if robot or whisper:
            # 变调输出 + tremolo → 最终 output
            success, _ = add_tremolo(str(pitch_output), output_path,
                                     frequency=20 if robot else 15,
                                     depth=0.5)
            if not success:
                log_warn("变调成功，但叠加 tremolo 失败")
                # 至少变调成功了，把临时输出 copy 到 output
                import shutil
                shutil.copy2(str(pitch_output), output_path)
        else:
            # 无叠加，直接 move
            import shutil
            shutil.move(str(pitch_output), str(output_path))

        log_info(f"输出: {output_path}")
        return str(output_path)
    finally:
        # 确保临时文件清理
        try:
            pitch_output.unlink()
        except Exception:
            pass


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 音频变声（调 lib/ffmpeg/audio/transform）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"预设: {', '.join(PRESETS.keys())}\n\n示例:\n  %(prog)s --input in.mp4 --type old_man --output out.mp4\n  %(prog)s --input in.mp4 --pitch 1.5 --output out.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--type", choices=list(PRESETS.keys()), help="预设变声")
    parser.add_argument("--pitch", type=float, help="自定义音调倍数（0.5-2.0）")
    args = parser.parse_args()

    if args.type:
        preset = PRESETS[args.type]
        change_voice(
            args.input, args.output,
            pitch=preset.get("pitch", 1.0),
            robot=preset.get("robot", False),
            whisper=preset.get("whisper", False),
        )
    else:
        change_voice(args.input, args.output, pitch=args.pitch or 1.0)


if __name__ == "__main__":
    safe_run(main)