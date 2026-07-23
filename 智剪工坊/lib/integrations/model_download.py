# -*- coding: utf-8 -*-
"""
智剪工坊 · 模型下载集成层（v1.21 新建）

封装 3 个模型下载场景（原散落在 tools/）：

  | # | 工具                          | 原脚本                            | 用途          |
  |---|-------------------------------|-----------------------------------|---------------|
  | 1 | download_whisper_model.py     | tools/download_whisper_model.py   | Whisper 模型  |
  | 2 | install_ffprobe.py            | tools/install_ffprobe.py          | ffprobe 二进制|
  | 3 | mediapipe face_landmarker     | scripts/ai/beauty.py              | 人脸关键点模型|

现有踩过的 4 大坑（已封进 download_whisper_model.py，本次统一抽象）：
  1. Python SSL EOF：`requests.get` 间歇失败 → 自动 fallback `curl.exe`
  2. huggingface.co 直连超时：中国网络 → 走 https://hf-mirror.com
  3. 仓库文件列表 404：写死文件名 vs 实际 siblings 不同 → API siblings 拿真实列表
  4. PowerShell 中文路径乱码：PS1 中间层 GBK → 纯 Python UTF-8

设计要点：
  - 统一 4 大坑处理（任一模型下载都受益）
  - 统一幂等（已存在 → 跳过，不重复下载）
  - 统一进度条（输出到 stderr，避免污染 stdout JSON）
  - 统一缓存路径（与 HF client 共用 resolve_hf_cache_dir）

对外接口：
    ModelDownloader().download(model_name, mirror="https://hf-mirror.com", ...)
    ModelDownloader().check_exists(model_name) -> bool

骨架状态（Sprint P0-1 step 1/7）：
  - 类与函数签名已定
  - 实现细节待 P0-1 step 4/7 填充
"""
from pathlib import Path
import sys

# 引导：保证 lib/common.py 可被找到
_LIB_DIR = Path(__file__).parent.parent
if str(_LIB_DIR) not in sys.path:
    sys.path.append(str(_LIB_DIR))

from common import SkillError, log_info, log_warn  # noqa: E402


# ============================================================
# 镜像源（与 lib/integrations/huggingface.py 共享）
# ============================================================

NPMMIRROR_FFMPEG_URL = "https://registry.npmmirror.com/-/binary/ffmpeg-static"
HF_MIRROR_URL = "https://hf-mirror.com"


# ============================================================
# 异常类型
# ============================================================

class ModelDownloadError(SkillError):
    """模型下载失败"""
    pass


class ModelIntegrityError(ModelDownloadError):
    """模型文件完整性校验失败"""
    pass


# ============================================================
# 客户端类
# ============================================================

class ModelDownloader:
    """模型统一下载器

    用法：
        dl = ModelDownloader()
        if not dl.check_exists("large-v3"):
            dl.download("large-v3")  # 自动走镜像 + SSL fallback
    """

    def __init__(self, mirror=HF_MIRROR_URL, cache_dir=None):
        """初始化 ModelDownloader

        Args:
            mirror: HF 镜像源（默认 https://hf-mirror.com）
            cache_dir: 模型缓存目录（None=自动 resolve_hf_cache_dir）
        """
        # 注意：骨架阶段允许循环引用 huggingface.resolve_hf_cache_dir
        # Sprint P0-1 step 4/7 会拆到独立小函数避免循环
        try:
            from integrations.huggingface import resolve_hf_cache_dir
            self.cache_dir = cache_dir or resolve_hf_cache_dir()
        except Exception:
            # huggingface 模块尚未安装或导入失败时,用默认
            from integrations.huggingface import DEFAULT_CACHE_DIR
            self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.mirror = mirror
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def check_exists(self, model_name, min_size_mb=10):
        """检查模型是否已下载完整

        Args:
            model_name: 模型名（如 "large-v3"）
            min_size_mb: 最小文件大小（MB），小于此值视为不完整

        Returns:
            bool: True=已下载完整，False=未下载或不完整

        Sprint P0-1 step 4/7 待实现：
          - 扫描 self.cache_dir 下 {model_name}/ 目录
          - 检查 model.bin / pytorch_model.bin 等关键文件大小
          - 返回 bool
        """
        raise NotImplementedError("Sprint P0-1 step 4/7 实现 ModelDownloader.check_exists")

    def download(self, model_name, force=False, force_curl=False):
        """下载模型（带 4 大坑处理）

        Args:
            model_name: 模型名
            force: 强制重下（忽略 check_exists）
            force_curl: 强制走 curl.exe（SSL 严重失败时用）

        Returns:
            str: 模型本地路径（成功）/ None（失败）

        Raises:
            ModelDownloadError: 下载失败
            ModelIntegrityError: 下载后校验失败

        Sprint P0-1 step 4/7 待实现：
          1. check_exists 检查（非 force 时跳过已存在的）
          2. 优先 requests.get(self.mirror) 走 Python
          3. SSL EOF 时自动 fallback curl.exe（非 force_curl 时）
          4. 进度条输出到 stderr（"\r 进度: 50% (100/200 MB)"）
          5. API siblings 拿真实文件列表（避免 404）
          6. 下载完做 size sanity check
        """
        raise NotImplementedError("Sprint P0-1 step 4/7 实现 ModelDownloader.download")

    def download_ffprobe(self, force=False):
        """下载 ffprobe（特殊：从 npmmirror 走，不走 HF）

        Sprint P0-1 step 4/7 待实现：
          - 从 NPMMIRROR_FFMPEG_URL/b6.1.1/ffprobe-win32-x64.gz 下载
          - gunzip 解压到 imageio_ffmpeg 同目录
          - 幂等：已存在 > 50MB → 跳过
        """
        raise NotImplementedError("Sprint P0-1 step 4/7 实现 ModelDownloader.download_ffprobe")


__all__ = [
    "ModelDownloader",
    "ModelDownloadError",
    "ModelIntegrityError",
    "NPMMIRROR_FFMPEG_URL",
    "HF_MIRROR_URL",
]