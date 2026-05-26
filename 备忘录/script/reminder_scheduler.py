"""
提醒调度器：由 cron 每 {MEMO_CRON_INTERVAL} 分钟调用
检查到期提醒并输出 JSON，由 openclaw 平台处理推送
"""
import subprocess
import json
import os
from pathlib import Path

def get_db_path():
    """三层查找DB路径：环境变量 SKILLS_DB_PATH > 父目录.db > 技能目录.db"""
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        return Path(env_path) / "memo.db"
    # 2. 父目录层层找 .db 文件夹
    skill_dir = Path(__file__).parent.parent
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return db_dir / "memo.db"
    # 3. 技能目录下 .db 子目录（默认 fallback）
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / "memo.db"

def check_reminders():
    cli_path = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    db_path = get_db_path()
    try:
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(db_path.parent)
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