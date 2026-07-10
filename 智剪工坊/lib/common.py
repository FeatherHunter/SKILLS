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
import functools
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
# 日志(支持 debug / 进度条 / 文件日志)
# ============================================================

import logging
from logging.handlers import RotatingFileHandler

# 全局状态
_LOG_VERBOSE = False
_LOG_FILE_INITIALIZED = False


def setup_logging(verbose: bool = False) -> None:
    """设置日志:verbose 模式显示 debug,默认只看 info 及以上"""
    global _LOG_VERBOSE, _LOG_FILE_INITIALIZED
    _LOG_VERBOSE = verbose
    if not _LOG_FILE_INITIALIZED:
        log_dir = Path.home() / ".zhijian" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        log_file = log_dir / f"zhijian-{datetime.now().strftime('%Y%m%d')}.log"
        logger = logging.getLogger("zhijian")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            fh = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            fh.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            ))
            logger.addHandler(fh)
        _LOG_FILE_INITIALIZED = True


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def log_info(msg: str) -> None:
    print(f"  [{_now()}] [INFO]  {msg}")
    logging.getLogger("zhijian").info(msg)


def log_warn(msg: str) -> None:
    print(f"  [{_now()}] [WARN]  {msg}", file=sys.stderr)
    logging.getLogger("zhijian").warning(msg)


def log_error(msg: str) -> None:
    print(f"  [{_now()}] [ERROR] {msg}", file=sys.stderr)
    logging.getLogger("zhijian").error(msg)


def log_debug(msg: str) -> None:
    """只在 --verbose 模式显示(总是写文件)"""
    if _LOG_VERBOSE:
        print(f"  [{_now()}] [DEBUG] {msg}")
    logging.getLogger("zhijian").debug(msg)


def log_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    logging.getLogger("zhijian").info(f"=== {title} ===")


def log_progress(current: int, total: int, msg: str = "", bar_width: int = 20) -> None:
    """
    显示进度条。例:log_progress(3, 10, "处理中")
    输出:  [12:34:56] [███████░░░░░░░░░░░░] 30% (3/10) 处理中
    """
    if total <= 0:
        return
    pct = int(current * 100 / total)
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    line = f"  [{_now()}] [{bar}] {pct:3d}% ({current}/{total}) {msg}"
    # 进度条用 \r 覆盖(不换行),但只在终端
    if current < total:
        print(line, end="\r", flush=True)
    else:
        print(line, flush=True)  # 最后一行换行


def is_verbose() -> bool:
    return _LOG_VERBOSE


def safe_batch(files: list, process_fn, desc: str = "处理") -> tuple:
    """
    批处理包装:对每个文件调用 process_fn(file),失败继续,不中断整批。
    进度条自动更新。

    Args:
        files: 文件路径列表
        process_fn: 处理函数,接收单个文件路径
        desc: 进度描述

    Returns:
        (success_count, failed_count)
    """
    success = 0
    failed = 0
    for i, f in enumerate(files, 1):
        log_progress(i, len(files), f"{desc} {Path(f).name}")
        try:
            process_fn(f)
            success += 1
        except SkillError as e:
            log_warn(f"跳过 {Path(f).name}: {e}")
            failed += 1
        except Exception as e:
            log_error(f"失败 {Path(f).name}: {e}")
            failed += 1
    return success, failed


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
        except json.JSONDecodeError as e:
            log_error(
                f"JSON 解析失败: {e}\n"
                f"  提示: API 返回格式异常,稍后重试或检查上游服务状态"
            )
            sys.exit(6)
        except (subprocess.TimeoutExpired, TimeoutError) as e:
            log_error(
                f"操作超时: {e}\n"
                f"  提示: 任务太大或网络慢,可加 --max-frames 限制处理量"
            )
            sys.exit(7)
        except OSError as e:
            # 网络 / 进程 / IO 错误
            err_msg = str(e)
            if "Errno 2" in err_msg or "WinError 2" in err_msg:
                log_error(
                    f"文件/命令找不到: {e}\n"
                    f"  提示: 检查路径,Windows 上 mavis/npm 全局命令可能在 PATH 之外"
                )
            elif "Connection" in err_msg or "Errno 11001" in err_msg:
                log_error(
                    f"网络连接失败: {e}\n"
                    f"  提示: 检查网络/代理/防火墙"
                )
            else:
                log_error(f"系统错误: {e}")
            sys.exit(8)
        except Exception as e:
            log_error(f"未预期错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(2)
    return wrapper


# === v1.13 日志装饰器 ===

def _truncate_args(args, max_len=200):
    """截断长参数（如视频路径）避免日志过长"""
    s = str(args)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def log_ffmpeg_call(func):
    """装饰器：自动记录 ffmpeg 调用的输入/输出/错误

    用法：
        @log_ffmpeg_call
        def extract_audio(input_path, output_path, fmt="wav"):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = _truncate_args(args)
        log_info(f"[{func.__module__}.{func.__name__}] 调用: args={args_repr}")
        try:
            result = func(*args, **kwargs)
            log_info(f"[{func.__module__}.{func.__name__}] 完成: result_type={type(result).__name__}")
            return result
        except FFmpegError as e:
            log_error(f"[{func.__module__}.{func.__name__}] FFmpegError: {e}")
            raise
        except Exception as e:
            log_error(f"[{func.__module__}.{func.__name__}] 异常: {type(e).__name__}: {e}")
            raise
    return wrapper
