"""
私家大厨 · 做菜域测试(T8 · 2026-08-09)

覆盖:
- cook-4 断点续做: cooking_render --step N 注入 __START_STEP__ + #step 锚点 + 复制进度按钮
- 完结闭环: 祝贺页 4 个单动作 prompt 按钮(评分/点评/反思/完成拍照,完成拍照 = 预告式)
- 作品照片: photo_utils 值类型判定表 + 三目录契约命名 + chef:// 解析
- history_manager add --photo chef:// 入库
"""
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
SKILL_DIR = SCRIPT_DIR.parent

# ── 模块级环境(先于 db_config/init_db import · 同 test_add.py 模式)──
# DB 路径在 db_config import 时缓存,必须模块级设置,不能依赖 fixture 动态改
_TMP = Path(tempfile.mkdtemp(prefix="chef_t8_test_"))
os.environ["SKILLS_DB_PATH"] = str(_TMP)
os.environ["CHEF_OUTPUT_DIR"] = str(_TMP / "out")
sys.path.insert(0, str(SCRIPT_DIR))

import init_db  # noqa: E402
init_db.init_db()

from db import execute, query  # noqa: E402
import db_config  # noqa: E402

import photo_utils  # noqa: E402


def _child_env():
    """子进程环境: 必须指向进程内缓存 DB_PATH 的目录。
    并行域测试模块(如 test_派生.py)会在模块级改 os.environ + 缓存 db_config.DB_PATH,
    收集顺序不定,子进程若用 _TMP 会打开空库(no such table)→ 以缓存的 DB_PATH 为准"""
    env = {k: v for k, v in os.environ.items()}
    env["SKILLS_DB_PATH"] = str(Path(db_config.DB_PATH).parent)
    env["CHEF_OUTPUT_DIR"] = str(_TMP / "out")
    return env


def _make_recipe(name):
    """最小菜谱(3 步)入模块级临时库(L1 全字段必填)"""
    rid = str(uuid.uuid4())
    execute("INSERT INTO recipes (id, name, description, difficulty, servings, total_time_minutes, status, photo_url, source, source_url) VALUES (?, ?, ?, '简单', 2, 15, '未做', 'https://picsum.photos/seed/x/200/200', '测试', 'https://example.com/source')",
            (rid, name, f"{name}的测试描述"))
    for i in range(1, 4):
        execute("INSERT INTO cooking_steps (id, recipe_id, sequence, action, duration_minutes, heat_level, temperature, expected_result) VALUES (?, ?, ?, ?, 5, '中火', '常温', 'ok')",
                (str(uuid.uuid4()), rid, i, f"步骤{i}"))
    return rid


# ── 值类型判定表(photo_utils)──────────────────────────────
class TestClassifyMedia:
    """G5 值类型判定表: chef:// 本地 / 图片扩展名·图床域名 / 视频平台·视频扩展名 / 其他 URL"""

    def test_chef_is_local(self):
        assert photo_utils.classify_media("chef://work_photos/辣椒炒肉__work__20260809.jpg") == "local"

    def test_image_ext(self):
        for v in ("https://x.com/a.jpg", "https://x.com/b.PNG", "https://x.com/c.webp"):
            assert photo_utils.classify_media(v) == "image", v

    def test_image_host(self):
        for v in ("https://picsum.photos/seed/x/200/200", "https://imgur.com/abc", "https://unsplash.com/p/1"):
            assert photo_utils.classify_media(v) == "image", v

    def test_video_ext(self):
        assert photo_utils.classify_media("https://x.com/v.mp4") == "video"

    def test_video_platform(self):
        for v in ("https://www.bilibili.com/video/BV1xx", "https://youtube.com/watch?v=x", "https://vimeo.com/1"):
            assert photo_utils.classify_media(v) == "video", v

    def test_plain_link(self):
        for v in ("https://baike.baidu.com/item/x", "https://www.xiaohongshu.com/explore/abc"):
            assert photo_utils.classify_media(v) == "link", v

    def test_empty_is_link(self):
        assert photo_utils.classify_media(None) == "link"
        assert photo_utils.classify_media("") == "link"


