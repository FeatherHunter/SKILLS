# Daily Recorder - API 参考

其他技能调用前先读取此文件。

## 数据库路径

```
/mnt/d/2Study/StudyNotes/.db/daily_recorder.db
```

## 查询消息（CLI）

```bash
# 查单日
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --date 20260509

# 查时间范围
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --start 20260509000000 --end 20260509235959

# 只传开始时间（查某时刻之后所有）
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --start 20260509000000

# 只传结束时间（查某时刻之前所有）
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --end 20260509235959

# 指定最大条数（默认 1000）
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --date 20260509 --limit 500
```

**输出格式**：
```
共 N 条消息

[YYYY-MM-DD HH:MM:SS] [channel] 消息内容...
[YYYY-MM-DD HH:MM:SS] [channel] 消息内容...
```

## 直接 import 查询函数

```python
import sys
sys.path.insert(0, '/mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts')
from db import Database
from query import parse_ts

db = Database('/mnt/d/2Study/StudyNotes/.db/daily_recorder.db')

# 范围查询
rows = db.query(start_ts=parse_ts('20260509000000'), end_ts=parse_ts('20260509235959'))
for msg_id, ts, channel, content, date in rows:
    print(f"[{ts}] {content}")
```

## 触发扫描（cron / 手动）

```bash
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/record.py
```

支持两种调用方式：
- **不带参数**：扫描自上次运行以来的新消息（增量）
- **带参数**（TODO）：强制全量扫描 `python3 record.py --full`