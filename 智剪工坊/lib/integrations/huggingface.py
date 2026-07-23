# -*- coding: utf-8 -*-
"""
智剪工坊 · HuggingFace 集成层（v1.21 新建）

封装 3 个 HuggingFace 调用点（原散落在 lib/asr/ + lib/）：

  | # | 库                   | 原调用脚本                       | 用途          |
  |---|----------------------|----------------------------------|---------------|
  | 1 | faster-whisper       | lib/asr/whisper.py              | Whisper ASR   |
  | 2 | pyannote.audio       | lib/asr/pyannote.py             | 说话人分离    |
  | 3 | demucs + torch       | lib/separate_demucs.py          | 声源分离      |

现有调用模式（3 处高度相似）：
  - 都依赖 HuggingFace token（pyannote 强制，whisper/demucs 可选）
  - 都要解析 HF_HUB_CACHE 路径（HF_HUB_CACHE > HUGGINGFACE_HUB_CACHE > HF_HUB_DOWNLOAD_ROOT > ~/.cache/huggingface/hub）
  - 都要处理 CUDA 不可用时自动 fallback 到 CPU

设计要点：
  - 统一 token 探测（环境变量 HF_TOKEN > 配置文件 > 用户输入）
  - 统一 cache 路径解析（与 SKILL.md §v1.21 HF env 一致）
  - 统一 CUDA 自动检测（torch.cuda.is_available() → device 决策）
  - 统一镜像源（HF_ENDPOINT 默认 https://hf-mirror.com）
  - 统一失败降级（CUDA OOM → CPU；token 缺失 → 跳过说话人分离）

对外接口：
    HuggingFaceClient().transcribe(audio_path, model="large-v3", ...)
    HuggingFaceClient().diarize(audio_path, token=None, ...)
    HuggingFaceClient().separate(audio_path, model="htdemucs", ...)

骨架状态（Sprint P0-1 step 1/7）：
  - 类与函数签名已定
  - 实现细节待 P0-1 step 3/7 填充
"""
from pathlib import Path
import sys
import os

# 引导：保证 lib/common.py 可被找到
_LIB_DIR = Path(__file__).parent.parent
if str(_LIB_DIR) not in sys.path:
    sys.path.append(str(_LIB_DIR))

from common import SkillError  # noqa: E402


# ============================================================
# HF 标准 env（与 SKILL.md §v1.21 HF env 优先级一致）
# ============================================================

HF_ENDPOINT_FALLBACK = "https://hf-mirror.com"  # 中国网络环境默认镜像
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")


def resolve_hf_cache_dir() -> str:
    """解析 HF 模型缓存目录

    优先级（实测 2026-07-20）：
      HF_HUB_CACHE > HUGGINGFACE_HUB_CACHE > HF_HUB_DOWNLOAD_ROOT > ~/.cache/huggingface/hub

    Returns:
        缓存目录绝对路径

    骨架实现：按 env 优先级解析。Sprint P0-1 step 3/7 会加 Windows 路径兼容
    与 SKILL.md §v1.21 HF env 配置同步校验。
    """
    return (
        os.environ.get("HF_HUB_CACHE")
        or os.environ.get("HUGGINGFACE_HUB_CACHE")
        or os.environ.get("HF_HUB_DOWNLOAD_ROOT")
        or DEFAULT_CACHE_DIR
    )


def resolve_hf_token() -> str:
    """解析 HuggingFace token

    优先级：
      1. 环境变量 HF_TOKEN
      2. 环境变量 HUGGING_FACE_HUB_TOKEN（旧名兼容）
      3. 配置文件 ~/.huggingface/token（骨架阶段未实现）
      4. 用户输入（None 触发）

    Returns:
        token 字符串（找不到返回 None，不抛错）

    骨架实现：只查环境变量。Sprint P0-1 step 3/7 加文件读取 + 提示信息。
    """
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def resolve_device(prefer: str = "cuda") -> str:
    """解析 device 参数

    Args:
        prefer: 期望 device("cuda" / "cpu")

    Returns:
        实际可用 device("cuda" / "cpu")
        - prefer="cuda" 且 torch.cuda.is_available() → "cuda"
        - 否则 → "cpu"（自动 fallback）

    骨架实现：try torch.cuda，失败 fallback cpu。Sprint P0-1 step 3/7
    会加更细致的 VRAM 检查与多卡选择。
    """
    if prefer == "cuda":
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"
    return prefer


# ============================================================
# 异常类型
# ============================================================

