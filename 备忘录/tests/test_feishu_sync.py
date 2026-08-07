"""feishu_sync.py 权限编排 + 4 BUG 修复测试(#197 · 2026-08-08)

覆盖:
- 主线:REQUIRED_SCOPES 单一真值源 / check_permissions 差集 / app_scopes 提示层 /
       sentinel 6 项真打(task create/update/complete + calendar create/update/delete)/
       check 状态机(missing → 跳过 sentinel;全过 → 跑 sentinel)
- 伴随线:B1 .cmd 优先 + cwd / B3 reset_user_open_id_cache / B4 traceback 兜底 /
       B1子 _backfill_local_wishes 传 due_iso

原则:只测外部可观察行为;lark-cli 全部 mock;不碰真实飞书。
"""
import json
import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_feishu_state():
    import feishu_sync
    feishu_sync.reset_user_open_id_cache()
    feishu_sync._LARK_CLI_CACHE = {"path": None, "fetched_at": 0.0}
    yield
    feishu_sync.reset_user_open_id_cache()
    feishu_sync._LARK_CLI_CACHE = {"path": None, "fetched_at": 0.0}


# ==================== 主线:REQUIRED_SCOPES ====================

def test_required_scopes_single_source():
    """REQUIRED_SCOPES = task 2 + calendar 3 写权限(单一真值源)"""
    import feishu_sync
    assert len(feishu_sync.REQUIRED_SCOPES) == 5
    for s in ("task:task:write", "task:tasklist:write",
              "calendar:calendar.event:create",
              "calendar:calendar.event:update",
              "calendar:calendar.event:delete"):
        assert s in feishu_sync.REQUIRED_SCOPES


# ==================== 伴随线:B1 .cmd 优先 + cwd ====================

def test_find_lark_cli_windows_prefers_cmd(monkeypatch):
    """B1:Windows where 多行输出优先 .cmd(即使 .exe 在前)"""
    import feishu_sync
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(feishu_sync.os, "environ", {})  # 无 APPDATA → 走 where
    fake_out = b"C:\\tools\\lark-cli.exe\nC:\\Users\\x\\AppData\\Roaming\\npm\\lark-cli.cmd\n"

    def fake_run(cmd, **kwargs):
        class P:
            returncode = 0
            stdout = fake_out
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run)
    found = feishu_sync._find_lark_cli()
    assert found is not None
    assert str(found).lower().endswith(".cmd")


def test_run_lark_uses_cmd_cwd_on_windows(monkeypatch):
    """B1:_run_lark 在 Windows 且 cli 是 .cmd 时,cwd = .cmd 所在目录"""
    import feishu_sync
    monkeypatch.setattr("sys.platform", "win32")
    cmd_path = "C:\\Users\\x\\AppData\\Roaming\\npm\\lark-cli.cmd"
    monkeypatch.setattr(feishu_sync, "_LARK_CLI_CACHE", {"path": cmd_path, "fetched_at": 0.0})
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        class P:
            stdout = '{"ok": true}'
            stderr = ""
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run)
    feishu_sync._run_lark(["task", "+get-my-tasks"])
    assert captured["cwd"] == "C:\\Users\\x\\AppData\\Roaming\\npm"


def test_get_user_open_id_uses_cmd_cwd_on_windows(monkeypatch):
    """B1:_get_user_open_id 同样带 cwd(与 _run_lark 一致)"""
    import feishu_sync
    monkeypatch.setattr("sys.platform", "win32")
    cmd_path = "C:\\Users\\x\\AppData\\Roaming\\npm\\lark-cli.cmd"
    monkeypatch.setattr(feishu_sync, "_LARK_CLI_CACHE", {"path": cmd_path, "fetched_at": 0.0})
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: True)
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        class P:
            stdout = b'{"identities": {"user": {"openId": "ou_abc"}}}'
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run)
    assert feishu_sync._get_user_open_id() == "ou_abc"
    assert captured["cwd"] == "C:\\Users\\x\\AppData\\Roaming\\npm"


# ==================== 伴随线:B3 reset ====================

