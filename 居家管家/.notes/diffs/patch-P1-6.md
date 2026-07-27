# Patch P1-6: account_del master-key 强制 + 软删除

## diff
- `accounts.py:_init_db` 加 is_deleted / deleted_at 字段 + 兼容老库 ALTER
- `accounts.py:account_del` 加 master_key 必填 + 软删除 UPDATE
- `accounts.py:account_list` 排除 is_deleted=1
- `accounts.py:account_show` 排除 is_deleted=1
- `home_manager.py:del` 加 master_key 校验

## 实测(隔离 temp DB)
| 场景 | 结果 |
|---|---|
| init 8字符密钥 | ✓ |
| add 账号 | ✓ |
| del 无 master key | ✗ 拒绝 exit=1 |
| del 错 master key | ✗ Master key 错误 |
| del 正 master key | ✓ 软删除 |
| list (软删除后) | (无记录) |
| show (软删除后) | ✗ 账号不存在 |

## 软删除恢复(暂未实现,留 P2)
- 当前软删除后只能用 SQL 恢复:
  `UPDATE accounts SET is_deleted = 0, deleted_at = NULL WHERE platform = 'x'`
- 后续可加 account --action restore 子命令

## 风险
- 老账号表没有 is_deleted/deleted_at 字段 → 首次调用 _init_db 时自动 ALTER 补齐
- 软删除后能否被 set-master 重新解密?YES(encrypted_password 不变,只是不再被 list/show 列出)