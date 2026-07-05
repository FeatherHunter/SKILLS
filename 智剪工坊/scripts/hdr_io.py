# -*- coding: utf-8 -*-
"""
智剪工坊 · hdr_io 子技能
HDR 视频导入导出(Rec.2020 / HLG / HDR10)

用法:
  # SDR → HDR 转换
  python hdr_io.py --input sdr.mp4 --output hdr.mp4 --mode convert

  # HDR 标记 + 元数据写入
  python hdr_io.py --input video.mp4 --output hdr.mp4 --mode tag --transfer hlg


📖 SKILL.md §14 索引 → REQUIRED: read references/05-color.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


# HDR 色彩空间
COLOR_PRIMARIES = {
    "bt709": "bt709",       # SDR 标准
    "bt2020": "bt2020",     # HDR 标准
    "displayp3": "displayp3",  # Apple
}

TRANSFER_CHARACTERISTICS = {
    "bt709": "bt709",       # SDR
    "hlg": "arib-std-b67",  # HLG(Hybrid Log-Gamma)
    "pq": "smpte2084",      # PQ(Perceptual Quantizer,用于 HDR10)
    "smpte2084": "smpte2084",
}

COLOR_RANGES = {
    "tv": "tv",       # Limited(16-235)
    "pc": "pc",       # Full(0-255)
}


def convert_sdr_to_hdr(input_path, output_path, transfer="hlg"):
    """SDR 转 HDR"""
    log_section(f"SDR → HDR({transfer}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 用 tonemap 反向 + HDR 元数据
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"zscale=t=linear,format=yuv420p10le,colorspace=all=bt2020:trc={TRANSFER_CHARACTERISTICS.get(transfer, 'arib-std-b67')}:range=tv",
        "-color_primaries", "bt2020",
        "-color_trc", TRANSFER_CHARACTERISTICS.get(transfer, "arib-std-b67"),
        "-colorspace", "bt2020_ncl",
        "-color_range", "tv",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def tag_hdr(input_path, output_path, transfer="hlg", primaries="bt2020"):
    """标记视频为 HDR(不重编码)"""
    log_section(f"HDR 标记 {transfer}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-i", str(input_path),
        "-c", "copy",
        "-color_primaries", COLOR_PRIMARIES.get(primaries, "bt2020"),
        "-color_trc", TRANSFER_CHARACTERISTICS.get(transfer, "arib-std-b67"),
        "-colorspace", "bt2020_ncl",
        "-color_range", "tv",
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def extract_hdr_metadata(input_path):
    """提取 HDR 元数据"""
    import subprocess
    result = subprocess.run(
        ["ffmpeg", "-i", str(input_path)],
        capture_output=True, text=True
    )
    info = {}
    for line in result.stderr.split("\n"):
        if "color primaries" in line.lower() or "transfer characteristics" in line.lower() or "color space" in line.lower():
            log_info(line.strip())
            info[line.strip()] = True
    return info


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · HDR 视频导入导出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--mode", choices=["convert", "tag"], default="convert",
                       help="convert=SDR 转 HDR / tag=只标记 HDR")
    parser.add_argument("--transfer", choices=list(TRANSFER_CHARACTERISTICS.keys()),
                       default="hlg", help="HDR 类型")
    parser.add_argument("--primaries", choices=list(COLOR_PRIMARIES.keys()),
                       default="bt2020", help="色彩空间")
    args = parser.parse_args()

    if args.mode == "convert":
        convert_sdr_to_hdr(args.input, args.output, args.transfer)
    else:
        tag_hdr(args.input, args.output, args.transfer, args.primaries)


if __name__ == "__main__":
    safe_run(main)()
