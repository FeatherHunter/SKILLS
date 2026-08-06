"""SM6 票据凭证域 · 账号密码场景(account_ops)

第一性原理:
  - 复用现状 accounts.py 的 Fernet 加密链(迁移升级 = 新壳承接, 不重写密码学)
  - 新增: 类型组织(购物/银行/社交/其他 → 存 tags 首值, 零 schema 变更)
  - 新增: 清单全脱敏(密码永不进 payload; 复制数据默认不含密码 = 结构上无明文)
  - 敏感操作分离: 查看密码/复制密码 = 独立指令(经 AI 中转, 对话内回显)
"""
import sys
from pathlib import Path
from datetime import datetime
import sqlite3

_scripts_dir = Path(__file__).parent.parent.resolve()
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from accounts import (  # noqa: E402  (复用 Fernet 加密链)
    is_master_key_set, verify_master_key, _write_master_key,
    account_add, account_list, account_show, account_set_master,
    _encrypt, _init_db,
)

from 票据凭证.ops import ACCOUNT_TYPES  # noqa: E402


def account_type_of(tags):
    """从 tags 取类型(首值, 非法回退 其他)"""
    if tags:
        first = str(tags).split(",")[0].strip()
        if first in ACCOUNT_TYPES:
            return first
    return "其他"


def account_add_typed(platform, username, password, master_key,
                      account_type="其他", note=""):
    """存账号(带类型; 类型经 tags 承载)"""
    if account_type not in ACCOUNT_TYPES:
        raise ValueError(f"账号类型必须是 {'/'.join(ACCOUNT_TYPES)}")
    return account_add(platform, username, password, master_key,
                       tags=account_type, note=note)


def account_update_typed(platform, master_key, username=None, password=None,
                         account_type=None, note=None):
    """改账号(重新录入语义: 需主密钥验证; 空字段保持原值)"""
    if not verify_master_key(master_key):
        return {"success": False, "message": "Master key 错误"}
    conn = _init_db()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM accounts WHERE platform = ? AND (is_deleted IS NULL OR is_deleted = 0)",
        (platform,),
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"账号 '{platform}' 不存在"}

    new_enc = row["encrypted_password"]
    if password is not None:
        new_enc = _encrypt(password, master_key)
    new_user = row["username"] if username is None else username
    new_tags = row["tags"] if account_type is None else account_type
    new_note = row["note"] if note is None else note
    conn.execute(
        "UPDATE accounts SET username = ?, encrypted_password = ?, tags = ?, note = ?, "
        "updated_at = ? WHERE id = ?",
        (new_user, new_enc, new_tags, new_note,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"账号 '{platform}' 已更新", "platform": platform}


def account_list_masked():
    """账号清单(全脱敏: 无密码字段; 带类型组织)"""
    out = []
    for row in account_list():
        row["type"] = account_type_of(row.get("tags", ""))
        row["password_masked"] = "******"
        row.pop("encrypted_password", None)
        out.append(row)
    return out


def account_show_typed(platform, master_key):
    """查看账号明文(敏感; 仅经 AI 对话回显, 不进 HTML payload)"""
    return account_show(platform, master_key)
