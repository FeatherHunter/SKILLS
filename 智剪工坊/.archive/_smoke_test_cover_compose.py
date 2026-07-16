"""Smoke test: 验证 cover_compose 重组后能否正常 import 和调用"""
import sys
import os
from pathlib import Path

# 加智剪工坊 scripts/ai 到 path
SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "ai"))

print("=" * 60)
print("Smoke test: cover_compose 重组后导入验证")
print("=" * 60)

# 1. import 包
try:
    from cover_compose import compose, auto_compose, parse_text_spec, ASPECT_RATIOS
    print("[1/5] OK 包导入成功 (compose / auto_compose / parse_text_spec / ASPECT_RATIOS)")
except Exception as e:
    print(f"[1/5] ✗ 包导入失败: {e}")
    sys.exit(1)

# 2. 检查 ASPECT_RATIOS
expected_aspects = {"16:9", "9:16", "4:3", "3:4", "1:1", "4:5", "5:4"}
actual = set(ASPECT_RATIOS.keys())
if expected_aspects == actual:
    print(f"[2/5] ✓ ASPECT_RATIOS 白名单完整 ({len(actual)} 个)")
else:
    print(f"[2/5] ✗ ASPECT_RATIOS 不匹配: 期望 {expected_aspects}, 实际 {actual}")
    sys.exit(1)

# 3. 测试 parse_text_spec (简单格式)
text_dict = {"main": "14 天", "sub": "-7 斤"}
text_spec, err = parse_text_spec(text_dict)
if err is None and text_spec and "lines" in text_spec and len(text_spec["lines"]) == 2:
    print(f"[3/5] ✓ parse_text_spec 简单格式: 2 行文字 ({[l['text'] for l in text_spec['lines']]})")
else:
    print(f"[3/5] ✗ parse_text_spec 失败: err={err}, spec={text_spec}")
    sys.exit(1)

# 4. 准备测试图片(用 PIL 现场造 3 张不同色)
from PIL import Image
import tempfile
tmpdir = Path(tempfile.gettempdir()) / "cover_compose_smoke"
tmpdir.mkdir(parents=True, exist_ok=True)

test_imgs = []
for i, color in enumerate([(255, 100, 100), (100, 255, 100), (100, 100, 255)]):
    p = tmpdir / f"test_{i}.jpg"
    Image.new("RGB", (800, 600), color).save(p)
    test_imgs.append(str(p))
print(f"[4/5] ✓ 测试图片准备: {test_imgs}")

# 5. 跑 compose(手动挡) + auto_compose(自动挡)
out_jpg = tmpdir / "out.jpg"
result = compose(
    photos=test_imgs,
    layout="symmetric-cascade",
    aspect="16:9",
    text={"main": "TEST", "sub": "compose"},
    bg="#000000",
    output=str(out_jpg),
)
if result["status"] in ("ok", "warn") and Path(result["data"]["path"]).exists():
    size_kb = Path(result["data"]["path"]).stat().st_size / 1024
    print(f"[5/5] ✓ compose 成功: status={result['status']}, "
          f"size={result['data']['size']}, path={result['data']['path']} ({size_kb:.1f}KB), "
          f"applied={len(result['data']['applied_layers'])} 图层")
else:
    print(f"[5/5] ✗ compose 失败: {result}")
    sys.exit(1)

# 6. auto_compose(只传 photos,自动决策)
out_auto = tmpdir / "out_auto.jpg"
result_auto = auto_compose(
    photos=test_imgs[:2],  # 2 张
    hint=None,
    output=str(out_auto),
)
if result_auto["status"] in ("ok", "warn") and Path(result_auto["data"]["path"]).exists():
    size_kb = Path(result_auto["data"]["path"]).stat().st_size / 1024
    print(f"[6/6] ✓ auto_compose 成功: status={result_auto['status']}, "
          f"decisions={result_auto['decisions']['layout']}/{result_auto['decisions']['aspect']}, "
          f"size={result_auto['data']['size']} ({size_kb:.1f}KB)")
else:
    print(f"[6/6] ✗ auto_compose 失败: {result_auto}")
    sys.exit(1)

print("=" * 60)
print("✅ Smoke test 全部通过 — 重组后的 cover_compose 工作正常")
print("=" * 60)
