# output_config.py - 输出根目录统一解析(基础设施奠基 · T1)
#
# G5 决策(2026-08-08 用户拍板): 输出根目录 env 优先 → 平台感知兜底
#   - 环境变量优先: CHEF_OUTPUT_DIR(兼容读,退役中) → 未来 SKILLS_DATA_DIR(预留)
#   - 平台兜底: Windows → D:/CookHub / WSL → /mnt/d/CookHub /
#     纯 Linux 无 D 盘挂载 → 提示设置 env(对齐 db_config._fallback_db_dir 先例)
#
# 用法: from output_config import get_output_root, get_output_dir
#   get_output_dir("recipes") → Path(D:/CookHub/recipes) 并 mkdir
import os
import sys
from pathlib import Path

# env 优先级: SKILLS_DATA_DIR(未来统一) > CHEF_OUTPUT_DIR(legacy 兼容读,退役中)
ENV_ORDER = ("SKILLS_DATA_DIR", "CHEF_OUTPUT_DIR")

# 平台默认输出根目录(无 env 时)
DEFAULT_ROOT_WIN = "D:/CookHub"
DEFAULT_ROOT_WSL = "/mnt/d/CookHub"


def _fallback_root():
    """平台感知兜底: Windows → D:/CookHub / WSL → /mnt/d/CookHub / 其他 → 报错提示设 env"""
    if sys.platform == "win32":
        return Path(DEFAULT_ROOT_WIN)
    d_drive = Path("/mnt/d")
    if d_drive.exists():
        return d_drive / "CookHub"
    raise RuntimeError(
        "CHEF_OUTPUT_DIR / SKILLS_DATA_DIR 未设置,且未检测到 Windows 或 WSL 的 D 盘挂载。"
        "请设置环境变量(如 CHEF_OUTPUT_DIR=D:/CookHub)后重试。"
    )


def get_output_root() -> Path:
    """输出根目录: env 优先 → 平台感知兜底(不创建)"""
    for key in ENV_ORDER:
        val = os.environ.get(key)
        if val:
            return Path(val)
    return _fallback_root()


def get_output_dir(sub: str) -> Path:
    """输出子目录: 根目录/<sub>,自动创建父目录"""
    base = get_output_root()
    target = base / sub
    target.mkdir(parents=True, exist_ok=True)
    return target
