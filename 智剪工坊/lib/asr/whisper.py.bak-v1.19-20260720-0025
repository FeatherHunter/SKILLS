# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/asr/whisper 底层库

faster-whisper（OpenAI Whisper 高效实现）封装:
  - transcribe_to_srt    主入口：音频/视频 → SRT 字幕
  - transcribe_to_text   纯文本转录（无时间戳）

调用示例:
    from lib.asr.whisper import transcribe_to_srt
    transcribe_to_srt("audio.wav", "subtitles.srt", model="medium")

依赖: faster-whisper (pip install faster-whisper)
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import ensure_dir, log_info, log_warn, log_error, log_section  # noqa: E402


def check_whisper():
    """检查 faster-whisper 是否安装。"""
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        return True
    except ImportError:
        return False


def fmt_ts(seconds):
    """格式化 SRT 时间戳（HH:MM:SS,mmm）。"""
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_to_srt(audio_or_video, srt_path,
                      model="medium", device="cuda", language=None):
    """音频/视频转录为 SRT 字幕（faster-whisper）。

    Args:
        audio_or_video: 输入音频或视频
        srt_path: 输出 SRT 路径
        model: 模型（tiny/base/small/medium/large-v3）
        device: cuda / cpu
        language: 强制语言（None=自动检测）

    Returns:
        int: 段数（成功）/ None（失败）
    """
    log_section(f"Whisper 转录: {Path(audio_or_video).name}")
    ensure_dir(Path(srt_path).parent)

    if not check_whisper():
        log_error("faster-whisper 未安装")
        log_error("安装: pip install faster-whisper")
        return None

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        log_error(f"导入失败: {e}")
        return None

    log_info(f"加载模型: {model} ({device})")
    wm = WhisperModel(model, device=device)

    log_info("开始转录...")
    segments_iter, info = wm.transcribe(
        str(audio_or_video),
        language=language,
        word_timestamps=False,
        vad_filter=True,
    )

    # 生成 SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        idx = 0
        for seg in segments_iter:
            idx += 1
            start = fmt_ts(seg.start)
            end = fmt_ts(seg.end)
            text = seg.text.strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

    log_info(f"SRT 输出: {srt_path} ({idx} 段)")
    return idx


def transcribe_to_text(audio_or_video, txt_path,
                       model="medium", device="cuda", language=None):
    """音频/视频转录为纯文本（无时间戳）。

    Args:
        audio_or_video: 输入
        txt_path: 输出文本路径
        model/device/language: 同 transcribe_to_srt

    Returns:
        int: 段数（成功）/ None（失败）
    """
    log_section(f"Whisper 纯文本转录: {Path(audio_or_video).name}")
    ensure_dir(Path(txt_path).parent)

    if not check_whisper():
        log_error("faster-whisper 未安装")
        log_error("安装: pip install faster-whisper")
        return None

    from faster_whisper import WhisperModel
    wm = WhisperModel(model, device=device)

    segments_iter, info = wm.transcribe(
        str(audio_or_video),
        language=language,
        word_timestamps=False,
        vad_filter=True,
    )

    with open(txt_path, "w", encoding="utf-8") as f:
        idx = 0
        for seg in segments_iter:
            idx += 1
            text = seg.text.strip()
            f.write(f"{text}\n")

    log_info(f"文本输出: {txt_path} ({idx} 段)")
    return idx