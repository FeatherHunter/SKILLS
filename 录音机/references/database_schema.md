# Daily Recorder - 数据库表结构

## user_messages

记录用户消息（只存有文字内容的）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| message_id | VARCHAR(255) | OpenClaw 消息唯一ID，用于去重 |
| session_file | VARCHAR(500) | 来源的 session 文件路径 |
| timestamp | INTEGER | Unix 微秒时间戳（去重+排序） |
| channel | VARCHAR(50) | 渠道：qq/wechat/pc |
| sender_id | VARCHAR(255) | 发送者ID |
| content | TEXT | 消息内容原文（ASR 或纯文本） |
| date | VARCHAR(8) | 归属日期 YYYYMMDD |
| has_attachment | INTEGER | 是否附带附件（0/1） |
| created_at | INTEGER | 记录入库时间（Unix 秒） |

## user_attachments

记录用户发送的图片/文件/语音附件。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| message_id | VARCHAR(255) | 关联的消息ID |
| session_file | VARCHAR(500) | 来源的 session 文件路径 |
| timestamp | INTEGER | Unix 微秒时间戳 |
| channel | VARCHAR(50) | 渠道：qq/wechat/pc |
| sender_id | VARCHAR(255) | 发送者ID |
| file_path | TEXT | 文件路径 |
| file_type | VARCHAR(50) | MIME 类型：image/jpeg, audio/wav, file/md 等 |
| created_at | INTEGER | 记录入库时间（Unix 秒） |

## scan_checkpoint

记录每个 session 文件的扫描进度，实现增量扫描。

| 字段 | 类型 | 说明 |
|------|------|------|
| session_file | VARCHAR(500) | session 文件路径（主键） |
| last_timestamp | INTEGER | 最后扫描到的时间戳（微秒） |
| last_message_id | VARCHAR(255) | 最后一条消息的 ID |
| updated_at | INTEGER | 最后更新时间（Unix 秒） |

## 索引

- `idx_um_date`：按日期快速查询 user_messages
- `idx_um_timestamp`：按时间戳排序和范围查询 user_messages
- `idx_ua_timestamp`：按时间戳排序和范围查询 user_attachments

## 内容提取逻辑

消息内容可能有多种格式，提取规则：

| 格式 | 处理方式 |
|------|---------|
| `- ASR: xxx` | 提取 `xxx` 作为内容 |
| `[Voice message] xxx` | 提取 `xxx` 作为内容 |
| `[Day GMT+8] xxx` | 提取 `xxx` 作为内容 |
| 纯自然语言 | 直接保留全文 |
| `Conversation info` | 元数据块，提取 channel/sender_id，不作为内容 |
| `Sender (untrusted` | 元数据块，提取 sender_id，不作为内容 |
| `- Voice: /path/...` | 媒体路径，提取为附件，不作为内容 |
| `- Images: /path/...` | 媒体路径，提取为附件，不作为内容 |
| `[media attached: /path...]` | 媒体路径，提取为附件，不作为内容 |
| `[Attachment: /path...]` | 附件路径，提取为附件，不作为内容 |

## 渠道判断

从 Conversation info 的 chat_id 字段提取：
- 包含 `qqbot` → `qq`
- 包含 `weixin` 或 `wechat` → `wechat`
- 其他 → `pc`

## 文件类型

根据文件扩展名推断 MIME 类型：
- `.jpg` / `.jpeg` → `image/jpeg`
- `.png` → `image/png`
- `.gif` → `image/gif`
- `.wav` → `audio/wav`
- `.mp3` → `audio/mpeg`
- `.md` → `file/markdown`
- 其他 → `application/octet-stream`