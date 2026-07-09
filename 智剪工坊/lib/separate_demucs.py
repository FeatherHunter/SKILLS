# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/separate_demucs 底层库

Demucs（Meta 开源声源分离）封装:
  - separate_vocals      主入口：分离人声（最常用）
  - separate_full        完整分离（vocals + drums + bass + other）

v1.7 (2026-07-10) 重构:
  - 改用 Python API 而非 subprocess CLI（支持 GPU）
  - 加 device 参数（'cuda' / 'cpu'）

调用示例:
    from lib.separate_demucs import separate_vocals
    vocals_path = separate_vocals("audio.wav", "output_dir/", device="cuda")

依赖: demucs (pip install demucs) + torch + soundfile + numpy
"""
import os
import sys
import time
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # lib/ 在 path（找 common）
from common import get_duration, log_info, log_warn, log_error, log_section, ensure_dir  # noqa: E402


# 默认模型（精度 + 速度平衡）
DEFAULT_MODEL = "htdemucs"


def check_demucs():
    """检查 demucs + torch 是否可用。

    Returns:
        bool: True=可用, False=未安装
    """
    try:
        import demucs  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _resolve_device(device):
    """解析 device 参数：如果 cuda 不可用则 fallback 到 cpu。"""
    import torch
    if device == 'cuda':
        if torch.cuda.is_available():
            return 'cuda'
        else:
            log_warn("CUDA 不可用，自动 fallback 到 CPU")
            return 'cpu'
    return device


def _separate_internal(input_path, output_dir, model_name, device='cuda'):
    """Demucs 内部：调 Python API 分离 4 stems → 保存到 output_dir/<model>/<stem>/

    Args:
        input_path: 输入音频路径
        output_dir: 输出目录
        model_name: 模型名（htdemucs / htdemucs_ft / ...）
        device: 'cuda' / 'cpu'

    Returns:
        dict: {stem_name: path} 或 None（失败）
    """
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    device = _resolve_device(device)

    log_info(f"加载模型: {model_name} (device={device})")
    model = get_model(model_name)
    model = model.to(device)
    log_info(f"  sources: {model.sources}")

    log_info(f"读取音频: {input_path}")
    data, sr = sf.read(input_path)
    # demucs 要求 (batch, channels, samples) + 立体声
    if data.ndim == 1:
        # mono → stereo
        data = np.stack([data, data], axis=-1)
    audio_tensor = torch.from_numpy(data).float().transpose(0, 1).unsqueeze(0).to(device)
    log_info(f"  shape: {audio_tensor.shape}, sr: {sr}")

    log_info("开始分离...")
    start = time.time()
    out = apply_model(
        model, audio_tensor,
        device=device,
        split=True,
        overlap=0.25,
        progress=False,
        num_workers=0,
    )
    elapsed = time.time() - start
    audio_duration = data.shape[0] / sr
    log_info(f"分离完成: {elapsed:.1f}s for {audio_duration:.1f}s ({audio_duration/elapsed:.2f}x realtime)")

    # 保存每个 stem
    input_stem = Path(input_path).stem
    sep_dir = Path(output_dir) / model_name / input_stem
    sep_dir.mkdir(parents=True, exist_ok=True)

    saved = {}
    # demucs 4.x 输出 shape: (1, 4, channels, samples)
    if isinstance(out, torch.Tensor):
        out = out.cpu().numpy()  # (1, 4, channels, samples)
        for i, name in enumerate(model.sources):
            stem_np = out[0, i]  # (channels, samples)
            stem_np = stem_np.T   # (samples, channels) 适合 soundfile
            out_path = sep_dir / f"{name}.wav"
            sf.write(str(out_path), stem_np, sr, subtype='PCM_16')
            saved[name] = str(out_path)
            size = out_path.stat().st_size
            log_info(f"  ✓ {name}: {out_path.name} ({size//1024} KB)")
    elif isinstance(out, list):
        for i, name in enumerate(model.sources):
            stem = out[i]
            if hasattr(stem, 'cpu'):
                stem_np = stem.cpu().numpy()
            else:
                stem_np = stem
            if stem_np.ndim == 3:
                stem_np = stem_np[0]
            stem_np = stem_np.T
            out_path = sep_dir / f"{name}.wav"
            sf.write(str(out_path), stem_np, sr, subtype='PCM_16')
            saved[name] = str(out_path)
            size = out_path.stat().st_size
            log_info(f"  ✓ {name}: {out_path.name} ({size//1024} KB)")
    else:
        log_error(f"未知输出格式: {type(out).__name__}")
        return None

    return saved


def separate_vocals(input_path, output_dir, model=DEFAULT_MODEL, device='cuda'):
    """Demucs 分离人声（最常用）。

    Args:
        input_path: 输入音频/视频
        output_dir: 输出目录
        model: 模型（htdemucs / htdemucs_ft / mdx_extra / ...）
        device: 'cuda'（默认，GPU）/ 'cpu'

    Returns:
        str: vocals.wav 路径（成功）/ None（失败）
    """
    log_section(f"Demucs 分离人声: {Path(input_path).name} (model={model}, device={device})")
    ensure_dir(output_dir)

    if not check_demucs():
        log_error("demucs 或 torch 未安装")
        log_error("安装: pip install demucs  +  pip install torch torchaudio")
        return None

    try:
        saved = _separate_internal(input_path, output_dir, model, device)
        if saved and "vocals" in saved:
            log_info(f"人声: {saved['vocals']}")
            return saved["vocals"]
        log_error("未生成 vocals stem")
        return None
    except Exception as e:
        log_error(f"Demucs 失败: {type(e).__name__}: {e}")
        return None


def separate_full(input_path, output_dir, model=DEFAULT_MODEL, device='cuda'):
    """Demucs 完整分离（vocals + drums + bass + other）。

    Args:
        input_path: 输入音频/视频
        output_dir: 输出目录
        model: 模型名
        device: 'cuda' / 'cpu'

    Returns:
        dict: {stem_name: path}（成功）/ None（失败）
    """
    log_section(f"Demucs 完整分离: {Path(input_path).name} (model={model}, device={device})")
    ensure_dir(output_dir)

    if not check_demucs():
        log_error("demucs 或 torch 未安装")
        return None

    try:
        return _separate_internal(input_path, output_dir, model, device)
    except Exception as e:
        log_error(f"Demucs 失败: {type(e).__name__}: {e}")
        return None