class HuggingFaceError(SkillError):
    """HuggingFace 调用失败"""
    pass


class TokenMissingError(HuggingFaceError):
    """缺少 HF token（如 pyannote 必需）"""
    def __init__(self, model_name: str):
        self.model_name = model_name
        msg = (
            f"HuggingFace token 缺失,无法使用 {model_name}\n"
            f"修复方法:\n"
            f"  1. 申请 token: https://huggingface.co/settings/tokens\n"
            f"  2. 接受模型协议: https://huggingface.co/{model_name}\n"
            f"  3. 设置环境变量: $env:HF_TOKEN = 'hf_xxxx'\n"
            f"  4. 重跑命令"
        )
        super().__init__(msg)


# ============================================================
# 客户端类
# ============================================================

class HuggingFaceClient:
    """HuggingFace 统一客户端

    用法：
        client = HuggingFaceClient()
        srt_path = client.transcribe("audio.wav", model="large-v3", lang="zh")
        diar_json = client.diarize("vocals.wav", token="hf_xxx")
        vocals = client.separate("audio.wav", model="htdemucs", device="cuda")
    """

    def __init__(self, token=None, cache_dir=None, device="cuda"):
        """初始化 HuggingFaceClient

        Args:
            token: HF token（None=自动 resolve_hf_token）
            cache_dir: 模型缓存目录（None=自动 resolve_hf_cache_dir）
            device: 期望 device("cuda"/"cpu"，自动 fallback)
        """
        self.token = token or resolve_hf_token()
        self.cache_dir = cache_dir or resolve_hf_cache_dir()
        self.device = resolve_device(device)

    # -------- Whisper ASR --------

    def transcribe(self, audio_path, model="medium", lang=None, device=None):
        """Whisper 转录 → SRT

        Args:
            audio_path: 输入音频路径（wav/mp3/mp4 都行）
            model: Whisper 模型（tiny/base/small/medium/large-v3）
            lang: 强制语言（None=自动检测，简体中文场景建议传 "zh"）
            device: 覆盖默认 device

        Returns:
            str: 输出 SRT 路径（成功）/ None（失败）

        Sprint P0-1 step 3/7 待实现：
          - 内部调 lib/asr/whisper.transcribe_to_srt()
          - 保持向后兼容（现有 transcribe_to_srt 签名）
          - 失败时 log_error + return None
        """
        raise NotImplementedError("Sprint P0-1 step 3/7 实现 HuggingFaceClient.transcribe")

    # -------- pyannote 说话人分离 --------

    def diarize(self, audio_path, token=None, device=None):
        """说话人分离 → diar.json

        Args:
            audio_path: 输入音频路径
            token: HF token（None=用 self.token）
            device: 覆盖默认 device

        Returns:
            str: 输出 diar.json 路径（成功）/ None（失败/token 缺失）

        Raises:
            TokenMissingError: token 缺失（pyannote 必需）

        Sprint P0-1 step 3/7 待实现：
          - 内部调 lib/asr/pyannote.diarize()
          - token 缺失时抛 TokenMissingError（让上层决策）
          - CUDA OOM 自动 fallback CPU
        """
        raise NotImplementedError("Sprint P0-1 step 3/7 实现 HuggingFaceClient.diarize")

    # -------- demucs 声源分离 --------

    def separate(self, audio_path, model="htdemucs", device=None, output_dir=None):
        """声源分离 → vocals.wav + other stems

        Args:
            audio_path: 输入音频路径
            model: demucs 模型（htdemucs/htdemucs_ft/mdx_q）
            device: 覆盖默认 device
            output_dir: 输出目录（None=audio_path 同级）

        Returns:
            dict: {stem_name: path}（成功）/ None（失败）
                  例：{"vocals": "audio/vocals.wav", "drums": "...", ...}

        Sprint P0-1 step 3/7 待实现：
          - 内部调 lib/separate_demucs.separate_full()
          - CUDA OOM 自动 fallback CPU（与现有 _resolve_device 一致）
          - 失败时 log_error + return None
        """
        raise NotImplementedError("Sprint P0-1 step 3/7 实现 HuggingFaceClient.separate")


__all__ = [
    "HuggingFaceClient",
    "HuggingFaceError",
    "TokenMissingError",
    "HF_ENDPOINT_FALLBACK",
    "DEFAULT_CACHE_DIR",
    "resolve_hf_cache_dir",
    "resolve_hf_token",
    "resolve_device",
]