# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/pyannote 底层库

pyannote.audio（说话人分离）封装:
  - diarize_speakers      主入口：识别说话人（输出时间戳 + 标签）

调用示例:
    from lib.pyannote import diarize_speakers
    result = diarize_speakers("vocals.wav", min_speakers=1, max_speakers=4)
    # result = {'segments': [{'start': 0.0, 'end': 3.5, 'speaker': 'SPEAKER_00'}, ...]}

依赖: pyannote.audio + HuggingFace token
"""
import json
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import ensure_dir, log_info, log_warn, log_error, log_section, get_duration  # noqa: E402


# 默认模型（需要 HuggingFace 授权）
DEFAULT_MODEL = "pyannote/speaker-diarization-3.1"


def check_pyannote():
    """检查 pyannote.audio 是否安装（同时检查 torch，因为 pyannote 依赖 torch）。"""
    try:
        import torch  # noqa: F401
        from pyannote.audio import Pipeline  # noqa: F401
        return True
    except ImportError:
        return False


def check_torch():
    """检查 torch 是否单独可用（GPU/CPU 信息）。"""
    try:
        import torch
        cuda = torch.cuda.is_available()
        return True, cuda
    except ImportError:
        return False, False


def diarize_speakers(audio_path, output_json=None,
                     min_speakers=1, max_speakers=8,
                     use_auth_token=None, model=DEFAULT_MODEL):
    """说话人分离（pyannote.audio）。

    Args:
        audio_path: 输入音频（建议先用 demucs 提取人声）
        output_json: 输出 JSON 路径（None 则不写盘）
        min_speakers: 最少说话人数
        max_speakers: 最多说话人数
        use_auth_token: HuggingFace token（需要授权 pyannote 模型）
        model: 模型名

    Returns:
        dict: 包含 segments 列表的字典（成功）/ None（失败）

    输出格式:
    {
      "audio": "path/to/audio.wav",
      "duration": 10.5,
      "speaker_count": 2,
      "segments": [
        {"start": 0.0, "end": 3.5, "speaker": "SPEAKER_00"},
        {"start": 3.6, "end": 7.2, "speaker": "SPEAKER_01"},
        ...
      ]
    }
    """
    log_section(f"pyannote 说话人分离: {Path(audio_path).name}")
    log_info(f"min={min_speakers} max={max_speakers} model={model}")

    if not check_pyannote():
        log_error("pyannote.audio 未安装")
        log_error("安装: pip install pyannote.audio")
        log_error("注意: 需要申请 pyannote 授权（https://huggingface.co/pyannote）")
        return None

    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError as e:
        log_error(f"导入失败: {e}")
        return None

    log_info("加载模型...")
    try:
        pipeline = Pipeline.from_pretrained(
            model,
            use_auth_token=use_auth_token,
        )
    except Exception as e:
        log_error(f"加载模型失败: {e}")
        log_error("可能原因: 未提供 HuggingFace token，或未授权该模型")
        return None

    # GPU 加速
    if torch.cuda.is_available():
        pipeline = pipeline.to(torch.device("cuda"))
        log_info("使用 GPU")
    else:
        log_warn("无 GPU，使用 CPU（较慢）")

    log_info("开始分离...")
    try:
        diarization = pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    except Exception as e:
        log_error(f"分离失败: {e}")
        return None

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
        })

    duration = get_duration(audio_path) or 0.0
    speaker_count = len({s["speaker"] for s in segments})

    result = {
        "audio": str(audio_path),
        "duration": duration,
        "min_speakers": min_speakers,
        "max_speakers": max_speakers,
        "speaker_count": speaker_count,
        "model": model,
        "segments": segments,
    }

    log_info(f"说话人数: {speaker_count}, 分段数: {len(segments)}")

    if output_json:
        ensure_dir(Path(output_json).parent)
        Path(output_json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log_info(f"输出: {output_json}")

    return result