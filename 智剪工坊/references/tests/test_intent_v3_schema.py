"""
智剪工坊 intent.json v3.0 协议校验测试
=====================================
用 jsonschema 验证 references/intent_v3.schema.json 的行为。
plain assert 风格(不引 pytest),单文件跑通。

覆盖工单 02 acceptance criteria:
  - 通过用例: 符合 spec §4 的最小完整 JSON 通过校验
  - 拒绝用例:
    - _meta.schema_version 缺失或非 "3.0"
    - videos[].video_ops 含 5 个该消失的 op
    - time_segments[].ops 含白名单外 op
    - cover.type=image 但 cover.images[] 缺失
    - ending.template 缺失
  - 输出统一错误格式(字段路径)

跑法:
    cd D:\\2Study\\StudyNotes\\SKILLS\\智剪工坊
    python references/tests/test_intent_v3_schema.py
"""
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
SCHEMA_PATH = SKILL_ROOT / "references" / "intent_v3.schema.json"

try:
    import jsonschema
except ImportError:
    print("FAIL: jsonschema not installed. pip install 'jsonschema>=4.0'")
    sys.exit(1)


# ============================================================
# 测试基础设施(沿用 cover_compose tests 风格)
# ============================================================

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
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} PASS")
    print(f"{'='*60}\n")

    for name, ok, detail in RESULTS:
        marker = "PASS" if ok else "FAIL"
        line = f"  [{marker}] {name}"
        if not ok and detail:
            line += f"\n         {detail}"
        print(line)

    if passed != total:
        sys.exit(1)


# ============================================================
# Fixtures
# ============================================================

def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_minimal_valid_intent():
    """符合 spec §4 的最小完整 JSON。"""
    return {
        "_meta": {
            "tool": "智剪工坊",
            "schema_version": "3.0",
            "revision": 1,
            "created": "2026-07-29T10:00:00Z",
            "updated": "2026-07-29T10:00:00Z",
            "workspace": "test",
        },
        "ending": {
            "template": "BGM 渐弱到静音,画面同步淡出,平稳收尾",
            "prompt": "",
        },
        "videos": [],
    }


def validate_or_error(schema, data):
    """返回 (is_valid, error_list)。统一错误格式。"""
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if not errors:
        return True, []
    formatted = []
    for err in errors:
        path = "/".join(str(p) for p in err.path) or "<root>"
        formatted.append(f"{path}: {err.message}")
    return False, formatted


# ============================================================
# Section A · validate 通过用例
# ============================================================

@test("A1 · 最小完整 JSON 通过校验")
def a1():
    schema = load_schema()
    valid, errs = validate_or_error(schema, make_minimal_valid_intent())
    assert valid, f"expected valid, got errors: {errs}"


@test("A2 · 含 tool_version 的 JSON 通过校验")
def a2():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["_meta"]["tool_version"] = "2.135"
    valid, errs = validate_or_error(schema, intent)
    assert valid, f"tool_version should be optional, got: {errs}"


@test("A3 · cover.type=image 含 images[] 通过校验")
def a3():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["cover"] = {
        "type": "image",
        "images": ["img1.png", "img2.png"]
    }
    valid, errs = validate_or_error(schema, intent)
    assert valid, f"image cover with images[] should pass, got: {errs}"


@test("A4 · 含 video + 段内合法 op 通过校验")
def a4():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "time_segments": [{
            "id": "seg_1_1",
            "start_sec": 2.0,
            "end_sec": 30.0,
            "ops": {"mute": {"on": True}, "speed-up": {"on": True, "factor": 2.0}}
        }]
    }]
    valid, errs = validate_or_error(schema, intent)
    assert valid, f"valid segment ops should pass, got: {errs}"


# ============================================================
# Section B · validate 拒绝用例
# ============================================================

@test("B1 · schema_version 缺失被拒绝")
def b1():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    del intent["_meta"]["schema_version"]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "应该拒绝(schema_version 缺失)"
    assert any("schema_version" in e for e in errs), f"错误应提到 schema_version,实际:{errs}"


@test("B2 · schema_version 非 \"3.0\" 被拒绝")
def b2():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["_meta"]["schema_version"] = "2.0"
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "应该拒绝(schema_version=2.0)"
    assert any("schema_version" in e or "3.0" in e for e in errs), f"错误:{errs}"


@test("B3 · video_ops 含 trim-head 被拒绝")
def b3():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "video_ops": {"trim-head": {"on": True, "sec": 3}}
    }]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "trim-head 是 D7 已废弃 op"
    assert any("trim-head" in e for e in errs), f"错误应提到 trim-head:{errs}"


@test("B4 · video_ops 含 cut-middle/pin-range/target-duration 都被拒绝")
def b4():
    schema = load_schema()
    for forbidden in ["cut-middle", "pin-range", "target-duration"]:
        intent = make_minimal_valid_intent()
        intent["videos"] = [{
            "file": "test.mp4",
            "index": 1,
            "duration_sec": 60,
            "video_ops": {forbidden: {"on": True}}
        }]
        valid, errs = validate_or_error(schema, intent)
        assert not valid, f"{forbidden} 应被拒绝"
        assert any(forbidden in e for e in errs), f"错误:{errs}"


@test("B5 · time_segments.ops 含白名单外 op (color) 被拒绝")
def b5():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "time_segments": [{
            "id": "seg_1_1",
            "start_sec": 0,
            "end_sec": 60,
            "ops": {"color": {"on": True}}
        }]
    }]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "段内 color 不在白名单"
    assert any("color" in e or "additional" in e.lower() for e in errs), f"错误:{errs}"


@test("B6 · time_segments.ops 含 user op(SPEC 不允许的内部标记) 被拒绝")
def b6():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "time_segments": [{
            "id": "seg_1_1",
            "start_sec": 0,
            "end_sec": 60,
            "ops": {"user": {"on": True, "note": "拆段产生"}}
        }]
    }]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "user op 不在白名单"
    assert any("user" in e or "additional" in e.lower() for e in errs), f"错误:{errs}"


@test("B7 · cover.type=image 但 images[] 缺失被拒绝")
def b7():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["cover"] = {"type": "image", "prompt": ""}
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "image cover 必须有 images[]"
    assert any("images" in e for e in errs), f"错误:{errs}"


@test("B8 · ending.template 缺失被拒绝")
def b8():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    del intent["ending"]["template"]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "ending.template 必填"
    assert any("template" in e for e in errs), f"错误:{errs}"


@test("B9 · ending.template 空字符串被拒绝(minLength=1)")
def b9():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["ending"]["template"] = ""
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "空 template 应被拒绝"


@test("B10 · video_ops.speed-up.factor 负数被拒绝")
def b10():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "video_ops": {"speed-up": {"on": True, "factor": -1.5}}
    }]
    valid, errs = validate_or_error(schema, intent)
    assert not valid, "factor 必须 > 0"


# ============================================================
# Section C · 错误格式(供 02 工单验收)
# ============================================================

@test("C1 · 错误信息含字段路径(便于 HTML 端定位)")
def c1():
    schema = load_schema()
    intent = make_minimal_valid_intent()
    intent["videos"] = [{
        "file": "test.mp4",
        "index": 1,
        "duration_sec": 60,
        "video_ops": {"trim-head": {"on": True}}
    }]
    valid, errs = validate_or_error(schema, intent)
    assert not valid
    has_path = any("videos" in e and "trim-head" in e for e in errs)
    assert has_path, f"错误应含 videos/trim-head 路径,实际:{errs}"


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    print(f"Schema: {SCHEMA_PATH}")
    run_all()