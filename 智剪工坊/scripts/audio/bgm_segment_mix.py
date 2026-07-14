# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/bgm_segment_mix（v1.15 新增）

多段 BGM 拼接 + 混合进视频 + 分段音量。

用法:
  # 多段 BGM 拼接：bigroom 60s + hardstyle 150s + epic 74s
  python scripts/audio/bgm_segment_mix.py \
    --input final.mp4 \
    --bgm bgm_bigroom.mp3,60 bgm_hardstyle.mp3,150 bgm_epic.mp3,74 \
    --bgm-volume 0.50 \
    --loud 11,246,0.80 \
    --output out.mp4

分段音量（--loud）:
  格式: start_sec,end_sec,volume（可多次指定，不重叠）

  例: --loud 11,246,0.80  → 11-246s BGM 音量 0.80，默认 0.50
       --loud 0,30,0.3 --loud 100,200,0.9 → 0-30s=0.3,100-200s=0.9,其余=0.50

统一输出: 1080x1920 + yuv420p + 30fps
依赖: ffmpeg（PATH）+ common.py（智剪工坊 lib）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib" / "video"))

from common import get_ffmpeg_path, get_duration, run_ffmpeg, log_info, log_section, log_error, safe_run, ParamError
from patch_mp4_rotation import patch_mp4_rotation as _patch_rotation


def _parse_bgm_spec(raw: str) -> list:
    """解析 '--bgm bgm1.mp3,60 bgm2.mp3,150' → [(path, duration), ...] """
    specs = []
    for item in raw:
        parts = item.rsplit(",", 1)
        if len(parts) == 2:
            specs.append((parts[0].strip(), float(parts[1])))
        else:
            specs.append((parts[0].strip(), None))
    return specs


def _parse_loud(raw: list) -> list:
    """解析 '--loud 11,246,0.8 --loud 50,80,1.2' → [(start, end, vol), ...] """
    result = []
    for item in raw:
        parts = item.split(",")
        if len(parts) != 3:
            raise ParamError(f"--loud 格式错误: {item} (应为 start,end,volume)")
        result.append((float(parts[0]), float(parts[1]), float(parts[2])))
    return sorted(result, key=lambda x: x[0])


def combine_bgm(specs: list, output: Path, bgm_volume: float):
    """按 specs 拼接多段 BGM → output

    specs: [(path, duration_sec), ...]
    每段 cut 指定时长，段间 0.5s fade，统一音量 bgm_volume
    """
    n = len(specs)
    if n == 0:
        raise ParamError("至少指定一个 --bgm")

    if n == 1:
        # 单段直接 trim
        p, dur = specs[0]
        run_ffmpeg([
            "-y", "-i", p,
            "-t", str(dur),
            "-c:a", "aac", "-b:a", "256k",
            str(output),
        ])
        return

    # 多段用 filter_complex 拼接（段间 0.5s fade）
    inputs = []
    filter_parts = []
    for i, (p, dur) in enumerate(specs):
        inputs.extend(["-i", p])
        seg_start = sum(s[1] for s in specs[:i])  # 累计起始时间
        seg_start_fade = seg_start + 0.5
        # 每段: atrim + afade in/out
        filter_parts.append(
            f"[{i}:a]atrim=0:{dur},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.3,afade=t=out:st={dur-0.5}:d=0.5[a{i}]"
        )

    # 拼接
    concat_inputs = "".join(f"[a{i}]" for i in range(n))
    filter_parts.append(f"{concat_inputs}concat=n={n}:v=0:a=1[bgm]")
    filter_parts.append(f"[bgm]volume={bgm_volume}[bgm_out]")

    cmd = ["-y"] + inputs + [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[bgm_out]",
        "-c:a", "aac", "-b:a", "256k",
        str(output),
    ]
    run_ffmpeg(cmd)


def mix_with_loud(video: Path, bgm: Path, output: Path,
                  bgm_volume: float, loud_segments: list):
    """混合 BGM 进视频，支持分段音量

    loud_segments: [(start, end, vol), ...]
    用 ffmpeg volume='if(between(t,...),...)' 表达式
    """
    ffmpeg = get_ffmpeg_path()

    # 构造分段音量表达式
    if loud_segments:
        # 无分段时的默认音量值
        default_vol = bgm_volume
        # 构造嵌套 if
        vol_expr = str(default_vol)
        for start, end, vol in reversed(loud_segments):
            vol_expr = f"if(between(t,{start},{end}),{vol},{vol_expr})"
    else:
        vol_expr = str(bgm_volume)

    total_dur = get_duration(bgm)
    filter_str = (
        f"[0:a]volume=1.0[orig];"
        f"[1:a]volume='{vol_expr}':eval=frame,"
        f"afade=t=in:st=0:d=1,afade=t=out:st={total_dur-1}:d=1[bgm];"
        f"[orig][bgm]amix=inputs=2:duration=first:dropout_transition=0[mix]"
    )

    cmd = [
        ffmpeg, "-y",
        "-i", str(video),
        "-i", str(bgm),
        "-filter_complex", filter_str,
        "-map", "0:v",
        "-map", "[mix]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output),
    ]
    run_ffmpeg(cmd)


def patch_rotation(path: Path):
    """清 tkhd matrix + remux"""
    _patch_rotation(path, 0)
    tmp = path.with_suffix(".patched.mp4")
    run_ffmpeg([
        "-y", "-i", str(path),
        "-map", "0", "-c", "copy",
        "-map_metadata", "-1",
        "-metadata:s:v:0", "rotate=0",
        "-movflags", "+faststart",
        str(tmp),
    ])
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 多段 BGM 拼接 + 混合 + 分段音量",
    )
    parser.add_argument("--input", required=True, help="输入视频")
    parser.add_argument("--output", required=True, help="输出视频")
    parser.add_argument("--bgm", nargs="+", required=True,
                       help="BGM 文件,时长(秒) 如 'bgm.mp3,60'，可多个")
    parser.add_argument("--bgm-volume", type=float, default=0.50,
                       help="BGM 默认音量 (默认 0.50)")
    parser.add_argument("--loud", nargs="*", default=[],
                       help="分段音量 'start,end,vol' 如 '11,246,0.80'")
    args = parser.parse_args()

    bgm_specs = _parse_bgm_spec(args.bgm)
    loud_segments = _parse_loud(args.loud)

    tmp_bgm = Path(args.output).with_suffix(".bgm_tmp.mp4")

    log_section(f"拼接 {len(bgm_specs)} 段 BGM")
    combine_bgm(bgm_specs, tmp_bgm, args.bgm_volume)

    log_section(f"混合 BGM 进视频 ({len(loud_segments)} 个分段音量)")
    mix_with_loud(Path(args.input), tmp_bgm, Path(args.output),
                  args.bgm_volume, loud_segments)

    log_section("patch rotation")
    patch_rotation(Path(args.output))

    tmp_bgm.unlink(missing_ok=True)

    log_info(f"✓ 完成: {args.output} ({get_duration(args.output):.1f}s)")


if __name__ == "__main__":
    safe_run(main)()
