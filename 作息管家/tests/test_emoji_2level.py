"""分类 emoji 2 级决策测试(2026-07-25 用户报告触发)

第一性:HTML 渲染应该用 validators.CATEGORY_EMOJI_LEVEL2 全 69 条,
     而不是本地 EMOJI_MAP 42 条(还含 '健康' 重复 key bug → 🏥 错赢)。

修复:cat_emoji() 重写为从 validators 拿数据源。
本测试锁住:
  1. 二级 emoji 正确返回(组合 emoji "<一级><二级>")
  2. 一级 fallback(只有 1 级 cat 时只返一级)
  3. 未知兜底("📌")
  4. 修"健康"重复 key bug → "💪"
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from calculations import cat_emoji, EMOJI_MAP


# ===== 一级 × 二级组合 =====
def test_emoji_combined_one_and_two():
    """二级正确:cat '<l1>.<l2>' → 1+2 组合 emoji"""
    cases = [
        ("工作.AI调优", "💼🤖"),
        ("工作.开发", "💼💻"),
        ("工作.会议", "💼🤝"),
        ("健康.健身", "💪🏋️"),    # 修 bug:原 🏥
        ("健康.修行", "💪🧘"),
        ("健康.冥想", "💪🧠"),
        ("维持.睡眠", "🌱😴"),
        ("维持.做饭", "🌱🍳"),
        ("维持.通勤", "🌱🚴"),
        ("调整.游戏", "😌🎮"),
        ("调整.视频", "😌📺"),
        ("调整.休息", "😌🛋️"),
        ("创作.SOP", "🎨📋"),
        ("创作.文字", "🎨✍️"),
        ("创作.视频", "🎨🎥"),
        ("学习.读书", "📖📕"),
        ("学习.技术", "📖💻"),
        ("投入.家人", "🤝👨‍👩‍👧"),
        ("日常.园艺", "📋🌿"),
        ("日常.代办", "📋☑️"),
    ]
    for cat, expected in cases:
        actual = cat_emoji(cat)
        assert actual == expected, f"cat_emoji({cat!r}): expected {expected!r}, got {actual!r}"


# ===== 一级 fallback =====
def test_emoji_fallback_to_one_when_no_two():
    """只有一级时:只用一级 emoji(SKILL.md 官方 8 级:🌱💪💼📖🎨🤝😌📋)"""
    cases = [
        ("工作", "💼"),
        ("维持", "🌱"),
        ("健康", "💪"),         # 修 bug:原 🏥
        ("调整", "😌"),
        ("创作", "🎨"),
        ("投入", "🤝"),
        ("学习", "📖"),         # SKILL.md 官方用 📖(不是老 EMOJI_MAP 的 📚)
        ("日常", "📋"),
    ]
    for cat, expected in cases:
        actual = cat_emoji(cat)
        assert actual == expected, f"cat_emoji({cat!r}): expected {expected!r}, got {actual!r}"


# ===== 未知兜底 =====
def test_emoji_unknown_fallback_to_pin():
    """完全未知的 cat → '📌' 兜底"""
    cases = [
        ("health", "📌"),     # 真的不存在
        ("不存在.也.不存在", "📌"),
        ("", "📌"),
        # 老 1 级词在 LEVEL2 没设(部分在 EMOJI_MAP 老兼容 dict 有,但优先 validators)
        # 实际 l1_of 已做 l1_alias 映射,所以老词会被映射到新一级
        # 这里只测完全不认识的
    ]
    for cat, expected in cases:
        actual = cat_emoji(cat)
        assert actual == expected, f"cat_emoji({cat!r}): expected {expected!r}, got {actual!r}"


# ===== 修 bug: '健康' 重复 key 后写赢不再是 🏥 =====
def test_emoji_healthy_one_level_fixed():
    """'健康' 一级之前被 🏥 覆盖(重复 key 后写赢), 现在应该是 💪"""
    assert cat_emoji("健康") == "💪"
    assert cat_emoji("健康.健身") == "💪🏋️"
    assert cat_emoji("健康.运动") == "💪🏃"


# ===== OLD EMOJI_MAP 仍保留向下兼容 =====
def test_old_emoji_map_still_works():
    """老 EMOJI_MAP 还在(给其他函数/导入用) — 修复不破坏向后兼容"""
    assert EMOJI_MAP["维持"] == "🌱"
    assert EMOJI_MAP["工作"] == "💼"
    # '健康' 单一定义(修后)
    assert EMOJI_MAP["健康"] == "💪"


# ===== 4 种分隔符兼容 =====
def test_emoji_separator_compatibility():
    """4 种 l1/l2 分隔符(./·/・/•)都能正确分隔"""
    # 同样: 工作.AI调优 = 工作·AI调优 = 工作・AI调优 = 工作•AI调优
    expected = "💼🤖"
    assert cat_emoji("工作.AI调优") == expected
    assert cat_emoji("工作·AI调优") == expected
    assert cat_emoji("工作・AI调优") == expected
    assert cat_emoji("工作•AI调优") == expected


# ===== 真实使用场景测试 =====
def test_real_user_scenarios():
    """用户报告的真实场景样本"""
    cases = [
        ("调整.游戏", "😌🎮"),    # 用户报告'调整.游戏'之前只有一种 emoji
        ("创作.SOP", "🎨📋"),     # 用户报告'创作.SOP'之前显示 🎨(用户感觉不对)
        ("健康.健身", "💪🏋️"),    # 修 '健康' bug:之前 🏥
        ("工作.会议", "💼🤝"),     # 之前 💼(一级 fallback), 现在 💼🤝(二级具体)
        ("维持.做饭", "🌱🍳"),     # 之前 🌱, 现在 🌱🍳
    ]
    for cat, expected in cases:
        actual = cat_emoji(cat)
        assert actual == expected, f"用户场景 {cat}: {expected} vs {actual}"