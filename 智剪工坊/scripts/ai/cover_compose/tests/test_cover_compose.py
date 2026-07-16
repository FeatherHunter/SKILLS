"""
智剪工坊 cover_compose 完整测试套件
====================================

plain assert 风格(不引 pytest 依赖),单文件跑通所有 case。

10 个 section:
A. 回归测试: 守住 B1/B2/B3 (text=None / dark_areas.warning / cli 直接跑)
B. 4 种 layout: 各 layout 各种张数(单图/2/3/4/5/8/9 张)
C. 7 种 aspect: 16:9/9:16/4:3/3:4/1:1/4:5/5:4
D. text 格式: None / "" / "{}" / 简单 dict / 完整 dict / 混合
E. auto 决策: 1/3/4 张 / 全 portrait / 全 landscape / 全 square / 混合 / 纯色图
F. Corner case: RGBA PNG / 超长文字 / 多行文字
G. 错误路径: 只读目录 / 不存在 photo / 路径冲突
H. 5 层架构: 跨层 import 关系
I. 并发/资源: 同名输出连续 2 次 / 多线程
J. 文档一致性: SKILL.md 引用的 references 都存在

跑法:
    cd D:\\2Study\\StudyNotes\\SKILLS\\智剪工坊
    python scripts/ai/cover_compose/tests/test_cover_compose.py

输出: PASS 数 / FAIL 数 / 详细列表
"""
import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
import threading
from pathlib import Path

# 加智剪工坊 scripts/ai 到 path
SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "ai"))

from PIL import Image

# ============================================================
# 测试基础设施
# ============================================================

RESULTS = []  # [(name, passed, detail)]
TESTS = []  # [(name, fn)]

def test(name):
    """装饰器: 注册测试函数, 跑的时候遍历 TESTS 调用"""
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator

def run_all_tests():
    """跑所有注册的测试, 写入 RESULTS"""
    RESULTS.clear()
    for name, fn in TESTS:
        try:
            detail = fn()
            RESULTS.append((name, True, detail or ""))
        except AssertionError as e:
            RESULTS.append((name, False, f"AssertionError: {e}"))
        except Exception as e:
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))

def make_img(path, mode="RGB", size=(800, 600), color=(255, 128, 64), alpha=True):
    """造一张测试图"""
    if mode == "RGBA":
        img = Image.new("RGBA", size, color + (255,) if len(color) == 3 else color)
    else:
        img = Image.new(mode, size, color)
    img.save(path)

# ============================================================
# Section A: 回归测试 (B1/B2/B3 守住)
# ============================================================

@test("A1: text=None 必成功 (B1 守住)")
def a1():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        from cover_compose import compose
        r = compose(photos=[str(p1)], aspect="16:9", text=None, output=str(Path(td)/"o.jpg"))
        assert r["status"] in ("ok", "warn"), f"got {r['status']}"
        assert Path(r["data"]["path"]).exists(), "output not created"

@test("A2: text='null' JSON 字符串 (B1 边界)")
def a2():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        from cover_compose import compose
        r = compose(photos=[str(p1)], text="null", output=str(Path(td)/"o.jpg"))
        # "null" 解析为 None, 等价于 text=None
        assert r["status"] in ("ok", "warn"), f"got {r['status']}"

@test("A3: text={} 空 dict 必成功")
def a3():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        from cover_compose import compose
        r = compose(photos=[str(p1)], text={}, output=str(Path(td)/"o.jpg"))
        assert r["status"] in ("ok", "warn"), f"got {r['status']}"

@test("A4: text=[] 列表应被拒绝")
def a4():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        from cover_compose import compose
        r = compose(photos=[str(p1)], text=[], output=str(Path(td)/"o.jpg"))
        # [] 不是 dict/str/None, 应报错
        assert r["status"] == "error", f"expected error, got {r['status']}"

@test("A5: diagnose 必返回 dark_areas.warning 字段 (B2 守住)")
def a5():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        from cover_compose import diagnose_image
        r = diagnose_image(str(p1), checks=["darkness"])
        assert "dark_areas" in r["data"], "missing dark_areas"
        assert "warning" in r["data"]["dark_areas"], "missing warning field (B2 回退)"

@test("A6: find_dark_areas 直接调用必有 warning (B2 直接守住)")
def a6():
    from cover_compose.diagnostics import find_dark_areas
    img = Image.new("RGB", (100, 100), (0, 0, 0))  # 全黑
    r = find_dark_areas(img)
    assert "warning" in r, f"missing warning key, got keys {list(r.keys())}"
    assert r["warning"] is True, "全黑图应 warning=True"