class TestThreeDirContract:
    """三目录契约: photos/ 成品照 + source_photos/ 来源图 + work_photos/ 作品照"""

    def test_work_photo_naming(self):
        rel = photo_utils.work_photo_relpath("辣椒炒肉", ".jpg", "20260809")
        assert rel == "work_photos/辣椒炒肉__work__20260809.jpg"

    def test_source_photo_naming(self):
        rel = photo_utils.relpath_for("辣椒炒肉", "source", "20260809", "png")
        assert rel == "source_photos/辣椒炒肉__source__20260809.png"

    def test_photo_naming(self):
        rel = photo_utils.relpath_for("辣椒炒肉", "photo", "20260809", "JPG")
        assert rel == "photos/辣椒炒肉__photo__20260809.jpg"

    def test_unknown_shortcode_rejected(self):
        with pytest.raises(ValueError):
            photo_utils.relpath_for("x", "bad", "20260809", "jpg")

    def test_work_photo_date_default(self):
        rel = photo_utils.work_photo_relpath("x", ".jpg")
        assert re.match(r"^work_photos/x__work__\d{8}\.jpg$", rel)


class TestResolveChef:
    def test_resolve_local(self, tmp_path):
        p = photo_utils.resolve_chef("chef://work_photos/a__work__1.jpg", tmp_path)
        assert p == tmp_path / "work_photos" / "a__work__1.jpg"

    def test_reject_non_chef(self, tmp_path):
        with pytest.raises(ValueError):
            photo_utils.resolve_chef("https://x.com/a.jpg", tmp_path)


class TestBuildMediaHtml:
    def test_local_renders_img_file(self, tmp_path):
        html = photo_utils.build_media_html("chef://photos/a__photo__1.jpg", tmp_path)
        assert html.startswith('<img src="file:///')
        assert 'loading="lazy"' in html

    def test_image_renders_img(self, tmp_path):
        html = photo_utils.build_media_html("https://picsum.photos/seed/x/1/1", tmp_path)
        assert html.startswith('<img src="https://')

    def test_video_renders_link_with_emoji(self, tmp_path):
        html = photo_utils.build_media_html("https://www.bilibili.com/video/BV1xx", tmp_path)
        assert '🎬 视频' in html
        assert html.startswith('<a href=')

    def test_plain_link(self, tmp_path):
        html = photo_utils.build_media_html("https://baike.baidu.com/item/x", tmp_path)
        assert '查看原文' in html
        assert html.startswith('<a href=')

    def test_empty(self, tmp_path):
        assert photo_utils.build_media_html(None, tmp_path) == ""


