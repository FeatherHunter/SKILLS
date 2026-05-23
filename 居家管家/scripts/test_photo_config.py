#!/usr/bin/env python3
"""测试照片目录配置"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from home_manager.db import PHOTOS_DIR

def test_photo_config():
    print("=" * 60)
    print("照片目录配置测试")
    print("=" * 60)

    # 检查环境变量
    env_dir = os.environ.get("HOME_PHOTOS_DIR")
    print(f"环境变量 HOME_PHOTOS_DIR: {env_dir or '(未设置)'}")
    print(f"最终照片目录: {PHOTOS_DIR}")
    print(f"目录是否存在: {PHOTOS_DIR.exists()}")

    # 显示目录内容
    if PHOTOS_DIR.exists():
        photos = list(PHOTOS_DIR.glob("*.jpg")) + list(PHOTOS_DIR.glob("*.png"))
        print(f"目录中的照片数量: {len(photos)}")
        if photos:
            print("\n前5张照片:")
            for i, p in enumerate(photos[:5], 1):
                print(f"  {i}. {p.name}")
    else:
        print("\n[警告] 目录不存在，请检查配置或创建目录")

    print("\n" + "=" * 60)
    print("配置建议：")
    print("=" * 60)
    if not env_dir:
        print("* 当前使用默认配置（技能目录下的 photos 文件夹）")
        print("* 如需自定义路径，请设置环境变量 HOME_PHOTOS_DIR")
    else:
        print(f"* 已配置自定义路径: {env_dir}")
        if not PHOTOS_DIR.exists():
            print("* [警告] 建议创建该目录或检查路径是否正确")

    return 0

if __name__ == "__main__":
    sys.exit(test_photo_config())