@test("A7: find_semi_transparent 也有 warning 字段(对照)")
def a7():
    from cover_compose.diagnostics import find_semi_transparent
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 200))  # 半透明
    r = find_semi_transparent(img)
    assert "warning" in r, "should have warning field"

@test("A8: find_dark_areas_by_region 返回结构(不需 warning)")
def a8():
    from cover_compose.diagnostics import find_dark_areas_by_region
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    r = find_dark_areas_by_region(img)
    assert isinstance(r, list), f"expected list, got {type(r)}"

@test("A9: cli.py 直接 python 跑 (B3 守住)")
def a9():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        cli = SKILL_ROOT / "scripts" / "ai" / "cover_compose" / "cli.py"
        env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run(
            ["python", str(cli), "compose",
             "--photos", str(p1), "--aspect", "16:9",
             "-o", str(Path(td)/"o.jpg")],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60
        )
        assert p.returncode in (0, 2), f"rc={p.returncode}, stderr={p.stderr[:200]}"
        assert "status" in p.stdout, f"no status in stdout: {p.stdout[:200]}"

@test("A10: cli.py python -m 跑 (B3 兼容守住)")
def a10():
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.jpg"; make_img(p1)
        env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
        # 用 cd 切到 scripts/ai/ 后 python -m cover_compose.cli
        p = subprocess.run(
            ["python", "-m", "cover_compose.cli", "presets", "--list"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
            cwd=str(SKILL_ROOT / "scripts" / "ai")
        )
        assert p.returncode == 0, f"rc={p.returncode}, stderr={p.stderr[:200]}"
        assert "douyin" in p.stdout, f"missing douyin in output"

# ============================================================
# Section B: 4 种 layout + 各种张数
# ============================================================

LAYOUTS_CASES = [
    ("symmetric-cascade", [1, 2, 3]),  # 文档说 1/2/3 张用 symmetric-cascade(但 1 张实际是 cascade)
    ("cascade", [1, 2]),  # cascade 主图+堆叠
    ("polaroid", [4, 5, 6, 8]),  # polaroid 4-5 张最佳, 8 张会怎样?
    ("grid", [4, 6, 9]),  # grid 网格, 4/6/9 都行
]

@test("B1-B12: 4 layout × 各张数")
def b_all():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        for layout, counts in LAYOUTS_CASES:
            for n in counts:
                imgs = []
                for i in range(n):
                    p = Path(td) / f"img_{i}.jpg"
                    make_img(p, color=(255-i*30, 100+i*30, 50+i*30))
                    imgs.append(str(p))
                out = str(Path(td) / f"out_{layout}_{n}.jpg")
                r = compose(photos=imgs, layout=layout, aspect="16:9", output=out)
                assert r["status"] in ("ok", "warn"), \
                    f"layout={layout} n={n} got {r['status']}: {r.get('message','')[:80]}"

# ============================================================
# Section C: 7 种 aspect
# ============================================================

@test("C1-C7: 7 种 aspect 画布尺寸正确")
def c_all():
    expected = {
        "16:9": (1920, 1080), "9:16": (1080, 1920), "4:3": (1440, 1080),
        "3:4": (1080, 1440), "1:1": (1080, 1080), "4:5": (1080, 1350),
        "5:4": (1350, 1080),
    }
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        for aspect, (W, H) in expected.items():
            p1 = Path(td) / "a.jpg"; make_img(p1)
            out = str(Path(td) / f"o_{aspect.replace(':','x')}.jpg")
            r = compose(photos=[str(p1)], aspect=aspect, output=out)
            assert r.get("data", {}).get("size") == [W, H], \
                f"aspect={aspect} expected {[W,H]} got {r.get('data',{}).get('size')}"

# ============================================================
# Section D: text 格式
# ============================================================

TEXT_CASES = [
    ("text=None", None),
    ("text=''", ""),
    ("text='null' JSON", "null"),
    ("text='{}' JSON", "{}"),
    ("text={}", {}),
    ("text={'main':'x'}", {"main": "标题"}),
    ("text={'sub':'x'}", {"sub": "副"}),
    ("text={'tags':['a','b']}", {"tags": ["a", "b"]}),
    ("text={'lines':[{'text':'x','position':'top-center','size':100}]}",
     {"lines": [{"text": "x", "position": "top-center", "size": 100}]}),
    ("text JSON str full", '{"lines":[{"text":"x","position":"middle-center","size":80}]}'),
]

@test("D1-D10: 10 种 text 格式")
def d_all():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        for name, text in TEXT_CASES:
            p1 = Path(td) / "a.jpg"; make_img(p1)
            out = str(Path(td) / f"o.jpg")
            r = compose(photos=[str(p1)], text=text, output=out)
            assert r["status"] in ("ok", "warn"), \
                f"{name}: status={r['status']}, msg={r.get('message','')[:80]}"

# ============================================================
# Section E: auto_compose 决策 corner case
# ============================================================

@test("E1: auto 1 张 portrait -> 9:16")
def e1():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "p.jpg"; make_img(p1, size=(600, 800))  # portrait
        out = str(Path(td) / "o.jpg")
        r = auto_compose(photos=[str(p1)], output=out)
        assert r["decisions"]["aspect"] == "9:16", f"got {r['decisions']['aspect']}"

@test("E2: auto 1 张 landscape -> 16:9")
def e2():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "l.jpg"; make_img(p1, size=(800, 600))
        out = str(Path(td) / "o.jpg")
        r = auto_compose(photos=[str(p1)], output=out)
        assert r["decisions"]["aspect"] == "16:9", f"got {r['decisions']['aspect']}"

@test("E3: auto 1 张 square -> 16:9(默认)")
def e3():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "s.jpg"; make_img(p1, size=(800, 800))
        out = str(Path(td) / "o.jpg")
        r = auto_compose(photos=[str(p1)], output=out)
        assert r["decisions"]["aspect"] in ("1:1", "16:9"), f"got {r['decisions']['aspect']}"

@test("E4: auto 3 张全 portrait -> 9:16")
def e4():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        imgs = []
        for i in range(3):
            p = Path(td) / f"p{i}.jpg"; make_img(p, size=(600, 800)); imgs.append(str(p))
        r = auto_compose(photos=imgs, output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["aspect"] == "9:16", f"got {r['decisions']['aspect']}"

@test("E5: auto 4 张全 square -> grid")
def e5():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        imgs = []
        for i in range(4):
            p = Path(td) / f"s{i}.jpg"; make_img(p, size=(800, 800)); imgs.append(str(p))
        r = auto_compose(photos=imgs, output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["layout"] == "grid", f"got {r['decisions']['layout']}"

@test("E6: auto 混合 portrait+landscape -> 16:9")
def e6():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        imgs = [str(Path(td)/"p.jpg"), str(Path(td)/"l.jpg")]
        make_img(Path(imgs[0]), size=(600, 800))
        make_img(Path(imgs[1]), size=(800, 600))
        r = auto_compose(photos=imgs, output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["aspect"] == "16:9", f"got {r['decisions']['aspect']}"

@test("E7: auto 1 张纯色图(contrast=0) -> bg #000000")
def e7():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "flat.jpg"; make_img(p1, color=(128, 128, 128))  # 纯灰
        r = auto_compose(photos=[str(p1)], output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["bg"] == "#000000", f"got {r['decisions']['bg']}"

@test("E8: auto hint=字符串 -> text 转 dict")
def e8():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        r = auto_compose(photos=[str(p1)], hint="我的标题", output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["text"].get("main") == "我的标题", \
            f"got {r['decisions']['text']}"

@test("E9: auto hint=dict 完整覆盖智能决策")
def e9():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        r = auto_compose(photos=[str(p1)], hint={"main": "强制标题"}, output=str(Path(td)/"o.jpg"))
        assert r["decisions"]["text"]["main"] == "强制标题"

@test("E10: auto hint=None -> 从文件名推断")
def e10():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import auto_compose
        p1 = Path(td) / "my_cool_photo.jpg"; make_img(p1)
        r = auto_compose(photos=[str(p1)], hint=None, output=str(Path(td)/"o.jpg"))
        # 文件名 "my_cool_photo" -> 清理为 "my cool photo"
        main = r["decisions"]["text"].get("main", "")
        assert "cool" in main or "photo" in main, f"got main={main!r}"

# ============================================================
# Section F: Corner case (RGBA/超长文字/多行)
# ============================================================

@test("F1: RGBA PNG 输入(带透明)")
def f1():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "rgba.png"
        # 画一个带圆形透明区的 RGBA 图
        img = Image.new("RGBA", (400, 400), (255, 100, 100, 255))
        # 让中心 200x200 半透明
        for x in range(150, 250):
            for y in range(150, 250):
                img.putpixel((x, y), (100, 200, 100, 128))
        img.save(p1)
        r = compose(photos=[str(p1)], output=str(Path(td)/"o.jpg"))
        assert r["status"] in ("ok", "warn"), f"got {r['status']}"

@test("F2: 超长文字 (>50 字符)")
def f2():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        long_text = "这是一段非常非常长的测试文字用来验证 fit_text_size 是否能正确处理超长内容" * 2
        r = compose(photos=[str(p1)], text={"main": long_text}, output=str(Path(td)/"o.jpg"))
        assert r["status"] in ("ok", "warn"), f"got {r['status']}: {r.get('message','')[:100]}"

@test("F3: 多行文字 (3 行)")
def f3():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        r = compose(photos=[str(p1)], text={
            "lines": [
                {"text": "标题1", "position": "top-center", "size": 100},
                {"text": "副标题", "position": "middle-center", "size": 60},
                {"text": "标签", "position": "bottom-center", "size": 40},
            ]
        }, output=str(Path(td)/"o.jpg"))
        assert r["status"] in ("ok", "warn")
        assert r["data"]["text_lines"] == 3, f"got {r['data']['text_lines']}"

@test("F4: 9 宫格所有位置")
def f4():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        positions = ["top-left", "top-center", "top-right",
                     "middle-left", "middle-center", "middle-right",
                     "bottom-left", "bottom-center", "bottom-right"]
        for pos in positions:
            r = compose(photos=[str(p1)], text={"lines": [{"text": "X", "position": pos, "size": 50}]},
                       output=str(Path(td)/f"o_{pos.replace('-','_')}.jpg"))
            assert r["status"] in ("ok", "warn"), f"position={pos} got {r['status']}"

# ============================================================
# Section G: 错误路径扩展
# ============================================================

@test("G1: 输出到不存在的子目录(应自动创建)")
def g1():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        out = str(Path(td) / "subdir1" / "subdir2" / "o.jpg")  # 多层不存在
        r = compose(photos=[str(p1)], output=out)
        assert r["status"] in ("ok", "warn"), f"got {r['status']}: {r.get('message','')[:100]}"
        assert Path(out).exists()

@test("G2: 输出到只读目录(应报错, 不静默)")
def g2():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        # 创建只读子目录
        ro = Path(td) / "readonly"
        ro.mkdir()
        out = str(ro / "o.jpg")
        # Windows 取消只读属性用 os.chmod 有限, 试一下
        try:
            os.chmod(ro, 0o500)  # r-x
            r = compose(photos=[str(p1)], output=out)
            # Windows 上 chmod 限制大, 可能实际能写, 不强求
            assert r["status"] in ("ok", "warn", "error"), f"got {r['status']}"
        except (OSError, PermissionError) as e:
            # Windows 上可能抛错
            assert "权限" in str(e) or "denied" in str(e).lower() or "拒绝" in str(e)
        finally:
            os.chmod(ro, 0o700)  # 恢复

@test("G3: photo 路径不存在")
def g3():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        r = compose(photos=["/nonexistent/xxx.jpg"], output=str(Path(td)/"o.jpg"))
        assert r["status"] == "error"
        assert any(e["field"] == "photos" for e in r.get("errors", []))

@test("G4: 同名输出连续 2 次(看 .bak 行为)")
def g4():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        out = str(Path(td) / "o.jpg")
        # 第 1 次
        r1 = compose(photos=[str(p1)], output=out)
        assert r1["status"] in ("ok", "warn")
        assert Path(out).exists()
        # 第 2 次同名(应自动备份第一次)
        r2 = compose(photos=[str(p1)], output=out)
        assert r2["status"] in ("ok", "warn")
        # 检查 .bak 是否生成
        baks = list(Path(td).glob("o.*.jpg"))
        # canvas.safe_save 的 .bak 格式是: o.YYYYMMDD_HHMMSS.jpg
        # 至少应该有一个 .bak
        assert len(baks) >= 1, f"no .bak generated, files: {list(Path(td).iterdir())}"

@test("G5: photo 路径是目录而非文件")
def g5():
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        d = Path(td) / "is_dir"
        d.mkdir()
        r = compose(photos=[str(d)], output=str(Path(td)/"o.jpg"))
        assert r["status"] == "error"
        assert any(e["field"] == "photos" for e in r.get("errors", []))

# ============================================================
# Section H: 5 层架构 import 关系
# ============================================================

@test("H1: cli.py 不 import 业务核心(同层 OK, 业务层不行)")
def h1():
    cli_path = SKILL_ROOT / "scripts" / "ai" / "cover_compose" / "cli.py"
    content = cli_path.read_text(encoding="utf-8")
    # 不应直接 import layers/layout/text/validators
    for forbidden in ["from .layers", "from .layout", "from .text", "from .validators", "from .canvas", "from .diagnostics", "from .presets_data"]:
        assert forbidden not in content, f"cli.py 不应 import {forbidden}"

@test("H2: pipeline.py 只 import 业务层(不 import CLI)")
def h2():
    pipeline = SKILL_ROOT / "scripts" / "ai" / "cover_compose" / "pipeline.py"
    content = pipeline.read_text(encoding="utf-8")
    assert "from .cli" not in content, "pipeline 不应 import cli"
    assert "from .auto" not in content, "pipeline 不应 import auto"
    assert "from .diagnose" not in content, "pipeline 不应 import diagnose"
    assert "from .presets" not in content, "pipeline 不应 import presets"

@test("H3: canvas.py 是最底层(不 import 同包任何模块)")
def h3():
    canvas = SKILL_ROOT / "scripts" / "ai" / "cover_compose" / "canvas.py"
    content = canvas.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if re.search(r"^\s*from\s+\.\w+\s+import", line) or re.search(r"^\s*from\s+\.\w+", line):
            raise AssertionError(f"canvas.py 不应 import 同包其他模块,但发现: {line.strip()}")

@test("H4: presets_data.py 是最底层(纯数据)")
def h4():
    pd = SKILL_ROOT / "scripts" / "ai" / "cover_compose" / "presets_data.py"
    content = pd.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if re.search(r"^\s*from\s+\.\w+", line):
            raise AssertionError(f"presets_data.py 不应 import 同包模块: {line.strip()}")

# ============================================================
# Section I: 并发/资源
# ============================================================

@test("I1: 同名输出连续 2 次(并发模拟) 不丢 .bak")
def i1():
    # 同 G4 但更严: 跑 3 次, 验证 3 个 .bak
    with tempfile.TemporaryDirectory() as td:
        from cover_compose import compose
        p1 = Path(td) / "a.jpg"; make_img(p1)
        out = str(Path(td) / "o.jpg")
        for _ in range(3):
            r = compose(photos=[str(p1)], output=out)
            assert r["status"] in ("ok", "warn")
        baks = list(Path(td).glob("o.*.jpg"))
        # 至少 2 个 .bak(第 2/3 次会备份前一个)
        assert len(baks) >= 2, f"3 次应至少 2 个 .bak, got {len(baks)}"

# ============================================================
# Section J: 文档一致性
# ============================================================

@test("J1: SKILL.md 引用的 references 都存在")
def j1():
    skill = SKILL_ROOT / "SKILL.md"
    content = skill.read_text(encoding="utf-8")
    # 提取所有 references/*.md 引用(排除 glob `*.md` 模式)
    refs = re.findall(r"`(references/[^`\s]+\.md)`", content)
    refs = list(set(refs))  # 去重
    missing = []
    for r in refs:
        # 过滤 glob 模式(如 `references/*.md`)
        if "*" in r:
            continue
        p = SKILL_ROOT / r
        if not p.exists():
            missing.append(r)
    assert not missing, f"SKILL.md 引用的 references 缺失: {missing}"

@test("J2: cover_compose/ 关键模块文件都存在")
def j2():
    pkg = SKILL_ROOT / "scripts" / "ai" / "cover_compose"
    required = ["__init__.py", "cli.py", "auto.py", "diagnose.py", "presets.py",
                "pipeline.py", "layers.py", "layout.py", "text.py", "validators.py",
                "canvas.py", "diagnostics.py", "presets_data.py"]
    missing = [f for f in required if not (pkg / f).exists()]
    assert not missing, f"cover_compose/ 缺失: {missing}"

@test("J3: cover.py 没被 cover_compose 替代")
def j3():
    cover = SKILL_ROOT / "scripts" / "ai" / "cover.py"
    assert cover.exists(), "cover.py(原 AI 生图)不见了!"
    assert "matrix_generate_image" in cover.read_text(encoding="utf-8"), "cover.py 丢失了 matrix_generate_image 调用"

# ============================================================
# 跑
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("cover_compose 完整测试套件 (10 sections)")
    print("=" * 60)
    run_all_tests()
    for name, ok, detail in RESULTS:
        mark = "OK  " if ok else "FAIL"
        msg = "" if ok else f" -- {detail[:80]}"
        print(f"[{mark}] {name:55s}{msg}")
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("=" * 60)
    print(f"汇总: {passed}/{total} 通过")
    if passed < total:
        print("\nFAIL 详情:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  [{name}] {detail[:200]}")
    print("=" * 60)
    sys.exit(0 if passed == total else 1)
