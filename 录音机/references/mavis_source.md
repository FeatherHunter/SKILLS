# Mavis (MiniMaxCode) 数据源

> 新增于 2026-07-01,把本机 Mavis daemon 中的用户对话同步到录音机。

## 来源

**Mavis 本身**(用户口中的 "MiniMaxCode")—— 不是外部 Claude Code 客户端。

| 项 | 值 |
|---|---|
| 数据库 | `C:\Users\<user>\.mavis\sqlite.db` |
| 主表 | `session_messages` |
| 渠道标识 | `MiniMaxCode` |

环境变量 `MAVIS_DB` 可覆盖路径。

## 同步脚本

```bash
python3 scripts/record_mavis.py           # 增量(从 checkpoint 继续)
python3 scripts/record_mavis.py --full    # 全量重扫
python3 scripts/record_mavis.py --limit 100  # 限制本次最多同步 N 条(调试)
```

## 表结构(Mavis `session_messages`)

```sql
CREATE TABLE session_messages (
    id         INTEGER PRIMARY KEY,
    session_id TEXT    NOT NULL,
    msg_id     TEXT    NOT NULL,
    role       TEXT,                    -- 'user' / 'assistant' / NULL(系统注入)
    data       TEXT    NOT NULL,        -- JSON 字符串(核心信息在这)
    timestamp  INTEGER NOT NULL         -- 毫秒
);
```

**过滤条件**:`role = 'user' AND msg_content 非空`

## 字段映射

Mavis `session_messages` → 录音机 `user_messages`:

| 录音机字段 | Mavis 来源 | 转换 |
|---|---|---|
| `message_id` | `msg_id` | 直接赋值,如 `umsg_xxx` |
| `session_file` | `session_id` | 拼成 `Mavis:session:<session_id>` |
| `timestamp` | `timestamp` | 毫秒 × 1000 → 微秒(统一 db schema) |
| `channel` | 固定 | `MiniMaxCode` |
| `sender_id` | `data.origin.rawMeta.senderId` 或 `data.source` | 见下方优先级 |
| `content` | `data.msg_content` | JSON 字段 |
| `date` | `timestamp` | YYYYMMDD 北京时间 |
| `has_attachment` | 固定 | `0`(MiniMaxCode schema 不存附件) |

**sender_id 提取优先级**(2026-07-01 决定):
1. `data.origin.rawMeta.senderId`(飞书用户 ID,如 `ou_xxx`)
2. `data.source`(CLI/API/cron 触发,如 `api`、`cron`)

## 增量 checkpoint

**特殊设计**:Mavis 是单库,跨 session 一起扫,用一个全局 checkpoint。

- key: `"__Mavis_global__"`
- value: `last_timestamp = sm.id`(INTEGER,**用 id 不用 timestamp**,因为 id 是自增主键,严格单调,避免时钟回拨)
- 注意:`last_timestamp` 字段名是历史遗留,语义在这里其实是"已扫到的最大 sm.id"

跟 OpenClaw 的 session_file 路径(`~/.openclaw/agents/.../*.jsonl`)天然隔离,互不干扰。

## 用户分布(2026-07-01 调查)

MiniMaxCode 渠道下的 sender_id 主要分两类:

**飞书用户**(5 个 ou_xxx,实际上是同一人的多飞书号):
- `ou_cd84288d35925aa490f67332327972dd` → mavis
- `ou_c1799e09e24951a31ce6dbf38156ea2f` → xiaoyan
- `ou_e593dc144927a5dd3b103f51ec2273db` → coder
- `ou_37683ad7bedafb3c10e15fbdbec58fe7` → xiaozhuo
- `ou_41997d1d375bc9c45329398400c1a622` → xiaojiang

**非飞书触发**:
- `api` → API/CLI 调用
- `cron` → 定时任务
- `system` → 系统注入

## 不入库的内容

**过滤逻辑(2026-07-01 对抗式审查后收紧)**:

### 1. SQL 过滤(写入层)

```sql
WHERE role = 'user'
  AND json_extract(data, '$.msg_content') IS NOT NULL
  AND trim(json_extract(data, '$.msg_content')) != ''
  AND json_extract(data, '$.origin.rawMeta.senderId') IN (
    'ou_cd84288d35925aa490f67332327972dd',  -- mavis
    'ou_c1799e09e24951a31ce6dbf38156ea2f',  -- xiaoyan
    'ou_e593dc144927a5dd3b103f51ec2273db',  -- coder
    'ou_37683ad7bedafb3c10e15fbdbec58fe7',  -- xiaozhuo
    'ou_41997d1d375bc9c45329398400c1a622'   -- xiaojiang
  )
```

