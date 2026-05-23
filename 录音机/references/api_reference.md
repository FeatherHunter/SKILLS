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
sys.path.insert(0, 'scripts')
from db import Database
from query import parse_ts

db = Database()  # 自动通过三级路由查找 DB

# 范围查询
rows = db.query(start_ts=parse_ts('20260509000000'), end_ts=parse_ts('20260509235959'))
for msg_id, ts, channel, content, date in rows:
    print(f"[{ts}] {content}")
```

## 触发扫描（cron / 手动）

```bash
python3 scripts/record.py
```

不带参数运行，自动从上次 checkpoint 增量扫描新消息。