# 位置/scenes.py - SM2 域场景 id 单一事实源(#253 · 2026-08-11)
#
# 替代 cli.py / ops.py 中的硬编码 scene_id("SM2-1"~"SM2-4"):
#   命令 → 唤醒词 → 从 references/scenarios.yaml 反查场景 id。
#   清单缺失/未命中 → 回退历史值(集中一处, 不散落硬编码)。
import yaml
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent
SCENARIOS_YAML = SKILL_DIR / "references" / "scenarios.yaml"

# 命令 → (用途, 唤醒词, 回退场景 id)
_COMMANDS = {
    "sm2-view":    ("空间视图", "空间视图", "SM2-4"),
    "sm2-manage":  ("管位置", "管位置", "SM2-1"),
    "sm2-fixed":   ("固定位", "固定位", "SM2-2"),
    "sm2-suggest": ("收纳建议", "收纳建议", "SM2-3"),
}


def _load_space_scenes():
    """从场景清单读 space 域场景: {wake_word: id}"""
    try:
        data = yaml.safe_load(SCENARIOS_YAML.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    out = {}
    for s in (data.get("scenarios") or []):
        if s.get("domain") == "space" and s.get("wake_word"):
            out[s["wake_word"]] = s.get("id")
    return out


def scene_id(command):
    """命令 → 场景 id(单一事实源: 清单反查, 回退表兜底)"""
    if command not in _COMMANDS:
        return command
    _, wake, fallback = _COMMANDS[command]
    sm2 = _load_space_scenes()
    return sm2.get(wake, fallback)
