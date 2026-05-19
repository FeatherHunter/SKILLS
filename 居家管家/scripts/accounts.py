"""
账号管理模块
负责：账号的CRUD + 加密/解密逻辑
密码用 master key 加密存储，密钥不存明文只存哈希

路径配置：
  - 复用 home_manager.db 中的 DB_PATH（统一路径查找策略）
  - MASTER_KEY_FILE 存在技能目录下
"""

import os
import sys
import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken

# ── 路径配置（复用 home_manager.db 的共享路径）───────────

_pkg_dir = Path(__file__).parent.resolve()
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

# 从 home_manager.db 导入已计算好的共享路径
from home_manager.db import DB_PATH, SKILL_DIR

DB_DIR = DB_PATH.parent


def _find_master_key_path(skill_dir):
    """三层查找.master.key路径：环境变量 > 技能目录 > 父目录.db（与 db.py 三层查找保持一致）"""
    import os as _os
    env_path = _os.environ.get("SKILLS_DB_PATH")
    if env_path:
        p = Path(env_path) / ".master.key"
        if p.exists():
            return p
    p = skill_dir / ".master.key"
    if p.exists():
        return p
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / ".master.key"
            if p.exists():
                return p
    default_dir = skill_dir / ".db"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / ".master.key"


MASTER_KEY_FILE = _find_master_key_path(SKILL_DIR)
TABLE_NAME = "accounts"

# ── 加密工具 ─────────────────────────────────────────────────────────────────

def _derive_key(master_key: str) -> bytes:
    """把 master key 转成 Fernet 密钥（32字节）"""
    import hashlib, base64
    return base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())

def _encrypt(plain_text: str, master_key: str) -> str:
    """加密明文"""
    f = Fernet(_derive_key(master_key))
    return f.encrypt(plain_text.encode()).decode()

def _decrypt(cipher_text: str, master_key: str) -> str:
    """解密密文"""
    f = Fernet(_derive_key(master_key))
    return f.decrypt(cipher_text.encode()).decode()

def _hash_key(master_key: str) -> str:
    """哈希 master key 用于验证"""
    return hashlib.sha256(master_key.encode()).hexdigest()

# ── Master Key 管理 ──────────────────────────────────────────────────────────

def is_master_key_set() -> bool:
    """检查是否已设置 master key"""
    return MASTER_KEY_FILE.exists()

def verify_master_key(master_key: str) -> bool:
    """验证 master key 是否正确"""
    if not MASTER_KEY_FILE.exists():
        return False
    stored_hash = MASTER_KEY_FILE.read_text().strip()
    return _hash_key(master_key) == stored_hash

def set_master_key(master_key: str) -> dict:
    """设置/更新 master key"""
    if not master_key or len(master_key) < 4:
        return {"success": False, "message": "密钥至少4个字符"}
    MASTER_KEY_FILE.write_text(_hash_key(master_key))
    return {"success": True, "message": "Master key 已设置"}

# ── 数据库初始化 ─────────────────────────────────────────────────────────────

def _init_db():
    """初始化账号表"""
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL DEFAULT '',
            encrypted_password TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

# ── 账号 CRUD ────────────────────────────────────────────────────────────────

def account_add(platform: str, username: str, password: str,
               master_key: str, tags: str = "", note: str = "") -> dict:
    """添加账号"""
    if not is_master_key_set():
        return {"success": False, "message": "请先设置 master key（account --action init）"}
    if not verify_master_key(master_key):
        return {"success": False, "message": "Master key 错误"}
    if not platform:
        return {"success": False, "message": "platform 不能为空"}

    encrypted = _encrypt(password, master_key)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _init_db()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (platform, username, encrypted_password, tags, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (platform, username, encrypted, tags, note, now, now))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        return {"success": True, "message": f"账号已添加（ID:{record_id}）", "id": record_id, "platform": platform}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "message": f"账号 '{platform}' 已存在"}


def account_list() -> list:
    """列出所有账号（密码隐藏）"""
    conn = _init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, platform, username, tags, note, created_at FROM {TABLE_NAME} ORDER BY platform")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def account_show(platform: str, master_key: str) -> dict:
    """查看账号密码（需验证 master key）"""
    if not verify_master_key(master_key):
        return {"success": False, "message": "Master key 错误"}

    conn = _init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE platform = ?", (platform,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"success": False, "message": f"账号 '{platform}' 不存在"}

    try:
        decrypted = _decrypt(row['encrypted_password'], master_key)
    except InvalidToken:
        return {"success": False, "message": "解密失败，可能是密钥不匹配"}

    return {
        "success": True,
        "platform": row['platform'],
        "username": row['username'],
        "password": decrypted,
        "tags": row['tags'],
        "note": row['note']
    }


def account_del(platform: str) -> dict:
    """删除账号"""
    conn = _init_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM {TABLE_NAME} WHERE platform = ?", (platform,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"账号 '{platform}' 不存在"}

    cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE platform = ?", (platform,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        return {"success": True, "message": f"已删除账号 '{platform}'"}
    return {"success": False, "message": f"删除失败"}


def account_set_master(old_master_key: str, new_master_key: str) -> dict:
    """修改 master key"""
    if not is_master_key_set():
        return {"success": False, "message": "尚未设置 master key，请先初始化"}
    if not verify_master_key(old_master_key):
        return {"success": False, "message": "旧密钥错误"}
    if not new_master_key or len(new_master_key) < 4:
        return {"success": False, "message": "新密钥至少4个字符"}

    conn = _init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT platform, encrypted_password FROM {TABLE_NAME}")
    rows = cursor.fetchall()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        try:
            decrypted = _decrypt(row['encrypted_password'], old_master_key)
            new_encrypted = _encrypt(decrypted, new_master_key)
            cursor.execute(f"""
                UPDATE {TABLE_NAME} SET encrypted_password = ?, updated_at = ?
                WHERE platform = ?
            """, (new_encrypted, now, row['platform']))
        except InvalidToken:
            conn.close()
            return {"success": False, "message": f"解密 '{row['platform']}' 失败，跳过"}

    conn.commit()
    conn.close()

    MASTER_KEY_FILE.write_text(_hash_key(new_master_key))
    return {"success": True, "message": f"已更新 master key，共迁移 {len(rows)} 个账号"}