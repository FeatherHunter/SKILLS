# -*- coding: utf-8 -*-
"""批量修复 safe_run(main) → safe_run(main)()"""
import sys, shutil
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
dry = "--dry" in sys.argv
count = 0

for f in sorted(SCRIPTS.rglob("*.py")):
    if f.name == "__init__.py" or "_internal" in str(f):
        continue
    lines = f.read_text("utf-8").splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        # 行末正好是 safe_run(main) 且后面不跟 (
        stripped = line.rstrip("\r\n")
        if stripped.endswith("safe_run(main)") and "safe_run(main)()" not in stripped:
            # 确认下一行是文件尾或空行（防止误伤 import）
            next_is_end = i + 1 >= len(lines) or lines[i + 1].strip() == ""
            if next_is_end:
                lines[i] = stripped + "()" + line[len(stripped):]
                changed = True
    if not changed:
        continue
    if dry:
        print(f"[DRY] {f.relative_to(SCRIPTS.parent)}")
    else:
        shutil.copy2(f, f.with_suffix(".py.bak"))
        f.write_text("".join(lines), "utf-8")
        print(f"[FIX] {f.relative_to(SCRIPTS.parent)}")
    count += 1

print(f"\n{'将' if dry else '已'}修复 {count} 个文件")
