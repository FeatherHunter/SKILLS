# -*- coding: utf-8 -*-
"""
智剪工坊 · rewrite_audio 子技能
改词翻唱 L2:Whisper 转录 + agent 改词 + matrix TTS 合成 + ffmpeg 替换音轨

agent-driven 流程(用户不需要 LLM token):
  1. transcribe: 视频 → SRT + words.json
  2. (agent) 读 SRT,改写文案
  3. synthesize: 改写文案 → MP3 (matrix MCP, 327 预置声音)
  4. replace: 视频 + MP3 → 新视频(音轨替换)

用法:
  # 1. 转录
  python rewrite_audio.py transcribe --input v.mp4 --srt v.srt

  # 2. synthesize(直接传文本,或从文件读)
  python rewrite_audio.py synthesize --text "大家好,我是帅猎羽" --voice male-qn-qingse --out v_new.mp3
  python rewrite_audio.py synthesize --text-file v_new.txt --voice female-yujie --out v_en.mp3

  # 3. 替换音轨
  python rewrite_audio.py replace --video v.mp4 --audio v_new.mp3 --out v_final.mp4
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    get_duration, ensure_dir, log_info, log_warn, log_error,
    log_section, safe_run, get_ffmpeg_path,
)

# 复用 remove_fillers 的转录 / SRT 解析
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from remove_fillers import transcribe as rf_transcribe, parse_srt, format_srt
    HAS_RF = True
except ImportError:
    HAS_RF = False


# ============================================================
# 子命令:transcribe(复用 remove_fillers)
# ============================================================

def cmd_transcribe(args):
    if not HAS_RF:
        log_error("需要 remove_fillers.py 复用转录逻辑")
        sys.exit(1)
    input_path = Path(args.input)
    if not input_path.exists():
        log_error(f"输入不存在: {input_path}")
        sys.exit(1)
    srt_path = Path(args.srt)
    sentences, words = rf_transcribe(input_path, args.whisper_model, args.device, args.language)
    ensure_dir(srt_path.parent)
    srt_path.write_text(format_srt(sentences), encoding="utf-8")
    json_path = srt_path.with_suffix(".words.json")
    json_path.write_text(
        json.dumps({"sentences": sentences, "words": words}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_info(f"SRT: {srt_path} ({len(sentences)} 句)")
    log_info(f"词级 JSON: {json_path} ({len(words)} 词)")
    print()
    print(format_srt(sentences))


# ============================================================
# 子命令:synthesize(用 matrix MCP TTS)
# ============================================================

def synthesize_via_matrix(text: str, voice_id: str, speed: float = 1.0,
                          emotion: str = None) -> Path:
    """
    通过 mavis mcp call matrix 调 TTS,把 CDN URL 下载到本地,返回本地路径。
    """
    payload = {"text": text, "voice_id": voice_id, "speed": speed}
    if emotion:
        payload["emotion"] = emotion

    # 写 JSON 到临时文件(用 Python 写,避开 PowerShell 的 BOM 问题)
    tmp_json = Path(tempfile.gettempdir()) / f"tts_args_{abs(hash(text))%100000}.json"
    # 用 write_bytes 确保无 BOM
    tmp_json.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    # 找 mavis 全路径(subprocess.run 找不到 npm 全局命令)
    mavis_bin = shutil.which("mavis") or r"C:\Users\辰辰洋洋\.mavis\bin\mavis.cmd"
    log_info(f"调 matrix TTS:voice={voice_id} speed={speed} text_len={len(text)}")
    result = subprocess.run(
        [mavis_bin, "mcp", "call", "matrix", "matrix_synthesize_speech", "--file", str(tmp_json)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=120,
    )
    if result.returncode != 0:
        log_error(f"matrix TTS 失败: {result.stderr[:500]}")
        sys.exit(1)

    # 解析 output_url(CDN)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        log_error(f"无法解析 matrix 返回: {result.stdout[:500]}")
        sys.exit(1)

    if data.get("code") != 0:
        log_error(f"matrix 报错: {data}")
        sys.exit(1)

    output_url = data.get("output_url") or data.get("output_file")
    if not output_url:
        log_error(f"matrix 返回无 output_url: {data}")
        sys.exit(1)

    # output_url 可能是 CDN URL 或本地路径
    if output_url.startswith("http"):
        # CDN URL,下载到本地
        log_info(f"下载 CDN 音频: {output_url[:80]}...")
        local_path = Path(tempfile.gettempdir()) / f"tts_{abs(hash(output_url))%100000}.mp3"
        try:
            urllib.request.urlretrieve(output_url, local_path)
        except Exception as e:
            log_error(f"CDN 下载失败: {e}")
            sys.exit(1)
    else:
        local_path = Path(output_url)
        if not local_path.exists():
            log_error(f"matrix 输出文件不存在: {local_path}")
            sys.exit(1)

    log_info(f"TTS 音频: {local_path} ({local_path.stat().st_size // 1024} KB)")
    return local_path


def cmd_synthesize(args):
    """合成 MP3"""
    if args.text:
        text = args.text
    elif args.text_file:
        # 用 utf-8-sig 自动剥 BOM(Windows Write 工具常加 BOM)
        text = Path(args.text_file).read_text(encoding="utf-8-sig").strip()
    else:
        log_error("需要 --text 或 --text-file")
        sys.exit(1)

    out_path = Path(args.out) if args.out else Path("output.mp3")
    ensure_dir(out_path.parent)
    log_section(f"合成: {len(text)} 字 → {out_path}")

    matrix_out = synthesize_via_matrix(text, args.voice, args.speed, args.emotion)

    # 复制到目标路径
    import shutil
    shutil.copy2(matrix_out, out_path)
    log_info(f"输出: {out_path} ({get_duration(out_path):.1f}s)")


# ============================================================
# 子命令:replace(ffmpeg 替换音轨)
# ============================================================

def cmd_replace(args):
    """用新音频替换视频的音轨"""
    video = Path(args.video)
    audio = Path(args.audio)
    out = Path(args.out)

    if not video.exists():
        log_error(f"视频不存在: {video}")
        sys.exit(1)
    if not audio.exists():
        log_error(f"音频不存在: {audio}")
        sys.exit(1)

    log_section(f"替换音轨: {video.name} + {audio.name} → {out.name}")
    ensure_dir(out.parent)

    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v",  # 视频流
        "-map", "1:a",  # 新音频流
        "-c:v", "copy",  # 视频不重编码(快)
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",  # 截短到较短的那个
        "-movflags", "+faststart",
        str(out),
    ]
    log_info(f"ffmpeg 替换...")
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=600)
    if result.returncode != 0:
        log_error(f"ffmpeg 失败: {result.stderr[-500:]}")
        sys.exit(1)

    log_info(f"完成: {video} ({get_duration(video):.1f}s) + {audio} ({get_duration(audio):.1f}s) → {out} ({get_duration(out):.1f}s)")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 改词翻唱 L2(transcribe + synthesize + replace)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # transcribe
    p_t = subparsers.add_parser("transcribe", help="视频 → SRT + words.json")
    p_t.add_argument("--input", required=True)
    p_t.add_argument("--srt", required=True)
    p_t.add_argument("--whisper-model", default="small",
                     choices=["tiny", "base", "small", "medium", "large-v3"])
    p_t.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    p_t.add_argument("--language", default="zh")
    p_t.set_defaults(func=cmd_transcribe)

    # synthesize
    p_s = subparsers.add_parser("synthesize", help="文本 → MP3 (matrix TTS)")
    p_s.add_argument("--text", help="直接传文本")
    p_s.add_argument("--text-file", help="从文件读文本")
    p_s.add_argument("--voice", default="male-qn-qingse",
                     help="matrix 声音 ID(默认 male-qn-qingse)")
    p_s.add_argument("--speed", type=float, default=1.0, help="速度 0.5-2")
    p_s.add_argument("--emotion", help="情绪(happy/sad/angry/fearful/disgusted/surprised/neutral)")
    p_s.add_argument("--out", help="输出 MP3 路径(默认 output.mp3)")
    p_s.set_defaults(func=cmd_synthesize)

    # replace
    p_r = subparsers.add_parser("replace", help="视频 + 音频 → 新视频")
    p_r.add_argument("--video", required=True)
    p_r.add_argument("--audio", required=True)
    p_r.add_argument("--out", required=True)
    p_r.set_defaults(func=cmd_replace)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    safe_run(main)()