def test_reset_user_open_id_cache_clears_failed(monkeypatch):
    """B3:失败标志 + 缓存可整体重置(登录后重跑不再永久报未登录)"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_USER_OPEN_ID_FAILED", True)
    monkeypatch.setattr(feishu_sync, "_USER_OPEN_ID_CACHE", "ou_stale")
    feishu_sync.reset_user_open_id_cache()
    assert feishu_sync._USER_OPEN_ID_FAILED is False
    assert feishu_sync._USER_OPEN_ID_CACHE is None


def test_get_user_open_id_retries_after_reset(monkeypatch):
    """B3:先失败后 reset → 下一次调用重新探测(不再被失败标志卡死)"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_LARK_CLI_CACHE", {"path": "lark-cli", "fetched_at": 0.0})
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: True)

    calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls["n"] += 1
        class P:
            stdout = b''
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run)
    # 第一次:空输出 → 失败标记
    assert feishu_sync._get_user_open_id() is None
    assert feishu_sync._USER_OPEN_ID_FAILED is True
    # reset 后(模拟 auth login 完成),重新探测
    feishu_sync.reset_user_open_id_cache()

    def fake_run_ok(cmd, **kwargs):
        class P:
            stdout = b'{"identities": {"user": {"openId": "ou_new"}}}'
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run_ok)
    assert feishu_sync._get_user_open_id() == "ou_new"


# ==================== 伴随线:B4 traceback 兜底 ====================

def test_traceback_guard_decorator():
    """B4:装饰器把任何异常转成结构化 {ok: False, error: traceback}"""
    import feishu_sync

    @feishu_sync._traceback_guard
    def broken():
        raise ValueError("内部错误")

    r = broken()
    assert r["ok"] is False
    assert r["task_guid"] is None
    assert r["existed"] is False
    assert "ValueError" in r["error"]
    assert "Traceback" in r["error"]


def test_add_wish_sync_guard_on_exception(monkeypatch):
    """B4:add_wish_sync 异常 → error 带 traceback(不再是裸抛)"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")

    def boom(args, **kw):
        raise RuntimeError("lark-cli 崩溃了")

    monkeypatch.setattr(feishu_sync, "_run_lark", boom)
    r = feishu_sync.add_wish_sync(1, "测试心愿")
    assert r["ok"] is False
    assert "Traceback" in r["error"]


def test_update_complete_sync_guard_on_exception(monkeypatch):
    """B4:update/complete_wish_sync 异常同样兜底"""
    import feishu_sync

    def boom(args, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(feishu_sync, "_run_lark", boom)
    for fn, args in [
        (feishu_sync.update_wish_sync, ("guid_x", "新标题")),
        (feishu_sync.complete_wish_sync, ("guid_x",)),
        (feishu_sync.update_due_sync, ("guid_x", "2026-08-15")),
    ]:
        r = fn(*args)
        assert r["ok"] is False
        assert "Traceback" in r["error"]


# ==================== 伴随线:B1子 _backfill_local_wishes 传 due ====================

def test_backfill_local_wishes_passes_due(monkeypatch, in_memory_db):
    """B1子:补建时读 due 列传 due_iso 给 add_wish_sync(本地排期日期是 SoT)"""
    import feishu_sync
    conn = in_memory_db
    conn.execute(
        "INSERT INTO notes (content, category, due, created_at, updated_at) VALUES (?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))",
        ("心愿A", "心愿", "2026-08-15"),
    )
    conn.commit()
    captured = {}

    def fake_add(memo_id, content, category, tasklist_guid=None, due_iso=None):
        captured["due_iso"] = due_iso
        return {"ok": True, "task_guid": "guid_1", "error": None, "existed": False}

    monkeypatch.setattr(feishu_sync, "add_wish_sync", fake_add)
    n = feishu_sync._backfill_local_wishes(conn)
    assert n == 1
    assert captured["due_iso"] == "2026-08-15"


# ==================== 主线:权限差集 + app_scopes 提示层 ====================

def test_check_permissions_missing_diff(monkeypatch):
    """check_permissions:差集正确;app_scopes 不可读时 missing_in_app=None(提示层不脆)"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "get_granted_scopes",
                        lambda: ["task:task:write", "task:tasklist:write"])
    monkeypatch.setattr(feishu_sync, "get_app_scopes", lambda: [])
    p = feishu_sync.check_permissions()
    assert p["missing"] == ["calendar:calendar.event:create",
                            "calendar:calendar.event:update",
                            "calendar:calendar.event:delete"]
    assert p["app_scopes"]["readable"] is False
    assert p["app_scopes"]["missing_in_app"] is None
    assert p["note"] is not None  # 缺权限时给后台引导提示


