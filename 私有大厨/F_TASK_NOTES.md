# F 任务说明:5b4cb04 commit 错位修正

## 现象

5b4cb04 commit 信息与实际内容不匹配:

- 信息: `加清理 P0-4 FAT 真测副作用脚本`
- 实际: 改 render_data.py 4 处 sys.exit(1)(B 任务部分实现)
  - cmd_search 错误路径 → exit 1
  - cmd_history 错误路径 → exit 1
  - cmd_stats 错误路径 → exit 1
  - cmd_relations 错误路径 → exit 1

## 真实清理脚本位置

`scripts/cleanup_test_history.py`(commit d0fcb23):
- 删 cook_date = '2026-07-28' 历史
- 保留 2026-07-21 seq=1 真实数据

## 为什么不撤回 5b4cb04

- render_data.py 4 处 sys.exit(1) 是 B 任务部分实现
- 5 维度评估(commit 49842d8)B 必要性 = 0
- 但已修不删(不增加未来 user 困惑)
- 撤销反而丢真实修复

## 为什么不 rebase amend

- rebase 改 4 个 commit hash(高风险)
- 增 1 个新 commit(零风险)已足够

## 下次遇到"commit 信息错位"

- 选**增 1 个新 commit 说明**(零风险)
- 不用 rebase(改 hash)
- 不用 reset --hard(丢修复)
