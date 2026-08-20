import subprocess, sys, sqlite3

# 1. 卡路里:盖浇饭 550g → 1000 千卡
r = subprocess.run(
    [sys.executable, "scripts/calorie_tracker.py", "add",
     "盖浇饭", "1000", "25.0", "130.0", "31.0", "550",
     "--date", "2026-08-19", "--time", "12:30:00", "--meal", "午餐",
     "--note", "AI估算,盖浇饭 550g 记为 1000 千卡(用户口径)"],
    capture_output=True, text=True, encoding="utf-8"
)
print("[卡路里]", r.stdout.strip() or r.stderr.strip())

# 2. 饼干记账:DeepSeek 中转套餐 ¥5
r2 = subprocess.run(
    ["python", "scripts/write/cli.py", "add",
     "--category", "居家/工作/AI 工具", "--amount", "-5.00",
     "--account", "支付宝", "--time", "2026-08-19 12:50:00",
     "--note", "DeepSeek 中转套餐 ¥5.00"],
    capture_output=True, text=True, encoding="utf-8"
)
print("[记账]", r2.stdout.strip() or r2.stderr.strip())