def test_check_permissions_ok_and_app_scopes(monkeypatch):
    """check_permissions:全齐时 missing 空;app_scopes 可读时给缺失清单"""
    import feishu_sync
    full = list(feishu_sync.REQUIRED_SCOPES)
    monkeypatch.setattr(feishu_sync, "get_granted_scopes", lambda: full)
    monkeypatch.setattr(feishu_sync, "get_app_scopes",
                        lambda: full[:-2])  # 应用侧只开通了 3 个
    p = feishu_sync.check_permissions()
    assert p["missing"] == []
    assert p["app_scopes"]["readable"] is True
    assert p["app_scopes"]["missing_in_app"] == full[-2:]
    assert p["note"] is None  # 授权侧不缺,不引导


def test_check_scope_via_cli_exit_semantics(monkeypatch):
    """auth check exit 0=有 / 1=缺失"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_LARK_CLI_CACHE", {"path": "lark-cli", "fetched_at": 0.0})
    codes = [0, 1]

    def fake_run(cmd, **kwargs):
        class P:
            returncode = codes.pop(0)
        return P()

    monkeypatch.setattr(feishu_sync.subprocess, "run", fake_run)
    assert feishu_sync._check_scope_via_cli("task:task:write") is True
    assert feishu_sync._check_scope_via_cli("calendar:calendar.event:create") is False


# ==================== 主线:sentinel 真打 ====================

def test_sentinel_task_create_update_complete(monkeypatch):
    """sentinel task:create→update→complete 全调 + summary 带前缀;不调 delete(task 无 delete)"""
    import feishu_sync
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        if args[:2] == ["task", "+create"]:
            return {"ok": True, "data": {"task": {"guid": "g1"}}}
        return {"ok": True, "data": {}}

    monkeypatch.setattr(feishu_sync, "_run_lark", fake_run)
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")
    results = feishu_sync._sentinel_task("[备忘录测试]")
    assert [r["name"] for r in results] == ["task_create", "task_update", "task_complete"]
    assert all(r["ok"] for r in results)
    assert calls[0][3].startswith("[备忘录测试]")  # create 的 summary 带前缀
    assert not any("delete" in str(c) for c in calls)  # task 无 delete,complete 是终态


def test_sentinel_task_create_failure_short_circuits(monkeypatch):
    """sentinel task:create 失败 → 短路,不测 update/complete"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_run_lark", lambda args, **kw: {"ok": False, "error": "no perm"})
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")
    results = feishu_sync._sentinel_task("[备忘录测试]")
    assert [r["name"] for r in results] == ["task_create"]
    assert results[0]["ok"] is False
    assert results[0]["error"] == "no perm"


def test_sentinel_calendar_deletes_created_event(monkeypatch):
    """sentinel calendar:create→update→delete;delete 用 primary 日历;删失败 note 明示位置"""
    import feishu_sync
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        if args[:2] == ["calendar", "+create"]:
            return {"ok": True, "data": {"event": {"event_id": "ev_1"}}}
        if args[:3] == ["calendar", "events", "delete"]:
            return {"ok": False, "error": "权限不足"}
        return {"ok": True, "data": {}}

    monkeypatch.setattr(feishu_sync, "_run_lark", fake_run)
    results = feishu_sync._sentinel_calendar("[备忘录测试]")
    assert [r["name"] for r in results] == ["calendar_create", "calendar_update", "calendar_delete"]
    assert results[0]["ok"] and results[1]["ok"]
    assert results[2]["ok"] is False
    assert "手动删除" in results[2]["note"]  # 必清协议失败 → 明示资源位置
    delete_call = [c for c in calls if c[:3] == ["calendar", "events", "delete"]][0]
    assert delete_call[4] == "primary"


def test_run_sentinel_write_test_composes_domains(monkeypatch):
    """run_sentinel_write_test 组合 task + calendar 两组(mock 下 1+1;真实为 3+3),强制前缀贯穿"""
    import feishu_sync
    monkeypatch.setattr(feishu_sync, "_sentinel_task",
                        lambda prefix: [{"name": f"task_{prefix}", "ok": True}])
    monkeypatch.setattr(feishu_sync, "_sentinel_calendar",
                        lambda prefix: [{"name": f"cal_{prefix}", "ok": True}])
    results = feishu_sync.run_sentinel_write_test()
    assert len(results) == 2  # mock 后 1+1;真实为 3+3
    assert feishu_sync.SENTINEL_PREFIX == "[备忘录测试]"


# ==================== 主线:check 状态机 ====================

