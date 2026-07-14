# -*- coding: utf-8 -*-
"""
智剪工坊 · 工具 · 装 ffprobe

imageio-ffmpeg 只随 ffmpeg.exe，不含 ffprobe.exe。
本脚本从 npmmirror 国内镜像下载 ffmpeg-static 完整版含
ffprobe-win32-x64.gz（28MB），gunzip 解压到 imageio_ffmpeg 同一目录。

用法:
  python tools/install_ffprobe.py

幂等设计：已存在 ffprobe.exe → 跳过下载（不重复装）。
"""
import urllib.request
import gzip
import shutil
import os
from pathlib import Path

GZ_URL = 'https://registry.npmmirror.com/-/binary/ffmpeg-static/b6.1.1/ffprobe-win32-x64.gz'

def get_ffmpeg_dir():
    """探测 imageio_ffmpeg 的二进制目录"""
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe()).parent
    except ImportError:
        return Path(__file__).resolve().parent.parent.parent / 'bin'


def main():
    dest_dir = get_ffmpeg_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    exe_path = dest_dir / 'ffprobe.exe'

    if exe_path.exists() and exe_path.stat().st_size > 50 * 1024 * 1024:
        print(f'[OK] ffprobe.exe 已存在 ({exe_path.stat().st_size/1024/1024:.1f} MB)')
        return

    gz_path = dest_dir / 'ffprobe-win32-x64.gz'
    try:
        print(f'  下载 ffprobe (npmmirror, ~28MB)...')
        req = urllib.request.Request(GZ_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=600) as r:
            total = int(r.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 64 * 1024
            with open(gz_path, 'wb') as f:
                while True:
                    chunk = r.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 / total
                        print(f'\r  进度: {pct:.0f}% ({downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB)', end='', flush=True)
        print()

        print(f'  解压 → {exe_path.name}...')
        with gzip.open(gz_path, 'rb') as f_in:
            with open(exe_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out, length=chunk_size)

        exe_path.chmod(0o755)  # Linux/Mac 可执行权限
        gz_path.unlink(missing_ok=True)
        print(f'[OK] ffprobe.exe ({exe_path.stat().st_size/1024/1024:.1f} MB)')
    except Exception as e:
        print(f'[ERROR] 下载/解压失败: {e}')
        if gz_path.exists():
            gz_path.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    main()
