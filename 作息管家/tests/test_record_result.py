"""T2 · 记录三件套结果 HTML 测试(2026-08-09 · 实施 #227)

锁定契约:
- render_record_result payload:三件套 = ① timeline(24h 主导分类) + ② past_hours(推断回溯窗口) + ③ stats(笔数/覆盖/缺口)
- 推断回溯窗口 = [新记录 time_end − 3h, 新记录 time_end](补记日不误标"未来"记录为已推断)
- 缺口时段:00:00→首条 / 相邻间隔 / 末条→24:00(区间合并)
- CLI:add 写库后自动生成三件套结果 HTML(记录一笔 → 三件套)
- render-record-result / render-receipt(旧名)可用;旧 render_receipt(legacy 回执)不受影响
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = str(SCRIPTS_DIR / "schedule_cli.py")

import schedule_html_render as _render
import schedule_db as _db


def _add(db_path, **kw):
    """CLI add 一条,返回解析后的 ok 输出"""
    defaults = dict(
        date="2026-07-15",
        time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="写代码", category="工作.开发",
        source_contents="用户消息原文", source_timestamps="10:05",
        analysis_reasoning="推理链",
    )
    defaults.update(kw)
    args = ["add"]
    for k, v in defaults.items():
        args += [f"--{k}", str(v)]
    out, err, rc = _run_cli(args, db_path)
    assert out and out["status"] == "ok", f"add failed: out={out}, err={err}, rc={rc}"
    return out


def _run_cli(args, db_path):
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_path)
    result = subprocess.run(
        [sys.executable, CLI] + args,
        capture_output=True, text=True, env=env, timeout=30,
        cwd=str(SCRIPTS_DIR.parent),
    )
    out = result.stdout.strip()
    if not out:
        return None, result.stderr, result.returncode
    start = out.find("{")
    if start < 0:
        return None, result.stderr, result.returncode
    try:
        return json.loads(out[start:]), None, result.returncode
    except Exception as e:
        return None, f"JSON parse error: {e}\nraw: {out}", result.returncode


def _payload(conn, rid, warning=None):
    return _render.render_record_result(rid, warning=warning)


def _insert(conn, rid=None, **kw):
    """直接调 add_record_full 写库(conn fixture 的临时库)"""
    defaults = dict(
        date="2026-07-15", time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="写代码", category="工作.开发",
        source_contents="原文", source_timestamps="10:05", analysis_reasoning="推理",
    )
    defaults.update(kw)
    return _db.add_record_full(**defaults)


# ===== 三件套 payload 结构 =====

def test_payload_three_pieces(conn):
    r1 = _insert(conn, time_start="09:00", time_end="10:00", activity="晨练")
    r2 = _insert(conn, time_start="11:00", time_end="12:00", activity="写代码")
    payload = _payload(conn, r2)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["meta"]["mode"] == "record-result"
    assert data["meta"]["title"] == "已记录"
    assert data["meta"]["record_id"] == r2
    # ① 时间轴:24 小时
    assert len(data["timeline"]) == 24
    assert all("hour" in c and "records_count" in c for c in data["timeline"])
    # ② 推断回溯:窗口 = [12:00−3h, 12:00] = [09:00, 12:00],两条都在窗口内
    assert len(data["past_hours"]) == 2
    assert data["meta"]["inference_window"] == {"start": "09:00", "end": "12:00", "hours": 3}
    new_one = [p for p in data["past_hours"] if p["is_new"]]
    assert len(new_one) == 1 and new_one[0]["id"] == r2
    # ③ 状态总览:笔数 / 覆盖 / 缺口
    assert data["stats"]["today_count"] == 2
    assert data["stats"]["today_mins"] == 120
    assert data["stats"]["gap_slots"][0]["text"] == "00:00 → 09:00"
    assert any(g["text"] == "10:00 → 11:00" for g in data["stats"]["gap_slots"])
    assert data["stats"]["gap_slots"][-1]["text"] == "12:00 → 24:00"
    # 3 操作按钮 prompt
    assert {"continue", "overview", "review"} <= set(data["prompts"])


def test_past_hours_window_three_hours(conn):
    _insert(conn, time_start="06:00", time_end="07:00", activity="早读")
    _insert(conn, time_start="19:00", time_end="20:00", activity="晚餐")
    r3 = _insert(conn, time_start="20:00", time_end="21:00", activity="散步")
    data = _payload(conn, r3)["data"]
    # 窗口 [18:00, 21:00]:19:00-20:00 + 新记录在窗口;06:00-07:00 排除
    assert data["meta"]["inference_window"]["start"] == "18:00"
    acts = {p["activity"] for p in data["past_hours"]}
    assert acts == {"晚餐", "散步"}


def test_past_hours_clamps_to_midnight(conn):
    r = _insert(conn, time_start="00:30", time_end="01:00", activity="夜读")
    data = _payload(conn, r)["data"]
    assert data["meta"]["inference_window"]["start"] == "00:00"
    assert data["meta"]["inference_window"]["end"] == "01:00"


def test_past_hours_excludes_future_on_backfill(conn):
    """补记日(非今天):窗口按新记录时段定,不把当天更晚的记录误标为「已推断」"""
    r1 = _insert(conn, date="2026-07-10", time_start="20:00", time_end="21:00", activity="未来时段")
    r2 = _insert(conn, date="2026-07-10", time_start="09:00", time_end="10:00", activity="补记晨间")
    data = _payload(conn, r2)["data"]
    acts = [p["activity"] for p in data["past_hours"]]
    assert acts == ["补记晨间"]
    assert data["meta"]["inference_window"] == {"start": "07:00", "end": "10:00", "hours": 3}


def test_gap_slots_merge_overlaps(conn):
    _insert(conn, time_start="09:00", time_end="10:00", activity="A")
    _insert(conn, time_start="09:30", time_end="11:00", activity="B(重叠)")
    r3 = _insert(conn, time_start="11:00", time_end="12:00", activity="C")
    data = _payload(conn, r3)["data"]
    texts = [g["text"] for g in data["stats"]["gap_slots"]]
    # 09:00-11:00 合并,无 10:00→09:30 伪缺口
    assert texts == ["00:00 → 09:00", "12:00 → 24:00"]


def test_warning_in_payload(conn):
    r = _insert(conn)
    data = _payload(conn, r, warning="💡 category 是一级,建议细化")["data"]
    assert data["warning"] == "💡 category 是一级,建议细化"


def test_legacy_render_receipt_intact(conn):
    """旧 render_receipt(legacy 回执)不受 T2 改造影响"""
    r = _insert(conn)
    payload = _render.render_receipt(r)
    assert payload["status"] == "ok"
    assert payload["data"]["meta"]["mode"] == "record-receipt"
    assert {"continue", "overview", "review"} <= set(payload["data"]["prompts"])
    assert payload["data"]["record"]["id"] == r


# ===== render_and_write 落盘 =====

def test_render_and_write_record_result(conn, tmp_path, monkeypatch):
    r = _insert(conn)
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    payload = _payload(conn, r)
    result = _render.render_and_write(payload, None)
    assert result["status"] == "ok"
    fp = Path(result["data"]["file_path"])
    assert fp.exists()
    assert result["data"]["mode"] == "record-result"
    assert "record" in str(fp) and "result" in str(fp)
    content = fp.read_text(encoding="utf-8")
    assert "全天作息时间轴" in content
    assert "推断回溯" in content
    assert "状态总览" in content
    assert "INJECT-DATA" not in content  # payload 已注入


# ===== CLI 链路 =====

def test_cli_add_auto_renders(tmp_path):
    """记录一笔 → 三件套结果 HTML(add 自动渲染)"""
    db = tmp_path / "test.db"
    _run_cli(["init"], db)
    out = _add(db, date="2026-07-15", time_start="14:00", time_end="15:00")
    rh = out["data"].get("result_html")
    assert rh is not None, f"add 应自动渲染三件套: {out}"
    assert rh["mode"] == "record-result"
    fp = Path(rh["file_path"])
    assert fp.exists()
    content = fp.read_text(encoding="utf-8")
    assert "全天作息时间轴" in content and "推断回溯" in content


def test_cli_render_record_result_and_alias(tmp_path):
    db = tmp_path / "test.db"
    _run_cli(["init"], db)
    out = _add(db)
    rid = out["data"]["id"]
    new, err, rc = _run_cli(["render-record-result", str(rid)], db)
    assert new and new["status"] == "ok" and new["data"]["mode"] == "record-result"
    old, err2, rc2 = _run_cli(["render-receipt", str(rid)], db)
    assert old and old["status"] == "ok" and old["data"]["mode"] == "record-result"
    assert Path(old["data"]["file_path"]).exists()
