#!/usr/bin/env python3
"""
每日检查 v4.0
数据库操作层：负责 issues 表的读写
Lint 逻辑由 AI 根据各技能 SKILL.md 中的 Lint 模块描述执行
"""

import sqlite3
import os
import re
from datetime import datetime, date
from pathlib import Path

# ============================================================
# 配置
# ============================================================

SKILL_WORKSPACE = Path.home() / ".openclaw/workspace/skills"
DB_DIR = Path("/mnt/d/2Study/StudyNotes/.db")
DB_PATH = DB_DIR / "daily_check.db"


# ============================================================
# 数据库初始化
# ============================================================

def init_db():
    """初始化数据库，创建 issues 表"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill TEXT NOT NULL,
            key TEXT NOT NULL,
            desc TEXT,
            status TEXT DEFAULT 'open',
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            count INTEGER DEFAULT 1,
            UNIQUE(skill, key)
        )
    """)
    conn.commit()
    conn.close()


def get_db_path():
    """返回数据库路径"""
    return str(DB_PATH)


# ============================================================
# 问题记录
# ============================================================

def upsert_issue(skill: str, key: str, desc: str):
    """
    插入或更新问题记录
    key = 问题类型（如 calorie_overdue, missing_weight, orphan）
    - 不存在：INSERT，count=1
    - 存在+resolved：重新打开，count++
    - 存在+open：更新 desc、count++、updated_at
    - 存在+ignored：跳过
    """
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()

    c.execute("SELECT id, status, count FROM issues WHERE skill=? AND key=?", (skill, key))
    row = c.fetchone()

    if row is None:
        c.execute("""
            INSERT INTO issues (skill, key, desc, status, found_at, updated_at, count)
            VALUES (?, ?, ?, 'open', ?, ?, 1)
        """, (skill, key, desc, now, now))

    elif row[1] == "resolved":
        c.execute("""
            UPDATE issues SET status='open', updated_at=?, count=?, desc=?
            WHERE skill=? AND key=?
        """, (now, row[2] + 1, desc, skill, key))

    elif row[1] == "open":
        c.execute("""
            UPDATE issues SET updated_at=?, count=count+1, desc=?
            WHERE skill=? AND key=?
        """, (now, desc, skill, key))

    # ignored 状态不处理

    conn.commit()
    conn.close()


def resolve_issue(skill: str, key: str):
    """标记问题为已解决"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        UPDATE issues SET status='resolved', resolved_at=?, updated_at=?
        WHERE skill=? AND key=?
    """, (now, now, skill, key))
    conn.commit()
    conn.close()


def ignore_issue(skill: str, key: str):
    """标记问题为忽略"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        UPDATE issues SET status='ignored', updated_at=?
        WHERE skill=? AND key=?
    """, (now, skill, key))
    conn.commit()
    conn.close()


def get_open_issues():
    """获取所有 open 问题，按技能分组"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT skill, key, desc, status, count, found_at, updated_at
        FROM issues
        WHERE status='open'
        ORDER BY skill, key
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_issues():
    """获取所有问题（含 resolved/ignored）"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT skill, key, desc, status, count, found_at, updated_at
        FROM issues
        ORDER BY skill, key
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def clear_all_issues():
    """清空所有问题记录（用于测试）"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("DELETE FROM issues")
    conn.commit()
    conn.close()


# ============================================================
# 技能扫描
# ============================================================

def resolve_skill_path(skill_name: str) -> Path:
    """解析技能真实路径（跟随桥接跳转）"""
    workspace_sk = SKILL_WORKSPACE / skill_name / "SKILL.md"
    if not workspace_sk.exists():
        return workspace_sk

    content = workspace_sk.read_text(encoding="utf-8")
    if "本文件为桥接" not in content and "实际技能本体位于" not in content:
        return workspace_sk

    for line in content.split("\n"):
        if "/mnt/d/" in line:
            m = re.search(r'/mnt/d/[^\s`"\']+', line)
            if m:
                return Path(m.group(0).rstrip('`'))
        elif "D:\\" in line or "D:/" in line:
            m = re.search(r'D:[/\\][^\s`"\']+', line)
            if m:
                path_str = m.group(0).replace('\\', '/').replace('D:', '/mnt/d')
                return Path(path_str)

    return workspace_sk


def scan_skills_with_lint():
    """扫描 skills 目录，返回有 Lint 模块的技能列表"""
    results = []

    if not SKILL_WORKSPACE.exists():
        return results

    for skill_dir in SKILL_WORKSPACE.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_name = skill_dir.name

        real_path = resolve_skill_path(skill_name)
        if not real_path.exists():
            continue

        content = real_path.read_text(encoding="utf-8")
        if "Lint" not in content and "lint" not in content:
            continue

        results.append(skill_name)

    return results


# ============================================================
# 主流程（仅展示用）
# ============================================================

def generate_report(issues):
    """生成检查报告"""
    from collections import defaultdict

    # 按技能分组
    by_skill = defaultdict(list)
    for skill, key, desc, status, count, found_at, updated_at in issues:
        by_skill[skill].append((key, desc, count, found_at, updated_at))

    def fmt_time(ts):
        if not ts:
            return ""
        return ts[5:10] + " " + ts[11:16]  # MM-DD HH:MM

    report_lines = []

    skills_with_lint = scan_skills_with_lint()
    all_skills = sorted(set(skills_with_lint))

    for skill in all_skills:
        if skill not in by_skill or not by_skill[skill]:
            report_lines.append(f"【{skill}】✅")
            continue

        items = by_skill[skill]
        total_issues = len(items)
        report_lines.append(f"【{skill}】⚠️ {total_issues}")

        for key, desc, count, found_at, updated_at in items:
            # 判断图标（根据 key 类型）
            sev_icon = "🔴"
            if key in ["orphan", "no_record", "missing_weight"]:
                sev_icon = "ℹ️"
            elif key in ["broken_link", "express_overdue", "calorie_overdue", "item_no_tag", "calorie_under"]:
                sev_icon = "🟡"

            desc_short = desc[:30] + '...' if len(desc) > 30 else desc
            time_str = fmt_time(updated_at)
            report_lines.append(f"  {sev_icon} {desc_short}  {time_str}")

    return "\n".join(report_lines)


def main():
    print(f"\n{'='*60}")
    print(f"每日检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # 初始化数据库
    print("[Step 1] 初始化数据库")
    init_db()
    print(f"  数据库: {DB_PATH}\n")

    # 扫描有 Lint 的技能
    print("[Step 2] 扫描技能")
    skills_with_lint = scan_skills_with_lint()
    print(f"  发现 {len(skills_with_lint)} 个技能有 Lint: {', '.join(skills_with_lint)}\n")

    # 读取并展示问题
    print("[Step 3] 生成报告")
    issues = get_open_issues()
    print()
    print(f"📋 每日检查报告  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print(generate_report(issues))
    print()
    print(f"⚠️ {len(set(i[0] for i in issues))}技能有问题 · {len(issues)}问题待处理")
    print()


if __name__ == "__main__":
    main()
