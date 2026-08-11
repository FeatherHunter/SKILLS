"""plan_scenarios 域模块测试(实施 T5 · 制定次日计划)

锁定契约:
- COMMANDS 注册表含 plan-result,handler 签名 handler(args: list[str])
- 历史贴合:build_history_habits 按小时聚合分类计数降序;fit_events 判定
  match/drift/none;fit_rate = match/(match+drift)
- plan-result 命令:JSON 校验 / 日期规范化 / 历史窗口(过去 N 天)/ 冲突检测
  / 输出 plan/result/制定次日计划_*.html(08 动作层含 copy_data + copy_log)
- 渲染走 _naming_path + inject_into_template(不依赖 render_and_write 的 mode 表)
"""
import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest

import plan_scenarios as ps


# ===== COMMANDS 契约(T1 通道) =====

def test_commands_registry_has_plan_result():
    assert "plan-result" in ps.COMMANDS
    assert callable(ps.COMMANDS["plan-result"])


def test_discover_domain_finds_plan_scenarios(tmp_path):
    """T1 通道:真实脚本目录扫描能发现 plan_scenarios 的命令

    plan_scenarios 已被本测试文件顶部 import(T1 契约:sys.modules 已加载模块跳过),
    因此先 pop 再发现,验证真实注册路径。
    """
    import schedule_cli
    import plan_scenarios
    had = sys.modules.pop("plan_scenarios", None)
    try:
        registry = schedule_cli.discover_domain_commands(SCRIPTS_DIR)
    finally:
        if had is not None:
            sys.modules["plan_scenarios"] = had
    assert "plan-result" in registry
    # 注意:discover 重新 exec 产生新函数对象(T1 契约),断言可调用 + 命令名,不断言同一性
    assert callable(registry["plan-result"])
    assert registry["plan-result"].__name__ == "cmd_plan_result"


# ===== 历史习惯聚合 =====

def _rec(h, e, cat):
    return {"time_start": f"{h:02d}:00", "time_end": f"{e:02d}:00", "category": cat}


def test_build_history_habits_groups_by_hour():
    records = [
        _rec(9, 12, "工作"),
        _rec(9, 11, "工作"),
        _rec(10, 12, "学习"),
        _rec(13, 14, "餐饮"),
    ]
    habits = ps.build_history_habits(records)
    assert habits[9] == [("工作", 2)]          # 09-10 只有工作(两条)
    assert habits[10] == [("工作", 2), ("学习", 1)]
    assert habits[11] == [("工作", 1), ("学习", 1)]
    assert 13 in habits and habits[13] == [("餐饮", 1)]
    assert 8 not in habits                     # 无记录小时不出现


def test_build_history_habits_handles_bad_rows():
    records = [{"time_start": "bad", "time_end": "x", "category": "工作"}]
    assert ps.build_history_habits(records) == {}


def test_build_history_habits_default_category():
    records = [{"time_start": "09:00", "time_end": "10:00"}]
    habits = ps.build_history_habits(records)
    assert habits[9] == [("未知", 1)]


# ===== 贴合判定 =====

def test_fit_events_match():
    habits = {9: [("工作", 5)]}
    events = [{"time_start": "09:00", "time_end": "10:00", "title": "写代码", "category": "工作"}]
    fits = ps.fit_events(events, habits)
    assert fits[0]["fit"] == "match"
    assert fits[0]["history_top"] == "工作"
    assert "贴合" in fits[0]["hint"]


def test_fit_events_drift():
    habits = {9: [("工作", 5)]}
    events = [{"time_start": "09:00", "time_end": "10:00", "title": "跑步", "category": "运动"}]
    fits = ps.fit_events(events, habits)
    assert fits[0]["fit"] == "drift"
    assert fits[0]["history_top"] == "工作"
    assert "不同" in fits[0]["hint"]


def test_fit_events_none_no_history():
    events = [{"time_start": "03:00", "time_end": "04:00", "title": "夜班", "category": "工作"}]
    fits = ps.fit_events(events, {})
    assert fits[0]["fit"] == "none"
    assert fits[0]["history_top"] is None


def test_fit_events_multi_hour_aggregate():
    """跨小时事件聚合所有覆盖小时的分类"""
    habits = {9: [("工作", 3)], 10: [("学习", 2)], 11: [("学习", 4)]}
    events = [{"time_start": "09:30", "time_end": "11:30", "title": "上课", "category": "学习"}]
    fits = ps.fit_events(events, habits)
    # 09:30-11:30 覆盖 9/10/11 三小时:工作 3 vs 学习 6 → 学习胜出
    assert fits[0]["fit"] == "match"
    assert fits[0]["history_top"] == "学习"


def test_fit_events_unparsable_time_none():
    events = [{"time_start": "xx", "time_end": "yy", "title": "t", "category": "c"}]
    fits = ps.fit_events(events, {9: [("c", 1)]})
    assert fits[0]["fit"] == "none"
    assert "无法解析" in fits[0]["hint"]


