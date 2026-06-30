PRAGMA journal_mode=WAL;

-- 备忘录核心表
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL,
    summary     TEXT,                     -- AI生成的短摘要，用于列表预览
    category    TEXT DEFAULT '备忘',       -- 顶层功能分类：备忘/心愿/打卡/情绪日记
    sub_category TEXT,                    -- 备忘内部分类：社交/工作/学习/灵感/记账/成就（仅 category=备忘 时用）
    media_path  TEXT,                     -- 附件相对路径，如 media/20260522_abc.jpg
    reminder_id INTEGER,                  -- 关联提醒ID（打卡可追溯来源）
    feishu_task_guid TEXT,                -- 飞书 task GUID（心愿同步飞书时记录，用于反向查找）
    due TEXT,                             -- 心愿期望完成日期 (YYYY-MM-DD, 第一性: 备忘录是 SoT, 飞书是镜像)
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 全文搜索虚拟表 (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    content,
    category,
    content=notes,
    content_rowid=id,
    tokenize='unicode61'
);

-- 触发器：插入时同步FTS
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, content, category) VALUES (new.id, new.content, new.category);
END;

-- 触发器：更新时同步FTS
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
    INSERT INTO notes_fts(rowid, content, category) VALUES (new.id, new.content, new.category);
END;

-- 触发器：删除时同步FTS
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
END;

-- 提醒表
CREATE TABLE IF NOT EXISTS reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id     INTEGER NOT NULL,                -- 强制关联一条笔记
    remind_at   TEXT,                            -- 一次性提醒时间，ISO格式如 "2026-05-25 09:00"
    repeat_type TEXT DEFAULT 'none',             -- none/daily/weekly/monthly/yearly
    repeat_rule TEXT,                            -- 重复规则：
                                                --   daily   : "09:00"
                                                --   weekly  : "3 09:00" (周日=0)
                                                --   monthly : "15 08:30"
                                                --   yearly  : "12-25 10:00"
    status      TEXT DEFAULT 'active',           -- active / dismissed
    notified_at TEXT,                            -- 上次通知时间
    content     TEXT,                            -- 提醒内容（可不同于 notes.content，提醒独有）
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    -- NO ACTION（不是 CASCADE）：删除 note 前必须先手动删 reminders
    -- 代码负责手动级联（见 memo_cli.py delete_note --with-reminders 和 complete_wish）
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE NO ACTION
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS idx_reminders_status_remind ON reminders(status, remind_at);