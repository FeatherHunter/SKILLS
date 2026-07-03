# -*- coding: utf-8 -*-
"""
智剪工坊 · 公共库
所有子技能脚本共享的 ffmpeg 包装、参数验证、错误处理。

设计原则:
  - 跨平台(Windows / Mac / Linux):自动从 config.json 读 ffmpeg 路径
  - 友好错误:常见错误(缺 ffmpeg、缺 Python 包、参数错)给可操作的修复命令
  - 零依赖(只用 stdlib):其他 26 个脚本可以放心 import
"""
import subprocess
import os
import re
import sys
import json
import shutil
import platform
from pathlib import Path
from typing import List, Optional, Union


# ============================================================
# 错误处理(友好版)
# ============================================================

class SkillError(Exception):
    """skill 自定义错误基类"""
    pass


class FFmpegError(SkillError):
    """ffmpeg 执行失败"""
    def __init__(self, cmd, stderr, hint=None):
        self.cmd = cmd
        self.stderr = stderr
        self.hint = hint
        msg = f"ffmpeg 执行失败\n命令: {' '.join(cmd[:6])}\nstderr: {(stderr or '无输出')[-300:]}"
        if hint:
            msg += f"\n提示: {hint}"
        super().__init__(msg)


class ParamError(SkillError):
    """参数错误"""
    pass


class DependencyError(SkillError):
    """依赖缺失"""
    def __init__(self, package, install_cmd=None):
        self.package = package
        self.install_cmd = install_cmd or f"pip install {package}"
        super().__init__(
            f"缺少依赖: {package}\n"
            f"修复: {self.install_cmd}\n"
            f"或: pip install -r requirements.txt"
        )


# ============================================================
# 配置(读 config.json,跨平台找 ffmpeg)
# ============================================================

SKILL_ROOT = Path(__file__).parent.parent
CONFIG_PATH = SKILL_ROOT / "config.json"


def load_config() -> dict:
    """从 config.json 读配置;读不到返回空 dict"""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get_ffmpeg_path() -> str:
    """
    探测 ffmpeg 路径(优先级):
      1. config.json 里的 ffmpeg_path
      2. imageio_ffmpeg 包的二进制(自动装)
      3. 系统 PATH
      4. Windows 默认路径(向后兼容)
    """
    # 1. config.json
    cfg = load_config()
    p = cfg.get("ffmpeg_path")
    if p and os.path.exists(p):
        return p

    # 2. imageio_ffmpeg
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(p):
            return p
    except ImportError:
        pass

    # 3. 系统 PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 4. Windows 兼容路径
    if platform.system() == "Windows":
        win_default = r"D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe"
        if os.path.exists(win_default):
            return win_default

    raise FFmpegError(
        ["ffmpeg"],
        "在 config.json / imageio_ffmpeg / 系统 PATH 都找不到 ffmpeg",
        hint=(
            "修复:1) python -m pip install imageio-ffmpeg\n"
            "      2) 或下载 ffmpeg 放 PATH:https://ffmpeg.org/download.html\n"
            "      3) 或重跑 setup.bat / setup.sh"
        ),
    )


# 向后兼容(老代码用 DEFAULT_FFMPEG)
def _default_ffmpeg_compat() -> str:
    try:
        return get_ffmpeg_path()
    except FFmpegError:
        return "ffmpeg"  # 留个占位,实际调用时会再探测


DEFAULT_FFMPEG = _default_ffmpeg_compat()


# ============================================================
# ffmpeg 包装
# ============================================================

