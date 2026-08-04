#!/usr/bin/env python3
"""
在线视频下载器 - MiniMaxCode Skill
下载任意 yt-dlp 兼容平台的视频,自动合并音视频,清理文件名。

B 站特殊处理:
  - --extractor-args "bilibili:api_host=api.bilibili.com"  绕 WBI 风控
  - Referer + User-Agent 头
  - 显式 format ID 组合,不靠 "best" 这种语义(部分 BV 没 "best")

用法:
  python video_downloader.py <视频URL> [分辨率] [输出目录]

示例:
  python video_downloader.py "https://www.bilibili.com/video/BV1S83w6SEtp/"
  python video_downloader.py "https://www.bilibili.com/video/BV1S83w6SEtp/" "480p" "D:\\Videos"
  python video_downloader.py "https://youtu.be/xxx" "720p"
"""

import os
import sys
import re
import json
import shutil
import tempfile
import subprocess
from urllib.parse import urlparse


# ============== B 站特殊处理 ==============

BILIBILI_HOSTS = (
    'bilibili.com',
    'b23.tv',
    'bili2233.cn',
)

BILIBILI_HEADERS = {
    'Referer': 'https://www.bilibili.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

BILIBILI_EXTRACTOR_ARGS = 'bilibili:api_host=api.bilibili.com'

BILIBILI_AUDIO_ID = '30216'  # 64kbps 通用音频,免费可用


def is_bilibili_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ''
    except Exception:
        return False
    return any(host == h or host.endswith('.' + h) for h in BILIBILI_HOSTS)


def pick_bilibili_formats(target_height: int) -> str:
    """
    B 站没有 'best' 语义,只能从已知 ID 里挑一档最接近 target_height 的视频流 + 通用音频流。
    高度档位(avc, 免费可用): 1080 / 720 / 480 / 360
    """
    candidates = [
        (1080, '30080'),  # avc 1080p  48MB
        (720, '30064'),   # avc 720p   21MB
        (480, '30032'),   # avc 480p   12MB
        (360, '30016'),   # avc 360p   8MB
    ]
    chosen = None
    for h, fid in candidates:
        if h <= target_height:
            chosen = fid
            break
    if not chosen:
        chosen = candidates[-1][1]  # 兜底 360p
    return f'{chosen}+{BILIBILI_AUDIO_ID}'


# ============== 通用辅助 ==============

def sanitize_filename(name: str, max_len: int = 50) -> str:
    name = os.path.basename(name)
    name = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', name)
    if len(name) > max_len:
        base, ext = os.path.splitext(name)
        base = base[:max_len - len(ext)]
        name = base + ext
    return name


def has_audio_stream(filepath: str) -> bool:
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a',
             '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', filepath],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() != ''
    except Exception:
        return False


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """用 ffmpeg -c copy 不重编码合并"""
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except subprocess.CalledProcessError as e:
        print(f'  合并失败: {e.stderr.decode("utf-8", errors="ignore")[:200]}')
        return False


# ============== 核心下载逻辑 ==============

def build_yt_dlp_cmd(url: str, output_template: str, resolution: str) -> list:
    """
    根据 URL 平台选择不同的 yt-dlp 参数。
    返回 yt-dlp 命令行(列表形式)。
    """
    is_bili = is_bilibili_url(url)
    cmd = ['yt-dlp']

    # ---- 平台特殊参数 ----
    if is_bili:
        # 1. 绕 WBI 签名风控
        cmd += ['--extractor-args', BILIBILI_EXTRACTOR_ARGS]
        # 2. 必备 headers
        for k, v in BILIBILI_HEADERS.items():
            cmd += ['--add-header', f'{k}:{v}']
        # 3. 显式 format ID(1080p / 720p / 480p / 360p 视 resolution 选)
        if resolution:
            target_h = int(resolution.rstrip('p').rstrip('P'))
        else:
            target_h = 1080
        fmt = pick_bilibili_formats(target_h)
        cmd += ['-f', fmt]
        print(f'  [B 站模式] 选定 format: {fmt}')
    else:
        # 通用平台:走默认 bestvideo+bestaudio
        target_h = int(resolution.rstrip('p').rstrip('P')) if resolution else 1080
        cmd += ['-f', f'bestvideo[height<={target_h}]+bestaudio/best']
        print(f'  [通用模式] 最高 {target_h}p')

    # ---- 通用参数 ----
    cmd += [
        '--merge-output-format', 'mp4',
        '--restrict-filenames',
        '--no-warnings',
        '--output', output_template,
        url,
    ]
    return cmd


