"""
提醒调度器：由 cron 每 {MEMO_CRON_INTERVAL} 分钟调用
检查到期提醒并输出 JSON，由 openclaw 平台处理推送
"""
import subprocess
import json
import os
from memo_cli import DB_PATH

def check_reminders():
    cli_path = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    try:
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(DB_PATH.parent)
        result = subprocess.run(
            ["python3", cli_path, "due"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env
        )
        data = json.loads(result.stdout)
        if data["status"] == "ok" and data["data"]:
            for item in data["data"]:
                print(f"🔔 {item.get('content', '提醒事项')}\n⏰ {item.get('time', '现在')} · {item.get('repeat_type', '一次性')}")
        else:
            print("NO_REPLY")
    except Exception as e:
        print(f"提醒检查失败: {e}")

if __name__ == "__main__":
    check_reminders()
