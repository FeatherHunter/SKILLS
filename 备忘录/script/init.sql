PRAGMA journal_mode=WAL;

-- 备忘录核心表
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL,
    summary     TEXT,                     -- AI生成的短摘要，用于列表预览
    category    TEXT DEFAULT 'general',   -- 用户自定义分类：social, wish, inspiration 等
    media_path  TEXT,                     -- 附件相对路径，如 media/20260522_abc.jpg
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
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS idx_reminders_status_remind ON reminders(status, remind_at);