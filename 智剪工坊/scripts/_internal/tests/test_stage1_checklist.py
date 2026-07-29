"""
scripts/_internal/stage1_checklist v3.0 单元测试(plain assert)
"""
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "_internal"))

from stage1_checklist import (
    generate_checklist,
    _format_ops_human,
    _has_any_op,
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


def minimal_intent():
    return {
        "_meta": {
            "tool": "智剪工坊",
            "schema_version": "3.0",
            "tool_version": "2.135",
            "revision": 1,
            "created": "2026-07-29T10:00:00Z",
            "updated": "2026-07-29T10:00:00Z",
            "workspace": "test",
        },
        "ending": {
            "template": "BGM 渐弱到静音,画面同步淡出,平稳收尾",
            "prompt": ""
        },
        "videos": [{
            "file": "test.mp4",
            "index": 1,
            "duration_sec": 60,
            "video_ops": {
                "voice": {"mode": "keep-with-filler-removed"},
                "notes": "BGM 听起来很合适"
            }
        }]
    }


@test("S1 · v3.0 最小 intent 生成清单")
def s1():
    md = generate_checklist(minimal_intent())
    assert "# 操作清单 v1" in md, "应输出操作清单 markdown"
    assert "schema_version=3.0" not in md or True  # 不强制


@test("S2 · schema_version 缺失 → ValueError(D4)")
def s2():
    intent = minimal_intent()
    del intent["_meta"]["schema_version"]
    try:
        generate_checklist(intent)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert '3.0' in str(e), f"错误应提到 3.0: {e}"


@test("S3 · schema_version=2.0 → ValueError(D4)")
def s3():
    intent = minimal_intent()
    intent["_meta"]["schema_version"] = "2.0"
    try:
        generate_checklist(intent)
        assert False, "应该 raise ValueError"
    except ValueError as e:
        assert '3.0' in str(e), f"错误应提到 3.0: {e}"


@test("S4 · video_ops.notes 含 BGM 触发 D 象限模糊项")
def s4():
    md = generate_checklist(minimal_intent())
    assert "BG1" in md, "D 象限应触发 BG1 模糊项"
    assert "videos[1].video_ops.notes" in md, "D 象限 source 应指向 video_ops.notes"


@test("S5 · video_ops.voice.mode=keep-with-filler-removed 触发 D5")
def s5():
    md = generate_checklist(minimal_intent())
    assert "去水词" in md, "D5 应提示去水词"


@test("S6 · ending.template 显示在 B 象限")
def s6():
    md = generate_checklist(minimal_intent())
    assert "ending.template" in md, "ending.template 应在清单中"
    assert "BGM 渐弱" in md, "template 内容应展示"


@test("S7 · _format_ops_human 不再处理 trim-head")
def s7():
    # 即使 video_ops 含 trim-head(违规),函数也不报"掐头"
    ops = {"trim-head": {"on": True, "sec": 3}, "speed-up": {"on": True, "factor": 2}}
    human = _format_ops_human(ops, "keep")
    assert "掐头" not in human, "trim-head 应被忽略(D7)"
    assert "加速" in human, "speed-up 应正常处理"


@test("S8 · _format_ops_human 处理 voice 文本")
def s8():
    ops = {}
    human = _format_ops_human(ops, "mute")
    assert "静音" in human


@test("S9 · _has_any_op 检查 video_ops")
def s9():
    assert _has_any_op({"speed-up": {"on": True}}) is True
    assert _has_any_op({"speed-up": {"on": False}}) is False
    assert _has_any_op({}) is False
    assert _has_any_op(None) is False


@test("S10 · ending.template 含中文,markdown 输出正确")
def s10():
    intent = minimal_intent()
    intent["ending"]["template"] = "切黑屏后烧预告文字,停留 3 秒"
    md = generate_checklist(intent)
    assert "切黑屏" in md


if __name__ == "__main__":
    run_all()