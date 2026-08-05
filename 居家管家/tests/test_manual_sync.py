"""居家管家.html 必须与 HELP HTML 字节一致(总纲 04 §原则 4 镜像约束)

任何对 scenarios.yaml / help_center.py / templates/help_center.html 的修改
都应该跑 `python3 scripts/build_manual.py` 同步 居家管家.html。
本测试用哈希断言兜底(即使有人忘了跑脚本也不会被 lock 阻断,只在错误时报警)。
"""
import hashlib
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).parent.parent
TARGET = SKILL / "居家管家.html"
HELP_TMP = SKILL / ".db" / "__sync_test_help.html"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _generate_help_html() -> Path:
    HELP_TMP.parent.mkdir(parents=True, exist_ok=True)
    if HELP_TMP.exists():
        HELP_TMP.unlink()
    import os
    env = os.environ.copy()
    env["HELP_FIXED_TIMESTAMP"] = "0000-00-00 00:00 (快照)"
    env["HELP_INITIALIZED"] = "1"
    r = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "home_manager.py"),
         "help", "--output", str(HELP_TMP)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(SKILL / "scripts"),
        env=env,
    )
    if r.returncode != 0:
        pytest.fail(f"HELP HTML 生成失败:\n{r.stderr}")
    return HELP_TMP


def test_manual_html_matches_help_html():
    """强制约束: 居家管家.html == HELP HTML 字节级一致"""
    import pytest
    help_html = _generate_help_html()
    assert TARGET.exists(), f"居家管家.html 不存在;先跑 python3 scripts/build_manual.py"

    h1 = _sha256(help_html)
    h2 = _sha256(TARGET)

    if h1 != h2:
        pytest.fail(
            f"❌ 居家管家.html 与 HELP HTML 不一致!\n"
            f"  HELP:    {h1[:12]}... ({help_html.stat().st_size} B)\n"
            f"  TARGET:  {h2[:12]}... ({TARGET.stat().st_size} B)\n"
            f"修复: python3 scripts/build_manual.py"
        )
    print(f"✓ 居家管家.html == HELP HTML 字节一致 ({TARGET.stat().st_size} B)")


def test_build_manual_script_exists():
    """同步脚本必须在,否则镜像约束无自动化"""
    script = SKILL / "scripts" / "build_manual.py"
    assert script.exists(), "缺 scripts/build_manual.py"
    content = script.read_text(encoding="utf-8")
    assert "居家管家.html" in content
    assert "shutil.copy2" in content