# ── cook-4 断点续做(cooking_render --step)─────────────────
class TestCookingRenderStartStep:
    """断点续做: --step N → 注入 __START_STEP__ + 场景 cook-4 + #step 锚点"""

    def _render(self, tmp_path, recipe, extra_args=()):
        out = tmp_path / "cook.html"
        cmd = [sys.executable, str(SCRIPT_DIR / "cooking_render.py"), "render", recipe["name"]] + list(extra_args) + ["--output", str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 0, res.stderr
        return out.read_text(encoding="utf-8"), out

    def test_step_gt_1_injects_start_step_and_cook4(self, tmp_path):
        name = f"断点测试菜_{uuid.uuid4().hex[:6]}"
        _make_recipe(name)
        html, out = self._render(tmp_path, {"name": name}, ["--step", "3"])
        assert "window.__START_STEP__ = 3" in html
        # 08 复制数据 scene 应为 cook-4
        assert '"scene_id":"cook-4"' in html
        # 复制日志思考链带断点续做
        assert "断点续做" in html

    def test_step_beyond_total_clamps_to_last(self, tmp_path):
        name = f"钳制菜_{uuid.uuid4().hex[:6]}"
        _make_recipe(name)
        html, _ = self._render(tmp_path, {"name": name}, ["--step", "99"])
        assert "window.__START_STEP__ = 3" in html

    def test_default_step_1_cook1(self, tmp_path):
        name = f"全新菜_{uuid.uuid4().hex[:6]}"
        _make_recipe(name)
        html, _ = self._render(tmp_path, {"name": name})
        assert "window.__START_STEP__ = 1" in html
        assert '"scene_id":"cook-1"' in html

    def test_invalid_step_rejected(self, tmp_path):
        name = f"坏参菜_{uuid.uuid4().hex[:6]}"
        _make_recipe(name)
        out = tmp_path / "cook.html"
        cmd = [sys.executable, str(SCRIPT_DIR / "cooking_render.py"), "render", name, "--step", "abc", "--output", str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 1
        assert "--step 必须是正整数" in res.stderr


# ── 完结闭环 + 断点续做按钮(模板静态断言)────────────────
class TestCookingModeTemplateButtons:
    TEMPLATE = TEMPLATES_DIR / "cooking_mode.html"

    def test_copy_progress_button(self):
        content = self.TEMPLATE.read_text(encoding="utf-8")
        assert "copyProgress" in content
        assert "📋 复制进度" in content

    def test_done_4_action_buttons(self):
        content = self.TEMPLATE.read_text(encoding="utf-8")
        for fn in ("copyRatingPrompt", "copyFeedbackPrompt", "copyReflectionPrompt", "copyPhotoPrompt"):
            assert fn in content, fn
        assert "⭐ 复制评分" in content
        assert "📝 复制点评" in content
        assert "🤔 复制反思" in content
        assert "📷 完成拍照" in content

    def test_photo_prompt_is_anticipatory(self):
        """完成拍照 = 预告式 prompt(08 §4): 含【作品照片即将发送:】占位,AI 先回「请发照片」"""
        content = self.TEMPLATE.read_text(encoding="utf-8")
        assert "【作品照片即将发送:】" in content
        assert "请发照片" in content

    def test_start_step_resolve(self):
        """URL #step=N 解析 + __START_STEP__ 优先"""
        content = self.TEMPLATE.read_text(encoding="utf-8")
        assert "resolveStartStep" in content
        assert "location.hash" in content
        assert "__START_STEP__" in content

    def test_resume_banner(self):
        content = self.TEMPLATE.read_text(encoding="utf-8")
        assert "showResumeBanner" in content
        assert "断点续做" in content

    def test_actual_time_tracking(self):
        """完结闭环: 实际用时累计"""
        content = self.TEMPLATE.read_text(encoding="utf-8")
        assert "actualSeconds" in content
        assert "实际用时" in content


# ── 作品照片入库(history_manager --photo)─────────────────
class TestHistoryPhoto:
    def test_add_with_chef_photo(self):
        rid = _make_recipe("照片菜")
        chef = "chef://work_photos/照片菜__work__20260809.jpg"
        res = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "history_manager.py"), "add", rid, "--rating", "5", "--feedback", "好吃", "--photo", chef],
            capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 0, res.stderr
        rows = query("SELECT photo FROM recipe_history WHERE recipe_id = ?", (rid,))
        assert len(rows) == 1
        assert rows[0]["photo"] == chef

    def test_add_without_photo_is_null(self):
        rid = _make_recipe("无照菜")
        res = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "history_manager.py"), "add", rid, "--rating", "4", "--feedback", "不错"],
            capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 0, res.stderr
        rows = query("SELECT photo FROM recipe_history WHERE recipe_id = ?", (rid,))
        assert rows[0]["photo"] is None

    def test_add_photo_empty_rejected(self):
        rid = _make_recipe("空照菜")
        res = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "history_manager.py"), "add", rid, "--rating", "3", "--feedback", "一般", "--photo", ""],
            capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 1
        assert "--photo 不能是空字符串" in res.stdout

    def test_update_photo(self):
        rid = _make_recipe("改照菜")
        hid = str(uuid.uuid4())
        execute("INSERT INTO recipe_history (id, recipe_id, cook_date, cook_sequence, rating, feedback) VALUES (?, ?, '2026-08-09', 1, 5, '好吃')", (hid, rid))
        chef = "chef://work_photos/改照菜__work__20260809.png"
        res = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "history_manager.py"), "update", hid, "--photo", chef],
            capture_output=True, text=True, encoding="utf-8", env=_child_env(), cwd=str(SCRIPT_DIR))
        assert res.returncode == 0, res.stdout + res.stderr
        rows = query("SELECT photo FROM recipe_history WHERE id = ?", (hid,))
        assert rows[0]["photo"] == chef