def run_ffmpeg(args: List[str], timeout: int = 3600, ffmpeg_path: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    通用 ffmpeg 执行包装。
    - 自动加 -y(覆盖输出)
    - 自动捕获 stdout/stderr
    - 失败抛 FFmpegError(带 hint)
    """
    ffmpeg = ffmpeg_path or get_ffmpeg_path()
    cmd = [ffmpeg, "-y"] + list(args)
    log_info(f"ffmpeg {' '.join(cmd[:8])}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )
    except FileNotFoundError:
        raise FFmpegError(
            cmd, "ffmpeg 可执行文件不存在",
            hint="跑 setup.bat / setup.sh 装 ffmpeg,或重装 imageio-ffmpeg",
        )
    except subprocess.TimeoutExpired:
        raise FFmpegError(cmd, f"ffmpeg 超时 ({timeout}s)")

    if result.returncode != 0:
        # 智能 hint:从 stderr 抓线索
        hint = _extract_hint(result.stderr or "")
        raise FFmpegError(cmd, result.stderr or "无 stderr 输出", hint=hint)
    return result


def _extract_hint(stderr: str) -> Optional[str]:
    """从 ffmpeg 错误信息里抽最可能的修复建议"""
    s = stderr.lower()
    if "no such file" in s or "does not exist" in s:
        return "检查输入文件路径是否正确"
    if "permission denied" in s:
        return "检查文件/目录权限(试试换个输出目录)"
    if "invalid argument" in s or "option not found" in s:
        return "ffmpeg 版本不支持这个参数。试试升级 ffmpeg 或换 filter"
    if "no space left" in s:
        return "磁盘满,清一下空间再跑"
    if "connection refused" in s or "unable to connect" in s:
        return "网络问题,检查代理/防火墙"
    return None


def get_duration(video_path: Union[str, Path], ffmpeg_path: Optional[str] = None) -> float:
    """获取视频时长(秒)"""
    ffmpeg = ffmpeg_path or get_ffmpeg_path()
    cmd = [ffmpeg, "-i", str(video_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise FFmpegError(cmd, f"无法解析时长: {video_path}", hint="文件可能损坏,或不是视频")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def get_fps(video_path: Union[str, Path], ffmpeg_path: Optional[str] = None) -> float:
    """获取视频帧率"""
    ffmpeg = ffmpeg_path or get_ffmpeg_path()
    cmd = [ffmpeg, "-i", str(video_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    match = re.search(r"(\d+(?:\.\d+)?)\s*fps", result.stderr)
    if not match:
        raise FFmpegError(cmd, f"无法解析帧率: {video_path}", hint="文件可能不是视频,或编码异常")
    return float(match.group(1))


# ============================================================
# 通用滤镜
# ============================================================

UNIFIED_VIDEO_FILTER = (
    "scale={res}:force_original_aspect_ratio=decrease,"
    "pad={res}:(ow-iw)/2:(oh-ih)/2:black,"
    "setsar=1,fps={fps}"
)
"""统一竖屏 vlog 滤镜(1080x1920 + 30fps + 加黑边)"""


def unified_vf(res: str = "1080:1920", fps: int = 30) -> str:
    """返回统一滤镜字符串"""
    return UNIFIED_VIDEO_FILTER.format(res=res, fps=fps)


# ============================================================
# 通用编码参数
# ============================================================

DEFAULT_ENCODE_ARGS = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-c:a", "aac", "-b:a", "128k",
    "-movflags", "+faststart",
]
"""默认编码参数(避开 NVENC bug,稳定)"""


# ============================================================
# 参数验证
# ============================================================

def require_param(name: str, value) -> None:
    """必填参数检查"""
    if value is None:
        raise ParamError(f"缺少必填参数: --{name}")


def validate_resolution(res: str) -> None:
    """验证分辨率格式 WxH"""
    if not re.match(r"^\d+x\d+$", res):
        raise ParamError(f"分辨率格式错误: {res} (应为 1080x1920 格式)")


def validate_positive_number(name: str, value: float) -> None:
    """验证正数"""
    if value <= 0:
        raise ParamError(f"{name} 必须为正数: {value}")


def require_file(path: Union[str, Path], hint: str = "") -> None:
    """检查文件存在"""
    if not os.path.exists(path):
        msg = f"文件不存在: {path}"
        if hint:
            msg += f"\n提示: {hint}"
        raise ParamError(msg)


# ============================================================
# 路径工具
# ============================================================

def ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在,不存在则创建"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def find_files(directory: Union[str, Path], patterns: List[str]) -> List[Path]:
    """按 glob pattern 查找文件"""
    p = Path(directory)
    results = []
    for pattern in patterns:
        results.extend(p.glob(pattern))
    return sorted(set(results))


REFERENCES_DIR = SKILL_ROOT / "references"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
ASSETS_DIR = SKILL_ROOT / "assets"


def list_sub_skills() -> List[Path]:
    """列出所有子技能文档"""
    return sorted(REFERENCES_DIR.glob("*.md"))


# ============================================================
# 日志
# ============================================================

def log_info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def log_warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def log_error(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)


def log_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ============================================================
# 异常处理装饰器(友好版)
# ============================================================

def safe_run(func):
    """
    统一异常处理装饰器。
    - SkillError:打印可读消息,exit 1
    - ImportError:告诉用户装哪个包,exit 3
    - KeyboardInterrupt:用户中断,exit 130
    - 其他:打印 traceback,exit 2
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SkillError as e:
            log_error(str(e))
            sys.exit(1)
        except ImportError as e:
            # 缺包:解析出包名给安装命令
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e).split()[-1]
            log_error(
                f"缺少 Python 包: {missing}\n"
                f"  修复: pip install {missing}\n"
                f"  或:   pip install -r requirements.txt"
            )
            sys.exit(3)
        except KeyboardInterrupt:
            log_warn("用户中断")
            sys.exit(130)
        except FileNotFoundError as e:
            log_error(f"文件不存在: {e}\n  提示: 检查路径拼写,或用绝对路径")
            sys.exit(4)
        except PermissionError as e:
            log_error(f"权限不足: {e}\n  提示: 换个输出目录,或以管理员身份运行")
            sys.exit(5)
        except Exception as e:
            log_error(f"未预期错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(2)
    return wrapper
