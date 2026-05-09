# Daily Recorder - 设计思路

## 为什么用 Unix 微秒时间戳

1. **去重**：OpenClaw 消息 ID 本身是唯一的，但某些场景下 message_id 可能为空。用 timestamp+session_file 组合也能去重，微秒级精度几乎不可能重复。
2. **排序**：整数比较比 datetime 更快，范围查询直接用 `BETWEEN start AND end`。
3. **无时区歧义**：所有时间都以 UTC 存储，展示时转换为北京时间（+8小时）。

## 增量扫描设计

每次扫描时：
1. 读取 scan_checkpoint 获取该文件的上次终止时间戳
2. 从该时间戳之后继续扫描
3. 新消息全部入库后，更新 checkpoint

如果 checkpoint 为空（全量扫描），timestamp 传 0。

## 渠道推断

当前根据 session 文件名推断（暂未细分）：
- 文件名含 `qqbot` → `qq`
- 文件名含 `wechat` → `wechat`
- 文件名含 `web` → `web`
- 其他 → `pc`

未来可从 message metadata 中获取真实渠道。

## 过滤策略

当前只过滤 role != user 的消息，其他全部放开。后续按需在 record.py 的 `extract_user_messages()` 中增加过滤逻辑。

## 查询灵活性

查询支持三种时间参数：
- `--date YYYYMMDD`：单日查询
- `--start YYYYMMDDHHMMSS` + `--end YYYYMMDDHHMMSS`：范围查询
- 单独 `--start` 或 `--end`：无限制一端

所有时间参数最终转换为微秒时间戳进行查询。