### 2. 排除项

| 排除项 | 来源 | 数量(2026-07-01) | 为什么 |
|---|---|---|---|
| `role = 'assistant'` | AI 回复 | ~5000 | 只要 user 说的 |
| `role IS NULL` | 系统注入 | ~340 | 元信息块 |
| `source = 'api'` | mavis team plan spawn / CLI | 160 | 用户口径"API 调用不该录" |
| `source = 'cron'` / `system` | 定时任务 | 10 | 不是真人 |
| `source = 'communication'` | 跨 session 通信 | 1 | 不是用户自然对话 |
| `senderId IS NULL` | 老数据 / permission-response | 20 | 是系统权限响应,不是用户说的 |
| `msg_content` 空 | 异常 | ~50 | 无内容 |
| 5 个 ou_xxx 之外的 sender | 其他飞书号 | 0(本机) | 白名单外不录 |

### 3. 5 个 ou_xxx 白名单

用户承认这 5 个飞书号都是自己(2026-07-01 确认):

| sender_id | agent | 说明 |
|---|---|---|
| `ou_cd84288d35925aa490f67332327972dd` | mavis | 默认用户号 |
| `ou_c1799e09e24951a31ce6dbf38156ea2f` | xiaoyan | 第二飞书号 |
| `ou_e593dc144927a5dd3b103f51ec2273db` | coder | 第三飞书号 |
| `ou_37683ad7bedafb3c10e15fbdbec58fe7` | xiaozhuo | 当前对话的飞书号 |
| `ou_41997d1d375bc9c45329398400c1a622` | xiaojiang | 第五飞书号 |

> ⚠️ **副作用**:之前 2026-07-01 调查时入库的 160 条 `api` 来源(其实是用户的真实对话)被识别后删除。这是按用户"API 调用不该录"的口径执行的,但意味着这些对话**永久丢失**。如果将来想保留,需要把白名单放宽到"任何真人 sender_id"。

## 对抗式审查历史

### 2026-07-01 第一轮

**问题**:最初 SQL 只过滤 `role='user' AND msg_content 非空`,导致入库 1132 条,实际只有 941 条是用户的自然飞书对话。

**错录明细**(共 191 条已 DELETE):
- `sender='api'`:160 条 —— 用户说"API 调用的不该录"
- `sender='system'`:10 条 —— cron 定时任务
- `sender=''`(空):15 条 —— 异常数据
- `sender='channel:feishu'`:5 条 —— 老数据无 senderId,内容是 `<permission-response>` XML
- `sender='communication'`:1 条 —— 跨 session 通信

**修复**:
1. `record_mavis.py` 加 `USER_SENDER_IDS` 白名单(5 个 ou_xxx)
2. SQL 加 `senderId IN (...)` 过滤
3. DELETE 已入库的 191 条脏数据
4. 净入库 941 条(全部白名单内)

**口径冲突说明**:
- 用户口径 1:"5 个 ou_xxx 都是我" → 这些都该录
- 用户口径 2:"API 调用不该录" → `source=api` 不该录
- 160 条 `api` 来源**其实是用户在 mavis team plan / CLI 模式下的真实对话**,但按口径 1(只录 5 个 ou_xxx)+ 口径 2(api 不录),它们都被排除
- 用户拍板:按原口径删(2026-07-01 15:08)

## 调查方法参考

完整 Mavis 调查见 `C:\Users\辰辰洋洋\.mavis\MiniMax_Code_消息记录调查报告.md`(2026-07-01)。

**复现 SQL**:
```sql
-- 查某用户最近 N 句
SELECT datetime(timestamp/1000, 'unixepoch', 'localtime') AS time,
       msg_id,
       json_extract(data, '$.msg_content') AS content
FROM session_messages
WHERE role = 'user'
ORDER BY timestamp DESC
LIMIT 10;

-- 查某关键词
SELECT timestamp, json_extract(data, '$.msg_content')
FROM session_messages
WHERE role = 'user'
  AND json_extract(data, '$.msg_content') LIKE '%关键词%'
ORDER BY timestamp DESC;
```

## 已知坑

1. **db.py 路径 bug(2026-07-01 修复)**:之前在 WSL 下跑过录音机,db_registry 记的 WSL 路径回到 Windows 下打不开。已加 `_resolve_data_path` 自动转 Windows 路径。
2. **session_messages 是按 id 排序而非 timestamp**:所以 checkpoint 用 id,不用 timestamp。
3. **跨 session 的同一 sender_id 算同一个人**:1 个用户多个飞书号,入库后用 sender_id 聚合就能看到全貌。