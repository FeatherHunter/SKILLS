"""{技能名}.html 同步脚本 — 居家管家.html = HELP HTML 副本

总纲 04 §原则 4(新版本,2026-07-27):
  每个技能目录都需要有 {技能名}.html 文件,该文件就是 技能 HELP HTML
  最新版本的复制品。任何 唤醒词/场景 修改后,跑本脚本同步。

用法:
  python3 scripts/build_manual.py
  # 等价于:
  #   1. python3 scripts/home_manager.py help --output /tmp/__help.html
  #   2. cp /tmp/__help.html 居家管家.html
"""
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).parent.parent
TEMP = Path("/tmp") / "__居家管家_help_generated.html"
TARGET = SKILL / "居家管家.html"

# 用当前 Python 解释器 + home_manager.py 生成 HELP HTML(固定时间戳让可重现)
import os
env = os.environ.copy()
env["HELP_FIXED_TIMESTAMP"] = "0000-00-00 00:00 (快照)"
# 不强制 HELP_INITIALIZED:镜像 = 构造时检测本地真实初始化状态注入
# (用户 2026-08-05 拍板:HTML 快照无法运行时检测,必须生成时检测本地并注入)
r = subprocess.run(
    [sys.executable, str(SKILL / "scripts" / "home_manager.py"),
     "help", "--output", str(TEMP)],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=str(SKILL / "scripts"),
    env=env,
)
if r.returncode != 0:
    print(f"✗ HELP HTML 生成失败:\n{r.stderr}", file=sys.stderr)
    sys.exit(r.returncode)

# 字节级复制覆盖
shutil.copy2(TEMP, TARGET)
TEMP.unlink(missing_ok=True)
print(f"✓ 居家管家.html 已与 HELP HTML 同步(参考 references/scenarios.yaml)")
