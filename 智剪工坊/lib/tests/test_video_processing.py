"""
lib.video_processing v3.0 单元测试(plain assert)
"""
import sys
from pathlib import Path

SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
sys.path.insert(0, str(SKILL_ROOT / "lib"))

from video_processing import (
    build_video_filter,
    TARGET_RESOLUTIONS,
)


RESULTS = []
TESTS = []


def test(name):
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator


def run_all():
    for name, fn in TESTS:
        try:
            fn()
            RESULTS.append((name, True, ""))
        except AssertionError as e:
            RESULTS.append((name, False, str(e)))
        except Exception as e:
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'='*60}\nResults: {passed}/{total} PASS\n{'='*60}\n")
    for name, ok, detail in RESULTS:
        marker = "PASS" if ok else "FAIL"
        line = f"  [{marker}] {name}"
        if not ok and detail:
            line += f"\n         {detail}"
        print(line)
    if passed != total:
        sys.exit(1)


@test("V1 · speed-up 整段生效生成 filter")
def v1():
    ops = {"speed-up": {"on": True, "factor": 2.0}}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60, target_aspect="16:9")
    assert fc is not None, "应返回非空 filter_complex"
    assert "setpts=(1/2.0)*PTS" in fc, "speed-up filter 应含 setpts"
    assert "atempo=2.0000" in fc, "atempo chain 应含 2.0"


@test("V2 · slow-down 整段生效")
def v2():
    ops = {"slow-down": {"on": True, "factor": 0.5}}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60)
    assert fc is not None
    assert "setpts=(1/0.5)*PTS" in fc


@test("V3 · voice=mute 加 volume=0")
def v3():
    ops = {}
    fc, mappings = build_video_filter(ops, "mute", input_duration=60)
    assert "volume=0" in fc, "mute 应加 volume=0"


@test("V4 · fade-in 加 fade filter")
def v4():
    ops = {"fade-in": {"on": True, "sec": 2}}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60)
    assert "fade=t=in:st=0:d=2" in fc


@test("V5 · fade-out 加 fade filter")
def v5():
    ops = {"fade-out": {"on": True, "sec": 3}}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60)
    assert "fade=t=out" in fc


@test("V6 · trim-head 在 video_ops 应报错(D7)")
def v6():
    ops = {"trim-head": {"on": True, "sec": 3}}
    try:
        build_video_filter(ops, "keep", input_duration=60)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert "trim-head" in str(e), f"错误应提到 trim-head: {e}"


@test("V7 · trim-tail 在 video_ops 应报错(D7)")
def v7():
    ops = {"trim-tail": {"on": True, "sec": 3}}
    try:
        build_video_filter(ops, "keep", input_duration=60)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert "trim-tail" in str(e)


@test("V8 · cut-middle 在 video_ops 应报错(D7)")
def v8():
    ops = {"cut-middle": {"on": True}}
    try:
        build_video_filter(ops, "keep", input_duration=60)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert "cut-middle" in str(e)


@test("V9 · pin-range 在 video_ops 应报错(D7)")
def v9():
    ops = {"pin-range": {"on": True}}
    try:
        build_video_filter(ops, "keep", input_duration=60)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert "pin-range" in str(e)


@test("V10 · target-duration 在 video_ops 应报错(D7)")
def v10():
    ops = {"target-duration": {"on": True, "sec": 30}}
    try:
        build_video_filter(ops, "keep", input_duration=60)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert "target-duration" in str(e)


@test("V11 · voice=keep 不加 volume")
def v11():
    ops = {}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60)
    assert "volume=0" not in fc


@test("V12 · 空 ops 返回合理 filter")
def v12():
    ops = {}
    fc, mappings = build_video_filter(ops, "keep", input_duration=60)
    assert fc is not None, "空 ops 应仍生成可用 filter"


@test("V13 · build_video_filter 接受 dict-like video_ops")
def v13():
    # 模拟 v3.0 video_ops 真实结构
    video_ops = {
        "voice": {"mode": "keep-with-filler-removed"},
        "voice_note": "原声较小需放大",
        "notes": "海岛 vlog",
        "speed-up": {"on": True, "factor": 1.5},
        "fade-in": {"on": True, "sec": 2}
    }
    fc, mappings = build_video_filter(video_ops, "keep-with-filler-removed", input_duration=60)
    assert fc is not None
    assert "setpts" in fc  # speed-up
    assert "fade=t=in" in fc  # fade-in


@test("V14 · TARGET_RESOLUTIONS 包含 16:9")
def v14():
    assert "16:9" in TARGET_RESOLUTIONS
    assert TARGET_RESOLUTIONS["16:9"] == (1920, 1080)


if __name__ == "__main__":
    run_all()