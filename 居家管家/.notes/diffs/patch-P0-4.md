# Patch P0-4: set_master_key 内部化 + 强制走 account_set_master

## 目标
- `set_master_key()` 改名 `_write_master_key()`(明确是内部 helper)
- CLI `account --action init` 走新函数(允许首次初始化场景)
- CLI `account --action set-master` 必须验证旧密钥(已有逻辑,只需保证不旁路)

## 改动文件
- `scripts/accounts.py`
- `scripts/home_manager/home_manager.py`

## diff 草案

```python
# ── accounts.py ─────────────────────────────────
# 删除 def set_master_key(master_key) → dict
# 替换为:

def _write_master_key(master_key: str) -> dict:
    """内部:首次初始化 master key(无需旧密钥)。
    仅供 home_manager.py CLI account --action init 调用。
    其他场景必须走 account_set_master(old, new)。"""
    if not master_key or len(master_key) < 8:
        return {"success": False, "message": "密钥至少 8 个字符"}
    MASTER_KEY_FILE.write_text(_hash_key(master_key))
    os.chmod(MASTER_KEY_FILE, 0o600)
    return {"success": True, "message": "Master key 已设置(首次初始化)"}
```

```python
# ── home_manager.py ──────────────────────────────
# 改动 1: import 替换
# 旧: from accounts import (is_master_key_set, verify_master_key, set_master_key, ...)
# 新: from accounts import (is_master_key_set, verify_master_key, _write_master_key, ...)

# 改动 2: init 分支(line ~467)
# 旧: result = set_master_key(args.master_key)
# 新: 
#     if is_master_key_set():
#         print("✗ master key 已存在;改用 --action set-master 走密钥变更流程")
#         return 1
#     result = _write_master_key(args.master_key)
```

## 验证
```bash
T=$(mktemp -d)
# 1. 首次 init 必须成功
SKILLS_DB_PATH="$T" python3 -c "
import sys;sys.path.insert(0,'scripts')
import accounts
print(accounts._write_master_key('longenough123'))
"
# 期望: {'success': True, ...}

# 2. 验证 set_master_key 不再对外暴露
SKILLS_DB_PATH="$T" python3 -c "
import sys;sys.path.insert(0,'scripts')
import accounts
print(getattr(accounts, 'set_master_key', 'NOT FOUND'))
"
# 期望: 'NOT FOUND'

# 3. CLI init 第二次拒绝(必须用 set-master)
T2=$(mktemp -d)
SKILLS_DB_PATH="$T2" python3 scripts/home_manager.py account --action init --master-key 'firstkey123'
# 期望: ✓ 首次初始化
SKILLS_DB_PATH="$T2" python3 scripts/home_manager.py account --action init --master-key 'secondkey123'
# 期望: ✗ master key 已存在;改用 --action set-master
rm -rf "$T" "$T2"
```

## 风险
- 老 CLI 调用 `account --action init --master-key X` 第二次会失败 → 用户需改用 `set-master`(有提示)。
- `_write_master_key` 加了 8 字符校验(原来 4 字符),老 master key 4 字符会被拒 → 如果你的 master key 是 4 字符,需要先 `set-master` 加长。