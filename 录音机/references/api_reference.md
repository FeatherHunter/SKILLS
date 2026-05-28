# Daily Recorder - API 参考

其他技能调用前先读取此文件。

## 数据库路径

通过三级路由自动查找：环境变量 `SKILLS_DB_PATH` > 父目录 `.db/` > 技能目录 `.db/`

## 查询消息（CLI）

```bash
# 查单日
python3 scripts/query.py --date 20260509

# 查时间范围
python3 scripts/query.py --start 20260509000000 --end 20260509235959

# 只传开始时间（查某时刻之后所有）
python3 scripts/query.py --start 20260509000000

# 只传结束时间（查某时刻之前所有）
python3 scripts/query.py --end 20260509235959

# 指定最大条数（默认 1000）
python3 scripts/query.py --date 20260509 --limit 500

# 按渠道筛选
python3 scripts/query.py --date 20260509 --channel qq

# 按发送者筛选
python3 scripts/query.py --date 20260509 --sender user123

# 查询附件
python3 scripts/query.py --date 20260509 --attachments

# 按附件类型筛选（隐含 --attachments）
python3 scripts/query.py --date 20260509 --type image

# 查最近 N 条
python3 scripts/query.py --recent 20
```

**输出格式**：
```
消息 N 条

[YYYY-MM-DD HH:MM:SS] [channel]
  消息内容...
```

## 直接 import 查询函数

```python
import sys
sys.path.insert(0, 'scripts')
from db import Database
from query import parse_ts

db = Database()  # 自动通过三级路由查找 DB

# 范围查询
rows = db.query(start_ts=parse_ts('20260509000000'), end_ts=parse_ts('20260509235959'))
for msg_id, ts, channel, sender_id, content, has_attachment, date in rows:
    print(f"[{ts}] [{channel}] {content}")

# 按渠道筛选
rows = db.query(date='20260509', channel='qq')

# 按发送者筛选
rows = db.query(date='20260509', sender_id='user123')

# 查询附件
att_rows = db.query_attachments(date='20260509')
for msg_id, ts, channel, sender_id, file_path, file_type, date in att_rows:
    print(f"[{ts}] [{file_type}] {file_path}")

# 按附件类型筛选
att_rows = db.query_attachments(date='20260509', file_type='image')
```

## 触发扫描（cron / 手动）

```bash
# 增量扫描（默认）
python3 scripts/record.py

# 全量重扫（清空 checkpoint）
python3 scripts/record.py --full
```

不带参数运行，自动从上次 checkpoint 增量扫描新消息。

## 状态与维护（CLI）

```bash
# 初始化数据库
python3 scripts/status.py --init

# 查看状态
python3 scripts/status.py

# 消息统计
python3 scripts/status.py --stats

# 重建索引
python3 scripts/status.py --reindex
```
