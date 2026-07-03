# -*- coding: utf-8 -*-
"""
智剪工坊 · 环境验证脚本
跑这个确认智剪工坊能不能正常用。

用法:
  python verify.py             # 快检(~10 秒)
  python verify.py --full      # 全检 26 脚本(~2 分钟)
  python verify.py --script cut --cmd trim --args "--input in.mp4 --ss 0 --t 5 --output out.mp4"

返回:0 = 全过,1 = 有失败
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# 公共库
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from common import (
    get_ffmpeg_path, run_ffmpeg, log_info, log_warn, log_error,
    log_section, ensure_dir, SCRIPTS_DIR, ASSETS_DIR, safe_run,
    FFmpegError, SkillError,
)


# ============================================================
# 1. ffmpeg 探测
# ============================================================

def check_ffmpeg() -> bool:
    log_section("1. ffmpeg 探测")
    try:
        ffmpeg = get_ffmpeg_path()
        log_info(f"ffmpeg 路径: {ffmpeg}")
        result = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10,
        )
        if result.returncode != 0:
            log_error("ffmpeg 跑不起来")
            return False
        first = result.stdout.splitlines()[0] if result.stdout else "(no output)"
        log_info(f"版本: {first.strip()[:80]}")
        if "enable-libnvenc" not in result.stdout and "nvenc" not in result.stdout.lower():
            log_warn("当前 ffmpeg 没编 NVENC(用 CPU libx264,反而更稳)")
        return True
    except FFmpegError as e:
        log_error(str(e))
        return False
    except Exception as e:
        log_error(f"意外错误: {e}")
        return False


# ============================================================
# 2. Python 依赖检查
# ============================================================

REQUIRED_DEPS = [
    ("PIL", "Pillow"),
    ("numpy", "numpy"),
    ("cv2", "opencv-python"),
    ("librosa", "librosa"),
    ("soundfile", "soundfile"),
    ("faster_whisper", "faster-whisper"),
    ("edge_tts", "edge-tts"),
    ("deep_translator", "deep-translator"),
    ("rembg", "rembg"),
    ("imageio_ffmpeg", "imageio-ffmpeg"),
]


def check_deps() -> bool:
    log_section("2. Python 依赖")
    all_ok = True
    for module_name, pkg_name in REQUIRED_DEPS:
        try:
            mod = importlib.import_module(module_name)
            ver = getattr(mod, "__version__", "?")
            log_info(f"[OK]   {pkg_name:25s} {ver}")
        except ImportError:
            log_error(f"[缺失] {pkg_name:25s} pip install {pkg_name}")
            all_ok = False
    return all_ok


# ============================================================
# 3. 合成测试素材(lavfi)
# ============================================================

def gen_test_video(path: Path) -> bool:
    try:
        run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=3",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "64k",
            "-shortest",
            str(path),
        ], timeout=30)
        log_info(f"测试视频: {path}")
        return True
    except FFmpegError as e:
        log_error(f"生成测试视频失败: {e}")
        return False


def gen_test_audio(path: Path) -> bool:
    try:
        run_ffmpeg([
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:a", "libmp3lame", "-b:a", "64k",
            str(path),
        ], timeout=15)
        log_info(f"测试音频: {path}")
        return True
    except FFmpegError as e:
        log_error(f"生成测试音频失败: {e}")
        return False


def gen_test_assets() -> dict:
    log_section("3. 合成测试素材")
    tmp = Path(tempfile.gettempdir()) / "zhijian_verify"
    ensure_dir(tmp)
    assets = {
        "video": tmp / "test_video.mp4",
        "audio": tmp / "test_audio.mp3",
    }
    ok1 = gen_test_video(assets["video"])
    ok2 = gen_test_audio(assets["audio"])
    return assets if (ok1 and ok2) else {}


# ============================================================
# 4. 26 脚本的导入测试(用文件路径加载)
# ============================================================

def import_script_by_path(script_path: Path):
    """用 importlib.util 按文件路径加载模块(解决 sys.path 找不到的问题)"""
    spec = importlib.util.spec_from_file_location(
        script_path.stem,
        script_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 spec: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[script_path.stem] = module  # 缓存,免得脚本里的 `from common import` 找不到
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        # argparse --help 会 SystemExit,视为 OK
        pass
    return module


def check_script_imports() -> list:
    """对 scripts/*.py 逐个 import,返回 [(name, ok, err)]"""
    log_section("4. 26 子技能脚本导入测试")
    results = []
    for script in sorted(SCRIPTS_DIR.glob("*.py")):
        if script.name == "__init__.py":
            continue
        module_name = script.stem
        # 清缓存
        for k in list(sys.modules.keys()):
            if k in (module_name, "common"):
                del sys.modules[k]
        try:
            import_script_by_path(script)
            log_info(f"[OK]   scripts/{script.name}")
            results.append((script.name, True, ""))
        except SystemExit:
            # argparse --help 触发的 SystemExit,算过
            log_info(f"[OK]   scripts/{script.name} (with --help)")
            results.append((script.name, True, ""))
        except Exception as e:
            err = str(e).split("\n")[0][:120]
            log_error(f"[FAIL] scripts/{script.name}: {err}")
            results.append((script.name, False, err))
    return results


# ============================================================
# 5. 核心脚本冒烟测试(subprocess 跑,参数用真实 arg 名)
# ============================================================

# (脚本名, [可选子命令], [完整 args])
SMOKE_TESTS = [
    # cut 用子命令 trim
    ("cut", ["trim", "--input", "{video}", "--ss", "0", "--t", "2", "--output", "{out}/cut.mp4"]),
    # xfade 用 --out
    ("xfade", ["--a", "{video}", "--b", "{video}", "--type", "fade", "--duration", "0.5", "--out", "{out}/xfade.mp4"]),
    # reverse
    ("reverse", ["--input", "{video}", "--output", "{out}/reverse.mp4"]),
    # color_style 用 --out 和 --style
    ("color_style", ["--input", "{video}", "--style", "warm", "--intensity", "0.7", "--out", "{out}/color.mp4"]),
    # fx 用 --out 和 --effect(glow/motion_blur/... 之一,blur 不在列表里)
    ("fx", ["--input", "{video}", "--effect", "motion_blur", "--intensity", "0.5", "--out", "{out}/fx.mp4"]),
    # reframe 用 --target
    ("reframe", ["--input", "{video}", "--target", "16:9", "--output", "{out}/reframe.mp4"]),
]


def run_script_subprocess(script_name: str, args: list, timeout: int = 60) -> tuple:
    """用 subprocess 跑一个脚本,返回 (ok, msg, stderr_tail)"""
    cmd = [sys.executable, str(SCRIPTS_DIR / f"{script_name}.py")] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )
        if result.returncode == 0:
            return (True, "", "")
        err_tail = (result.stderr or "")[-200:].strip()
        return (False, f"exit {result.returncode}", err_tail)
    except subprocess.TimeoutExpired:
        return (False, f"timeout {timeout}s", "")
    except Exception as e:
        return (False, f"{type(e).__name__}: {str(e)[:80]}", "")


def smoke_test(assets: dict) -> list:
    log_section("5. 核心脚本冒烟测试(用合成素材)")
    if not assets:
        log_error("合成素材缺失,跳过冒烟测试")
        return []

    results = []
    out_dir = ensure_dir(Path(tempfile.gettempdir()) / "zhijian_verify" / "out")
    video = str(assets["video"])

    for script_name, args_template in SMOKE_TESTS:
        real_args = [a.format(video=video, out=str(out_dir)) for a in args_template]
        start = time.time()
        ok, msg, err_tail = run_script_subprocess(script_name, real_args, timeout=60)
        elapsed = time.time() - start
        status = "[OK]  " if ok else "[FAIL]"
        extra = f"  {err_tail[:80]}" if (not ok and err_tail) else ""
        log_info(f"{status} {script_name:15s} {elapsed:5.1f}s  {msg}{extra}")
        results.append((script_name, ok, msg))
    return results


# ============================================================
# 主入口
# ============================================================

@safe_run
def main():
    parser = argparse.ArgumentParser(description="智剪工坊环境验证")
    parser.add_argument("--full", action="store_true", help="跑全量 26 脚本导入+核心冒烟")
    parser.add_argument("--script", help="只验证某个脚本(模块名,如 cut)")
    parser.add_argument("--cmd", help="脚本子命令(如 cut trim)")
    parser.add_argument("--args", help="脚本参数(如 --input x.mp4 --ss 0 --t 5 --output y.mp4)")
    parser.add_argument("--skip-smoke", action="store_true", help="跳过冒烟测试")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  智剪工坊 · 环境验证")
    print("=" * 60)

    passed = []
    failed = []

    # 1. ffmpeg
    if check_ffmpeg():
        passed.append("ffmpeg")
    else:
        failed.append("ffmpeg")
        log_error("ffmpeg 缺失,后面跳过")
        print_summary(passed, failed, [], [])
        sys.exit(1)

    # 2. Python 依赖
    if check_deps():
        passed.append("依赖")
    else:
        failed.append("依赖")
        log_error("依赖缺失,后面跳过")
        print_summary(passed, failed, [], [])
        sys.exit(1)

    # 3. 合成测试素材
    assets = gen_test_assets()
    if not assets:
        failed.append("合成素材")

    # 4. 26 脚本导入测试
    import_results = check_script_imports()
    import_passed = sum(1 for _, ok, _ in import_results if ok)
    import_failed_count = len(import_results) - import_passed

    # 5. 冒烟测试
    smoke_results = []
    if assets and not args.skip_smoke:
        smoke_results = smoke_test(assets)

    # 单脚本模式
    if args.script:
        log_section(f"单脚本验证: {args.script} {args.cmd or ''}")
        cmd_args = []
        if args.cmd:
            cmd_args.append(args.cmd)
        if args.args:
            cmd_args.extend(args.args.split())
        ok, msg, err_tail = run_script_subprocess(args.script, cmd_args, timeout=120)
        if ok:
            log_info(f"[OK] {args.script} 跑通")
            passed.append(f"单脚本: {args.script}")
        else:
            log_error(f"[FAIL] {args.script}: {msg}")
            if err_tail:
                log_error(f"  stderr: {err_tail}")
            failed.append(f"单脚本: {args.script}")

    print_summary(passed, failed, import_results, smoke_results)

    if failed or import_failed_count > 0:
        sys.exit(1)
    sys.exit(0)


def print_summary(passed, failed, import_results, smoke_results):
    log_section("汇总")
    print(f"  基础检查: {len(passed)} 通过 / {len(failed)} 失败")
    for p in passed:
        print(f"    [OK]   {p}")
    for f in failed:
        print(f"    [FAIL] {f}")

    if import_results:
        ok = sum(1 for _, o, _ in import_results if o)
        print(f"\n  脚本导入: {ok}/{len(import_results)} 通过")
        for name, o, msg in import_results:
            tag = "[OK]  " if o else "[FAIL]"
            extra = f"  {msg}" if msg and not o else ""
            print(f"    {tag} {name}{extra}")

    if smoke_results:
        ok = sum(1 for _, o, _ in smoke_results if o)
        print(f"\n  冒烟测试: {ok}/{len(smoke_results)} 通过")
        for name, o, msg in smoke_results:
            tag = "[OK]  " if o else "[FAIL]"
            extra = f"  {msg}" if msg and not o else ""
            print(f"    {tag} {name}{extra}")

    print()
    if failed:
        print("  [FAIL] 有失败项,看上面排查")
    else:
        print("  [DONE] 智剪工坊环境就绪!可以开干。")


if __name__ == "__main__":
    main()