def test_check_missing_scopes_skips_sentinel(monkeypatch, capsys):
    """check:差集缺失 → sentinel skipped + status=missing_scopes + verdict 未实测"""
    import feishu_sync
    monkeypatch.setattr(sys, "argv", ["feishu_sync.py", "check"])
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: True)
    monkeypatch.setattr(feishu_sync, "get_lark_cli_path", lambda: "lark-cli")
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")
    monkeypatch.setattr(feishu_sync, "check_permissions", lambda: {
        "required": list(feishu_sync.REQUIRED_SCOPES),
        "granted": [], "missing": list(feishu_sync.REQUIRED_SCOPES),
        "app_scopes": {"readable": True, "missing_in_app": []}, "note": None,
    })
    called = {"sentinel": False}

    def fake_sentinel():
        called["sentinel"] = True
        return []

    monkeypatch.setattr(feishu_sync, "run_sentinel_write_test", fake_sentinel)
    feishu_sync.main()
    out = json.loads(capsys.readouterr().out)
    assert out["permissions"]["status"] == "missing_scopes"
    assert out["permissions"]["sentinel_write_test"]["skipped"] is True
    assert out["permissions"]["verdict"] == "飞书权限未实测:先补齐缺失权限"
    assert called["sentinel"] is False  # 缺权限不白跑 sentinel


def test_check_ok_runs_sentinel(monkeypatch, capsys):
    """check:差集全过 → 跑 sentinel → 全过 status=ok + verdict=已实测"""
    import feishu_sync
    monkeypatch.setattr(sys, "argv", ["feishu_sync.py", "check"])
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: True)
    monkeypatch.setattr(feishu_sync, "get_lark_cli_path", lambda: "lark-cli")
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")
    monkeypatch.setattr(feishu_sync, "check_permissions", lambda: {
        "required": [], "granted": [], "missing": [],
        "app_scopes": {"readable": True, "missing_in_app": []}, "note": None,
    })
    monkeypatch.setattr(feishu_sync, "run_sentinel_write_test", lambda: [
        {"name": "task_create", "ok": True, "error": None},
        {"name": "task_update", "ok": True, "error": None},
        {"name": "task_complete", "ok": True, "error": None},
        {"name": "calendar_create", "ok": True, "error": None},
        {"name": "calendar_update", "ok": True, "error": None},
        {"name": "calendar_delete", "ok": True, "error": None},
    ])
    feishu_sync.main()
    out = json.loads(capsys.readouterr().out)
    assert out["permissions"]["status"] == "ok"
    assert out["permissions"]["verdict"] == "飞书权限已实测"
    assert len(out["permissions"]["sentinel_write_test"]) == 6


def test_check_sentinel_failed_verdict(monkeypatch, capsys):
    """check:sentinel 有失败 → status=sentinel_failed + verdict=未通过"""
    import feishu_sync
    monkeypatch.setattr(sys, "argv", ["feishu_sync.py", "check"])
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: True)
    monkeypatch.setattr(feishu_sync, "get_lark_cli_path", lambda: "lark-cli")
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: "ou_x")
    monkeypatch.setattr(feishu_sync, "check_permissions", lambda: {
        "required": [], "granted": [], "missing": [],
        "app_scopes": {"readable": True, "missing_in_app": []}, "note": None,
    })
    monkeypatch.setattr(feishu_sync, "run_sentinel_write_test", lambda: [
        {"name": "task_create", "ok": True, "error": None},
        {"name": "calendar_delete", "ok": False, "error": "permission denied"},
    ])
    feishu_sync.main()
    out = json.loads(capsys.readouterr().out)
    assert out["permissions"]["status"] == "sentinel_failed"
    assert out["permissions"]["verdict"] == "飞书权限实测未通过"


def test_check_cli_not_available(monkeypatch, capsys):
    """check:CLI 不可用 → permissions skipped(cli_not_available),不跑任何探测"""
    import feishu_sync
    monkeypatch.setattr(sys, "argv", ["feishu_sync.py", "check"])
    monkeypatch.setattr(feishu_sync, "is_feishu_available", lambda force_refresh=False: False)
    monkeypatch.setattr(feishu_sync, "get_lark_cli_path", lambda: None)
    monkeypatch.setattr(feishu_sync, "_get_user_open_id", lambda: None)
    feishu_sync.main()
    out = json.loads(capsys.readouterr().out)
    assert out["available"] is False
    assert out["permissions"]["status"] == "skipped"
    assert out["permissions"]["skipped_reason"] == "cli_not_available"
