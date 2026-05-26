"""
提醒调度器：由 cron 每 {MEMO_CRON_INTERVAL} 分钟调用
检查到期提醒并输出 JSON，由 openclaw 平台处理推送
"""
import subprocess
import json
import os
from pathlib import Path

def get_db_path():
    """获取 memo.db 的路径，支持文件或目录（目录时自动找 memo.db）"""
    db_path = os.environ.get("MEMO_DB_PATH")
    if not db_path:
        raise ValueError("MEMO_DB_PATH 环境变量未设置")
    if os.path.isdir(db_path):
        # 目录 → 自动找里面的 memo.db
        db_path = os.path.join(db_path, "memo.db")
    if not os.path.isfile(db_path):
        raise ValueError(f"数据库文件不存在: {db_path}")
    return db_path

def check_reminders():
    cli_path = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    db_path = get_db_path()
    try:
        # 传递正确的 DB 路径给 memo_cli.py
        env = os.environ.copy()
        env["MEMO_DB_PATH"] = db_path
        result = subprocess.run(
            ["python3", cli_path, "due", "--db", db_path],
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
