# -*- coding: utf-8 -*-
"""
智剪工坊 · Whisper 模型一键下载工具 v1.20

设计目标(第一性原理):
  用户/AI 跑 `python tools/download_whisper_model.py <model>` 一行命令,
  不管遇到 SSL / 镜像 / 404 / PowerShell 编码 / 代理哪种坑,
  内部自动 fallback 到能用方案,跑完就成功。

支持模型: tiny / base / small / medium / large-v3
对应大小:  75MB / 150MB / 500MB / 1.5GB / 2.88GB

实测过的 4 大坑 + 解决:
  1. Python requests 走 https 间歇 SSL EOF 错误
     → 第一次先试 Python,失败 1 次后立刻 fallback 到 curl.exe
  2. huggingface.co 直连超时(中国网络常见)
     → 全程走镜像 https://hf-mirror.com
  3. 仓库文件列表写死导致 404 (medium 没有 preprocessor_config.json, large-v3 有)
     → API siblings 自动拿真实列表,404 跳过不报错
  4. Windows + PowerShell 调脚本时中文路径乱码
     → 纯 Python 内部用 UTF-8 字符串,避免 PS1 中间层

CLI:
  python tools/download_whisper_model.py <model>
  python tools/download_whisper_model.py small
  python tools/download_whisper_model.py medium
  python tools/download_whisper_model.py large-v3
  python tools/download_whisper_model.py --list       # 列出所有支持的模型
  python tools/download_whisper_model.py --status     # 看当前 cache 哪些模型
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ============================================================
# 常量(可改,不在 env 里藏)
# ============================================================
ENDPOINT = "https://hf-mirror.com"   # 镜像源(不是 huggingface.co,直连会超时)
PROXY    = "http://127.0.0.1:7890"   # Clash 默认代理(无代理自动忽略)
CURL_FALLBACK_THRESHOLD = 1          # 失败几次后 fallback 到 curl.exe (默认 1 次就切)

MODEL_REPO = "Systran/faster-whisper-{model}"

# 已知模型 + 大小(展示用,真实大小下载时拿)
MODELS = {
    "tiny":     {"size_mb":   75, "desc": "最快,精度低,适合预览/草稿"},
    "base":     {"size_mb":  150, "desc": "平衡,中文质量一般"},
    "small":    {"size_mb":  500, "desc": "推荐入门,简体输出,中文质量 ok"},
    "medium":   {"size_mb": 1500, "desc": "高精度(默认),但输出繁体"},
    "large-v3": {"size_mb": 2880, "desc": "最高精度,简体输出,推荐批量/正式"},
}


# ============================================================
# 路径解析(与 faster-whisper 保持一致)
# ============================================================
def get_cache_root():
    """解析 HF 模型缓存根路径(与 huggingface_hub 标准 env 对齐)

    优先级(与 hf_hub 内部 constants.py 一致):
      HF_HUB_CACHE > HUGGINGFACE_HUB_CACHE > HF_HUB_DOWNLOAD_ROOT (智剪工坊 v1.19 自定义, 兼容保留) > ~/.cache/huggingface/hub

    注意: 不要只设 HF_HUB_DOWNLOAD_ROOT——hf_hub 1.8.0 内部按 HF_HUB_CACHE 解析,
    设了 download_root 仍会被 hf_hub 默认 cache 路径覆盖(实测 2026-07-20)。
    推荐永久设 HF_HUB_CACHE=D:\\AI\\cache\\huggingface\\hub(智剪工坊 SKILL.md 默认值)
    """
    # 智剪工坊 v1.19 兼容保留(早期用户可能设了 HF_HUB_DOWNLOAD_ROOT)
    for env in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HUB_DOWNLOAD_ROOT"):
        val = os.environ.get(env)
        if val:
            return Path(val)
    return Path.home() / ".cache" / "huggingface" / "hub"


# ============================================================
# 工具: 进度条 + 格式化
# ============================================================
def human_size(num_bytes):
    """bytes → '1.42 GB' / '500.0 MB'"""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def progress_line(filename, downloaded, total, start_time):
    """一行进度,无外部依赖"""
    elapsed = time.time() - start_time
    speed = downloaded / elapsed if elapsed > 0 else 0
    if total > 0:
        pct = downloaded / total * 100
        eta = (total - downloaded) / speed if speed > 0 else 0
        return f"\r  {filename:30s} {pct:5.1f}%  {human_size(downloaded)}/{human_size(total)}  {human_size(speed)}/s  ETA {eta:.0f}s"
    else:
        return f"\r  {filename:30s} {human_size(downloaded)}  {human_size(speed)}/s"


# ============================================================
# API: 拿仓库真实文件列表(避免写死 404)
# ============================================================
def get_repo_files_py(repo, endpoint=ENDPOINT, timeout=15):
    """Python requests 拿文件列表 + commit hash"""
    import requests
    url = f"{endpoint}/api/models/{repo}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    sha = data.get("sha")
    if not sha:
        raise RuntimeError(f"无法从 {url} 拿到 commit hash")
    siblings = [x["rfilename"] for x in data.get("siblings", [])]
    return sha, siblings


def get_repo_files_curl(repo, endpoint=ENDPOINT):
    """curl.exe 拿文件列表(Python SSL 失败时 fallback)"""
    # 找 curl.exe
    curl_exe = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_exe:
        raise RuntimeError("curl.exe 不在 PATH,无法 fallback")
    url = f"{endpoint}/api/models/{repo}"
    cmd = [curl_exe, "-sSL", "-x", PROXY, url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"curl 调用失败: {result.stderr}")
    import json
    data = json.loads(result.stdout)
    sha = data.get("sha")
    if not sha:
        raise RuntimeError(f"无法从 {url} 拿到 commit hash")
    siblings = [x["rfilename"] for x in data.get("siblings", [])]
    return sha, siblings


# ============================================================
# 下载: Python 流式
# ============================================================
def download_file_py(repo, filename, dest, endpoint=ENDPOINT, max_retries=2, use_proxy=True):
    """Python requests 下载,带进度 + retry"""
    import requests
    url = f"{endpoint}/{repo}/resolve/main/{filename}"
    proxies = {"http": PROXY, "https": PROXY} if use_proxy else None
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            with requests.get(url, stream=True, timeout=120, allow_redirects=True, proxies=proxies) as r:
                if r.status_code == 404:
                    raise FileNotFoundError(f"404 (文件不存在): {filename}")
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                start = time.time()
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192 * 16):
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 进度(只大文件显示)
                        if total > 100 * 1024 * 1024:  # > 100MB
                            sys.stdout.write(progress_line(filename, downloaded, total, start) + "\033[K")
                            sys.stdout.flush()
                if total > 100 * 1024 * 1024:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                return downloaded
        except FileNotFoundError:
            raise  # 404 不重试
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                print(f"  ! retry {attempt+1}/{max_retries}: {filename} ({type(e).__name__})")
                continue
    raise RuntimeError(f"download failed: {last_err}")


# ============================================================
# 下载: curl.exe fallback
# ============================================================
def download_file_curl(repo, filename, dest, endpoint=ENDPOINT):
    """curl.exe 下载(Python SSL 失败时 fallback,走代理)"""
    curl_exe = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_exe:
        raise RuntimeError("curl.exe 不在 PATH,无法 fallback")
    url = f"{endpoint}/{repo}/resolve/main/{filename}"
    cmd = [
        curl_exe, "-sSL",
        "-x", PROXY,
        "-w", "\n%{size_download} %{speed_download} %{http_code}",  # 最后一行输出元数据
        "-o", str(dest),
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"curl exit={result.returncode}: {result.stderr}")
    # 解析最后一行 metadata
    meta = result.stdout.strip().split("\n")[-1]
    parts = meta.split()
    if len(parts) >= 3 and parts[-1] == "404":
        raise FileNotFoundError(f"404 (文件不存在): {filename}")
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"download empty: {filename}")
    return dest.stat().st_size


# ============================================================
# 主流程
# ============================================================
def check_disk_space(dest, need_mb):
    """下载前检查磁盘空间"""
    free_mb = shutil.disk_usage(dest).free / 1024 / 1024
    if free_mb < need_mb * 1.2:  # 留 20% buffer
        raise RuntimeError(
            f"磁盘空间不足: 需要 ~{need_mb} MB, 剩余 {free_mb:.0f} MB\n"
            f"  解决: 清理旧模型 (HF_HUB_CACHE={get_cache_root()})"
        )


def filter_files(files):
    """过滤掉不需要的元数据文件"""
    skip_exact = (".gitattributes",)
    skip_prefix = ("README", "LICENSE", "NOTICE")
    return [f for f in files if f not in skip_exact and not any(f.startswith(p) for p in skip_prefix)]


def download_model(model, cache_root=None, force_python=False):
    """主入口: 下载指定模型"""
    if model not in MODELS:
        raise ValueError(f"未知模型: {model}. 可选: {', '.join(MODELS.keys())}")

    info = MODELS[model]
    repo = MODEL_REPO.format(model=model)
    cache = cache_root or get_cache_root()

    print("=" * 60)
    print(f"Whisper {model} 下载 ({info['size_mb']} MB) - {info['desc']}")
    print("=" * 60)
    print(f"  repo:   {repo}")
    print(f"  mirror: {ENDPOINT}")
    print(f"  cache:  {cache}")
    print(f"  proxy:  {PROXY}")
    print()

    # 1. 检查磁盘空间
    check_disk_space(cache, info["size_mb"])

    # 2. 拿文件列表 (Python 优先,失败 1 次后切 curl)
    print(f"[1/3] 拿仓库文件列表 ...")
    try:
        sha, files = get_repo_files_py(repo)
        print(f"  OK (Python)  sha = {sha[:12]}")
    except Exception as e:
        print(f"  Python API fail: {type(e).__name__}: {e}")
        print(f"  fallback 到 curl.exe ...")
        try:
            sha, files = get_repo_files_curl(repo)
            print(f"  OK (curl)    sha = {sha[:12]}")
        except Exception as e2:
            raise RuntimeError(f"两种方法都拿不到文件列表:\n  Python: {e}\n  curl:   {e2}")

    files = filter_files(files)
    print(f"  共 {len(files)} 个文件: {', '.join(files)}")
    print()

    # 3. 建目录
    model_dir = cache / f"models--{repo.replace('/', '--')}"
    snap_dir  = model_dir / "snapshots" / sha
    refs_dir  = model_dir / "refs"
    snap_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    # 4. 下载每个文件
    print(f"[2/3] 下载 {len(files)} 个文件")
    # 先清理 .tmp 残留(上次下载中断留下的)
    tmp_files = list(snap_dir.glob("*.tmp"))
    if tmp_files:
        print(f"  [CLEAN] 清 {len(tmp_files)} 个 .tmp 残留(上次中断)")
        for tmp in tmp_files:
            try:
                tmp.unlink()
            except Exception:
                pass
    succeeded, skipped, failed = [], [], []
    for fn in files:
        dest = snap_dir / fn
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [SKIP] {fn} ({human_size(dest.stat().st_size)} 已存在)")
            succeeded.append(fn)
            continue

        # Python 优先 (除非 --force-curl)
        if force_python:
            try_fn = lambda: download_file_py(repo, fn, dest, use_proxy=True)
            method = "python"
        else:
            try_fn = lambda: download_file_py(repo, fn, dest, use_proxy=True)
            method = "python"

        try:
            size = try_fn()
            print(f"  [OK-{method}]   {fn}  ({human_size(size)})")
            succeeded.append(fn)
        except FileNotFoundError as e:
            print(f"  [SKIP] {fn} (404, 文件不存在于该仓库)")
            if dest.exists():
                dest.unlink()
            skipped.append(fn)
        except Exception as e:
            # Python SSL fail → fallback curl
            if not force_python and ("SSL" in str(e) or "EOF" in str(e) or "Connection" in str(e) or "MaxRetry" in str(e)):
                print(f"  Python fail ({type(e).__name__}), fallback curl ...")
                try:
                    size = download_file_curl(repo, fn, dest)
                    print(f"  [OK-curl]   {fn}  ({human_size(size)})")
                    succeeded.append(fn)
                except FileNotFoundError:
                    print(f"  [SKIP] {fn} (404)")
                    skipped.append(fn)
                except Exception as e2:
                    print(f"  [FAIL] {fn}  {e2}")
                    failed.append(fn)
            else:
                print(f"  [FAIL] {fn}  {type(e).__name__}: {e}")
                failed.append(fn)

    print()
    if failed:
        print(f"[FAIL] {len(failed)} 个文件失败: {failed}")
        return False

    if not succeeded:
        print(f"[FAIL] 一个文件都没下成功")
        return False

    # 5. 写 ref
    # 坑: huggingface_hub 1.8.0 读 refs/<revision> 时 f.read() 不 strip,
    #   写"\n"会导致 commit_hash 多一个 \n 字符, 拼路径 snapshot/<hash> 找不到
    #   实测 2026-07-20 修这个 bug 之前 D 盘 medium 一直报 LocalEntryNotFoundError
    #   修法: write_text 不加换行, 文件纯 40 hex
    print(f"[3/3] 写 ref (commit hash)")
    (refs_dir / "main").write_text(sha, encoding="ascii")  # 不要 + "\n"!

    print()
    print("=" * 60)
    print(f"DONE  model={model}  cache={snap_dir}")
    print("=" * 60)
    print()
    print("使用方法(告诉 AI 跑这个):")
    print(f'  python scripts/asr/transcribe.py -i audio.wav --srt v.srt --model {model} --lang zh')
    print()
    return True


def list_status():
    """列出 cache 里已下的模型(扫多个常见路径,防重复下载)"""
    # 智剪工坊 SKILL.md 推荐的几个常见路径(Windows 用户 D 盘 / C 盘默认 / WSL 等)
    candidate_roots = []
    # 1. 当前 env 解析的(脚本会用的)
    primary = get_cache_root()
    candidate_roots.append(("PRIMARY", primary))
    # 2. SKILL.md 默认的 D 盘(可能没设 env 但实际有模型)
    for default_path in [
        Path("D:/AI/cache/huggingface/hub"),
        Path("D:/AI/cache/huggingface"),
        Path.home() / ".cache" / "huggingface" / "hub",
    ]:
        if default_path not in (p for _, p in candidate_roots):
            candidate_roots.append(("DEFAULT", default_path))

    seen_models = {}  # name -> [(source, root, sha, size)]
    for source, root in candidate_roots:
        if not root.exists():
            continue
        for model_dir in sorted(root.glob("models--Systran--faster-whisper-*")):
            if not model_dir.is_dir():
                continue
            name = model_dir.name.replace("models--Systran--faster-whisper-", "")
            # 修 v1.20.1: f.read() 不 strip, raw 内容可能有 \n
            refs = model_dir / "refs" / "main"
            if refs.exists():
                sha = refs.read_text(encoding="ascii").strip()[:12]  # 本地 strip OK
            else:
                sha = "(no ref)"
            total = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
            seen_models.setdefault(name, []).append((source, root, sha, total))

    # 打印
    for source, root in candidate_roots:
        if not root.exists():
            continue
        models_here = [(n, entries) for n, entries in seen_models.items()
                       if any(e[1] == root for e in entries)]
        if not models_here:
            continue
        # 区分是 PRIMARY 还是 DEFAULT
        marker = "  [PRIMARY]" if source == "PRIMARY" else "  [DEFAULT]"
        print(f"{marker} {root}")
        for n, entries in models_here:
            for s, r, sha, size in entries:
                if r == root:
                    print(f"    {n:12s} sha={sha}  size={human_size(size)}")

    # 提示: 同一模型出现在多个路径 = 重复,占空间
    duplicates = {n: entries for n, entries in seen_models.items() if len(set(e[1] for e in entries)) > 1}
    if duplicates:
        print()
        print(f"⚠ 检测到 {len(duplicates)} 个模型存在多份(占重复空间):")
        for n, entries in duplicates.items():
            paths = ", ".join(str(e[1]) for e in entries)
            print(f"  {n}: {paths}")
        print(f"  → 删一份节省空间, 或设 HF_HUB_CACHE 永久指向一份")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 Whisper 模型一键下载(无坑版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/download_whisper_model.py small         # 下载 small (~500MB)
  python tools/download_whisper_model.py large-v3      # 下载 large-v3 (~2.88GB)
  python tools/download_whisper_model.py --status      # 看 cache 里已下哪些
  python tools/download_whisper_model.py --list        # 列出所有支持模型

支持的模型: tiny, base, small, medium, large-v3
        """,
    )
    parser.add_argument("model", nargs="?", help="模型名 (tiny/base/small/medium/large-v3)")
    parser.add_argument("--list", action="store_true", help="列出所有支持模型")
    parser.add_argument("--status", action="store_true", help="看 cache 状态")
    parser.add_argument("--force-curl", action="store_true", help="跳过 Python, 直接用 curl.exe")
    args = parser.parse_args()

    if args.list:
        print("支持的模型:")
        for name, info in MODELS.items():
            print(f"  {name:10s}  {info['size_mb']:>5d} MB  {info['desc']}")
        return 0

    if args.status:
        list_status()
        return 0

    if not args.model:
        parser.print_help()
        return 1

    try:
        ok = download_model(args.model, force_python=args.force_curl)
        return 0 if ok else 1
    except Exception as e:
        print(f"\n[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
