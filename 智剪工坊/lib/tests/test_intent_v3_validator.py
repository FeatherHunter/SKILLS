"""
lib.intent_v3_validator 单元测试(plain assert,与 cover_compose 一致)
"""
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
sys.path.insert(0, str(SKILL_ROOT / "lib"))

from intent_v3_validator import validate_intent, SCHEMA_PATH


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
            "revision": 1,
            "created": "2026-07-29T10:00:00Z",
            "updated": "2026-07-29T10:00:00Z",
            "workspace": "test",
        },
        "ending": {"template": "BGM 渐弱到静音", "prompt": ""},
        "videos": [],
    }


@test("V1 · 最小 JSON 通过")
def v1():
    valid, errs = validate_intent(minimal_intent())
    assert valid, f"应通过,实际:{errs}"


@test("V2 · schema_version=2.0 拒绝")
def v2():
    intent = minimal_intent()
    intent["_meta"]["schema_version"] = "2.0"
    valid, errs = validate_intent(intent)
    assert not valid
    assert any("schema_version" in e for e in errs)


@test("V3 · video_ops 含 trim-head 拒绝")
def v3():
    intent = minimal_intent()
    intent["videos"] = [{
        "file": "x.mp4", "index": 1, "duration_sec": 60,
        "video_ops": {"trim-head": {"on": True}}
    }]
    valid, errs = validate_intent(intent)
    assert not valid
    assert any("trim-head" in e for e in errs)


@test("V4 · ending.template 缺失拒绝")
def v4():
    intent = minimal_intent()
    del intent["ending"]["template"]
    valid, errs = validate_intent(intent)
    assert not valid
    assert any("template" in e for e in errs)


@test("V5 · cover.type=image 但 images[] 缺失拒绝")
def v5():
    intent = minimal_intent()
    intent["cover"] = {"type": "image", "prompt": ""}
    valid, errs = validate_intent(intent)
    assert not valid
    assert any("images" in e for e in errs)


@test("V6 · SCHEMA_PATH 指向正确文件")
def v6():
    assert SCHEMA_PATH.exists(), f"找不到 schema: {SCHEMA_PATH}"
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema.get("title", "") == "智剪工坊 intent.json v3.0", f"schema title 不是 v3.0: {schema.get('title')}"


if __name__ == "__main__":
    print(f"Validator: {SCHEMA_PATH}")
    run_all()