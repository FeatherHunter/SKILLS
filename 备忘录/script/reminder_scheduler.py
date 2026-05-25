"""
提醒调度器：由 cron 每分钟调用
检查到期提醒并输出 JSON，由 openclaw 平台处理推送
"""
import subprocess
import json
import os
from pathlib import Path

def get_db_path():
    """获取 memo.db 的正确路径（与 memo_cli.py 逻辑一致）"""
    # 使用绝对路径，避免 __file__ 相对路径问题
    skill_dir = Path(__file__).resolve().parent.parent
    # 环境变量优先
    db_path = os.environ.get("MEMO_DB_PATH")
    if db_path:
        # 如果是目录，追加 memo.db
        if os.path.isdir(db_path):
            db_path = os.path.join(db_path, "memo.db")
    else:
        # 回退到 skill_dir 的 .db/MemoHub/memo.db
        db_path = os.path.join(skill_dir, ".db", "MemoHub", "memo.db")
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