def test_fit_rate():
    fits = [
        {"fit": "match"}, {"fit": "match"}, {"fit": "drift"}, {"fit": "none"},
    ]
    assert ps.fit_rate(fits) == 66.7


def test_fit_rate_all_none_is_none():
    assert ps.fit_rate([{"fit": "none"}, {"fit": "none"}]) is None


def test_fit_rate_empty():
    assert ps.fit_rate([]) is None


# ===== 命令解析与校验 =====

def test_cmd_plan_result_no_args(capsys):
    ps.cmd_plan_result([])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "用法" in out["message"]


def test_cmd_plan_result_missing_json(capsys):
    ps.cmd_plan_result(["2026-07-20"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "--json" in out["message"]


def test_cmd_plan_result_bad_json_file(capsys, tmp_path):
    missing = tmp_path / "nope.json"
    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(missing)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "不存在" in out["message"]


def test_cmd_plan_result_invalid_events(capsys, tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps([{"title": "缺时间"}]), encoding="utf-8")
    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(f)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "校验失败" in out["message"]


def test_cmd_plan_result_bad_date(capsys, tmp_path):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps([{"time_start": "09:00", "time_end": "10:00", "title": "t"}]), encoding="utf-8")
    ps.cmd_plan_result(["2026/13/99", "--json", "@" + str(f)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "date" in out["message"]


def test_cmd_plan_result_bad_history_days(capsys, tmp_path):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps([{"time_start": "09:00", "time_end": "10:00", "title": "t"}]), encoding="utf-8")
    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(f), "--history-days", "9999"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "范围" in out["message"]


# ===== 渲染 e2e(隔离 DB) =====

@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """SKILLS_DB_PATH 指向临时目录(操作规范 §7 运行时隔离)"""
    db_dir = tmp_path / "dbhome"
    db_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("SKILLS_DB_PATH", str(db_dir))
    return db_dir


def test_cmd_plan_result_renders_html(capsys, tmp_path, isolated_env, monkeypatch):
    """完整链路:候选 JSON → 历史窗口查询 → 渲染 HTML → copy_data/copy_log"""
    import sqlite3
    import schedule_db

    # 建库 + 历史记录(过去 7 天内同段习惯 = 工作)
    db_path = tmp_path / "test_schedule.db"
    init = sqlite3.connect(str(db_path))
    init.row_factory = sqlite3.Row
    init.executescript("""
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, time_start TEXT NOT NULL, time_end TEXT NOT NULL,
            duration_minutes INTEGER, activity TEXT NOT NULL, category TEXT NOT NULL,
            source_contents TEXT, source_timestamps TEXT, analysis_reasoning TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL, category TEXT NOT NULL, total_minutes INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (date, category)
        );
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, title TEXT NOT NULL,
            notes TEXT, category TEXT, feishu_event_id TEXT, last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1, completion TEXT DEFAULT NULL,
            completion_note TEXT DEFAULT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    init.commit()
    for d in ("2026-07-13", "2026-07-14", "2026-07-15"):
        init.execute(
            "INSERT INTO schedule_records (date, time_start, time_end, duration_minutes, activity, category) VALUES (?,?,?,?,?,?)",
            (d, "09:00", "12:00", 180, "写代码", "工作"))
    init.commit()
    init.close()

    def _factory():
        new = sqlite3.connect(str(db_path))
        new.row_factory = sqlite3.Row
        return new
    monkeypatch.setattr(schedule_db, "get_connection", _factory)

    # 候选 24h 计划(09-12 工作 → 应 match)
    events = [
        {"time_start": "00:00", "time_end": "08:00", "title": "睡眠", "category": "睡眠"},
        {"time_start": "08:00", "time_end": "09:00", "title": "洗漱", "category": "洗漱"},
        {"time_start": "09:00", "time_end": "12:00", "title": "写代码", "category": "工作"},
        {"time_start": "12:00", "time_end": "13:00", "title": "午饭", "category": "餐饮"},
        {"time_start": "13:00", "time_end": "18:00", "title": "工作", "category": "工作"},
        {"time_start": "18:00", "time_end": "20:00", "title": "晚饭", "category": "餐饮"},
        {"time_start": "20:00", "time_end": "22:00", "title": "娱乐", "category": "娱乐"},
        {"time_start": "22:00", "time_end": "00:00", "title": "睡眠", "category": "睡眠"},
    ]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")

    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(plan_file), "--history-days", "7"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    data = out["data"]
    assert data["mode"] == "plan-result"
    assert data["history_days"] == 7
    assert data["history_record_count"] == 3
    assert data["match_count"] >= 1

    fp = Path(data["file_path"])
    assert fp.exists()
    html = fp.read_text(encoding="utf-8")
    # 注入契约:payload 锚点 + 内联数据
    assert '<script id="payload" type="application/json">' in html
    assert '"mode": "plan-result"' in html or '"mode":"plan-result"' in html  # Base injector 标准 dumps(带空格)
    # 08 动作层:复制数据/复制日志按钮
    assert "复制数据" in html
    assert "复制日志" in html
    # 时间轴容器
    assert 'id="timeline"' in html
    assert 'id="habit-strip"' in html
    # 命名合规:plan/result/制定次日计划_*.html(Windows 用 os.sep)
    assert ("plan" + os.sep + "result") in str(fp)
    assert "制定次日计划" in fp.name


def test_cmd_plan_result_no_history_none(capsys, tmp_path, isolated_env, monkeypatch):
    """无历史记录 → 全部 none,fit_rate=None,仍可渲染(缺数据兜底不降级)"""
    import sqlite3
    import schedule_db

    db_path = tmp_path / "empty.db"
    init = sqlite3.connect(str(db_path))
    init.row_factory = sqlite3.Row
    init.executescript("""
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, duration_minutes INTEGER,
            activity TEXT NOT NULL, category TEXT NOT NULL, source_contents TEXT,
            source_timestamps TEXT, analysis_reasoning TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL, category TEXT NOT NULL, total_minutes INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (date, category)
        );
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, title TEXT NOT NULL,
            notes TEXT, category TEXT, feishu_event_id TEXT, last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1, completion TEXT DEFAULT NULL,
            completion_note TEXT DEFAULT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    init.commit()
    init.close()

    def _factory():
        new = sqlite3.connect(str(db_path))
        new.row_factory = sqlite3.Row
        return new
    monkeypatch.setattr(schedule_db, "get_connection", _factory)

    events = [
        {"time_start": "00:00", "time_end": "08:00", "title": "睡眠", "category": "睡眠"},
        {"time_start": "08:00", "time_end": "23:00", "title": "做事", "category": "工作"},
        {"time_start": "23:00", "time_end": "00:00", "title": "睡眠", "category": "睡眠"},
    ]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")

    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(plan_file)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["data"]["fit_rate"] is None
    assert out["data"]["none_count"] == 3
    fp = Path(out["data"]["file_path"])
    assert fp.exists()


def test_cmd_plan_result_conflict_detected(capsys, tmp_path, isolated_env, monkeypatch):
    """已锁定事件与候选重叠 → conflict 状态 + conflicts 计数"""
    import sqlite3
    import schedule_db

    db_path = tmp_path / "lock.db"
    init = sqlite3.connect(str(db_path))
    init.row_factory = sqlite3.Row
    init.executescript("""
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, duration_minutes INTEGER,
            activity TEXT NOT NULL, category TEXT NOT NULL, source_contents TEXT,
            source_timestamps TEXT, analysis_reasoning TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL, category TEXT NOT NULL, total_minutes INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (date, category)
        );
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, title TEXT NOT NULL,
            notes TEXT, category TEXT, feishu_event_id TEXT, last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1, completion TEXT DEFAULT NULL,
            completion_note TEXT DEFAULT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    init.commit()
    # 当日已锁定 10:00-12:00 健身
    init.execute(
        "INSERT INTO schedule_plans (date, time_start, time_end, title, category, is_active) VALUES (?,?,?,?,?,1)",
        ("2026-07-20", "10:00", "12:00", "健身", "运动"))
    init.commit()
    init.close()

    def _factory():
        new = sqlite3.connect(str(db_path))
        new.row_factory = sqlite3.Row
        return new
    monkeypatch.setattr(schedule_db, "get_connection", _factory)

    events = [
        {"time_start": "00:00", "time_end": "09:00", "title": "睡眠", "category": "睡眠"},
        {"time_start": "09:00", "time_end": "11:00", "title": "写代码", "category": "工作"},
        {"time_start": "12:00", "time_end": "24:00", "title": "工作", "category": "工作"},
    ]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")

    ps.cmd_plan_result(["2026-07-20", "--json", "@" + str(plan_file)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["data"]["locked_count"] == 1
    assert out["data"]["conflict_count"] == 1
    html = Path(out["data"]["file_path"]).read_text(encoding="utf-8")
    assert '"status": "conflict"' in html or '"status":"conflict"' in html  # Base injector 标准 dumps(带空格)


def test_commands_dispatch_via_cli(capsys, tmp_path, isolated_env, monkeypatch):
    """T1 通道端到端:schedule_cli.py plan-result ... 自动 dispatch"""
    import subprocess
    import os
    import sys as _sys

    events = [
        {"time_start": "00:00", "time_end": "08:00", "title": "睡眠", "category": "睡眠"},
        {"time_start": "08:00", "time_end": "24:00", "title": "工作", "category": "工作"},
    ]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(isolated_env)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [_sys.executable, str(SCRIPTS_DIR / "schedule_cli.py"),
         "plan-result", "2026-07-20", "--json", "@" + str(plan_file)],
        capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["status"] == "ok"
    assert out["data"]["mode"] == "plan-result"
    assert Path(out["data"]["file_path"]).exists()
