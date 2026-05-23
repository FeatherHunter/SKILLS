"""
提醒调度器：由 openclaw cron 每分钟调用一次
负责调用 CLI 获取到期提醒，并推送给用户。
"""

import subprocess
import json
import os

def check_reminders():
    cli_path = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    try:
        result = subprocess.run(
            ["python3", cli_path, "due"],
            capture_output=True,
            text=True,
            timeout=5
        )
        data = json.loads(result.stdout)
        if data["status"] == "ok" and data["data"]:
            for item in data["data"]:
                # 推送通知（具体推送机制请替换为 openclaw 的通知接口）
                notify_user(item)
    except Exception as e:
        print(f"提醒检查失败: {e}")

def notify_user(item):
    """
    通过 openclaw 的通知系统向用户发送提醒。
    这里提供一个示例，你需要替换为实际的通知调用。
    """
    content = item.get("content", "提醒事项")
    time = item.get("time", "现在")
    print(f"【提醒】{time} - {content}")
    # 实际调用：openclaw.notify(title="备忘录提醒", body=content)

if __name__ == "__main__":
    check_reminders()