def download_video(url: str, output_dir: str = None, resolution: str = None) -> str:
    """
    下载视频,返回本地文件绝对路径。
    """
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix='video_dl_')
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
    cmd = build_yt_dlp_cmd(url, output_template, resolution)
    print(f'>> yt-dlp 命令: {" ".join(cmd[:6])} ... <省略后续参数>')

    # ---- 调用 yt-dlp ----
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True,
                                timeout=600, encoding='utf-8')
    except subprocess.CalledProcessError as e:
        err = e.stderr or ''
        print(f'  ❌ yt-dlp 退出码 {e.returncode}')
        if err:
            print(f'  stderr(末尾 400 字符): {err[-400:]}')
        raise RuntimeError(f'yt-dlp 下载失败: {err[-400:]}')
    except subprocess.TimeoutExpired:
        raise RuntimeError('yt-dlp 超时(>600s)')

    # ---- 找生成的视频文件 ----
    files = [f for f in os.listdir(output_dir)
             if f.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4a'))]
    if not files:
        raise RuntimeError('未找到 yt-dlp 输出的视频/音频文件')

    # B 站模式:yt-dlp 不会自动 merge,得自己 ffmpeg 拼
    if is_bilibili_url(url):
        # 找视频和音频两条流
        video_files = [f for f in files if not f.endswith('.m4a')]
        audio_files = [f for f in files if f.endswith('.m4a')]
        if video_files and audio_files:
            video_path = os.path.join(output_dir, video_files[0])
            audio_path = os.path.join(output_dir, audio_files[0])
            merged_path = os.path.join(output_dir, 'merged.mp4')
            print(f'  [B 站] 音视频分离,正在合并:')
            print(f'    视频: {video_files[0]}')
            print(f'    音频: {audio_files[0]}')
            if merge_audio_video(video_path, audio_path, merged_path):
                # 删掉分离文件,只留 merged
                try:
                    os.remove(video_path)
                    os.remove(audio_path)
                except OSError:
                    pass
                final_path = merged_path
            else:
                # 合并失败,返回视频流(无音轨)
                print('  ⚠️ 合并失败,返回纯视频流')
                final_path = video_path
        else:
            # 没分离(yt-dlp 自动合并了)
            final_path = os.path.join(output_dir, files[0])
    else:
        final_path = os.path.join(output_dir, files[0])

    # ---- 文件名清理 ----
    safe_name = sanitize_filename(os.path.basename(final_path))
    safe_path = os.path.join(output_dir, safe_name)
    if safe_path != final_path:
        try:
            os.rename(final_path, safe_path)
            final_path = safe_path
        except OSError:
            pass

    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    print(f'  ✅ 下载完成: {final_path}')
    print(f'  📦 大小: {size_mb:.1f} MB')
    return final_path


# ============== CLI 入口 ==============

def main():
    if len(sys.argv) < 2:
        print('用法: python video_downloader.py <视频URL> [分辨率] [输出目录]')
        print('示例:')
        print('  python video_downloader.py "https://www.bilibili.com/video/BV1xxx"')
        print('  python video_downloader.py "https://www.bilibili.com/video/BV1xxx" "480p" "D:\\Videos"')
        sys.exit(1)

    url = sys.argv[1]
    resolution = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        result = download_video(url, output_dir, resolution)
        print(f'\n📁 最终文件: {result}')
    except Exception as e:
        print(f'\n❌ 出错: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
