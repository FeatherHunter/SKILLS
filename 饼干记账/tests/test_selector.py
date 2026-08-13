"""tests/test_selector.py — smartSelect 三字段 selector 块测试（wayfinder #312 T6）

覆盖（契约 公共组件 §6.9 + .scratch/selector-proto/contract.md §4）:
- 数据源: 账户=goals.json accounts 键（T6 依赖注记补建）· 分类=历史+L1 去重 · 账本=ledgers 键
- 来源语义: AI 未传值不预置 / --<field>-source 显式 / 缺省 值在候选内=existing 否则=recommended_new
  / 分类 hint 兜底（已有=inferred 全新=recommended_new）/ 历史预填走 input.value（selector 无 AI 键）
- CLI 端到端: render_write.py photo --account-source inferred（#298 场景）/ link form 子进程

隔离: SKILLS_DB_PATH → tmp_path, 生产 goals.json 与生产账本只读。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _env(tmp_db_dir):
    return {
        **os.environ.copy(),
        "SKILLS_DB_PATH": str(tmp_db_dir),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _write_goals(tmp_db_dir, data: dict):
    (tmp_db_dir / "goals.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _insert(tmp_db_dir, category, amount, time_str, note="", account="", ledger="生活"):
    """直接向临时库插记录(供历史分类/预填测试)"""
    from db import init_db, TABLE_NAME
    conn = init_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (category, time_str, amount, account, ledger, "人民币", note, None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _run_renderer(tmp_db_dir, script, args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)] + args,
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )


def _payload_from_html(html: str) -> dict:
    m = re.search(r'id="payload"[^>]*>(.*?)</script>', html, re.DOTALL)
    assert m, "HTML 缺 payload 脚本块"
    return json.loads(m.group(1).strip())


GOALS_WITH_ACCOUNTS = {
    "accounts": [
        {"name": "美团", "disabled": False},
        {"name": "微信", "disabled": False},
        {"name": "支付宝", "disabled": True},
    ],
    "ledgers": [
        {"name": "生活", "disabled": False},
        {"name": "旅行", "disabled": False},
    ],
}


# ── 数据源: 账户 / 分类 / 账本 options ──────────────────────────────────────────

class TestOptions:
    def test_account_options_from_goals(self, tmp_db_dir):
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import account_options
        assert account_options() == [
            {"name": "美团", "disabled": False},
            {"name": "微信", "disabled": False},
            {"name": "支付宝", "disabled": True},
        ]

    def test_account_options_empty_when_key_missing(self, tmp_db_dir):
        from _selector import account_options
        assert account_options() == []

    def test_account_options_ignores_malformed(self, tmp_db_dir):
        (tmp_db_dir / "goals.json").write_text("{not json", encoding="utf-8")
        from _selector import account_options
        assert account_options() == []

    def test_account_options_ignores_non_list_key(self, tmp_db_dir):
        _write_goals(tmp_db_dir, {"accounts": {"美团": 1}})
        from _selector import account_options
        assert account_options() == []

    def test_ledger_options_from_goals(self, tmp_db_dir):
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import ledger_options
        assert ledger_options() == [
            {"name": "生活", "disabled": False},
            {"name": "旅行", "disabled": False},
        ]

    def test_category_options_history_plus_l1_dedup(self, tmp_db_dir):
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35, "2026-08-01 12:00")
        _insert(tmp_db_dir, "餐饮/外卖/晚餐", -28, "2026-08-02 19:00")
        _insert(tmp_db_dir, "自定义/小众", -9.9, "2026-08-03 10:00")
        from _selector import category_options
        opts = category_options(_load_records(tmp_db_dir))
        names = [o["name"] for o in opts]
        # 历史分类在 L1 之前, 去重保序（fetch_all 时间倒序 → 新记录在前）
        assert names[:3] == ["自定义/小众", "餐饮/外卖/晚餐", "餐饮/外卖/午餐"]
        assert "餐饮" in names and "餐饮/外卖/午餐" in names
        assert len(names) == len(set(names))
        assert all(o == {"name": o["name"]} for o in opts)


def _load_records(tmp_db_dir):
    """临时库 → 最近记录(与渲染器同源)"""
    from db import fetch_all
    return fetch_all(limit=200)


# ── 来源语义: build_selector 单测 ──────────────────────────────────────────────

class TestBuildSelector:
    def test_no_ai_values_options_only(self, tmp_db_dir):
        """AI 未传值 → 三字段块只含 options（不预置 · #306 不得编造）"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"amount": "35"}, [])
        assert list(sel.keys()) == ["account", "category", "ledger"]
        assert sel["account"] == {"options": GOALS_WITH_ACCOUNTS["accounts"]}
        assert "inferred" not in sel["account"] and "initial" not in sel["account"]
        assert "inferred" not in sel["category"] and "initial" not in sel["category"]
        assert sel["ledger"] == {"options": GOALS_WITH_ACCOUNTS["ledgers"]}

    def test_default_source_existing_when_in_options(self, tmp_db_dir):
        """AI 传值无来源 → 值在候选内 = initial{existing}"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"account": "微信"}, [])
        assert sel["account"]["initial"] == {"name": "微信", "source": "existing"}
        assert "inferred" not in sel["account"]

    def test_default_source_recommended_new_when_not_in_options(self, tmp_db_dir):
        """AI 传值无来源 → 值不在候选内 = recommended_new"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"account": "美团月付卡"}, [])
        assert sel["account"]["recommended_new"] == "美团月付卡"
        assert "initial" not in sel["account"]

    def test_explicit_source_inferred(self, tmp_db_dir):
        """--account-source inferred → block.inferred（#298 场景 · 标「AI 推断」）"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"account": "美团"}, [], sources={"account": "inferred"})
        assert sel["account"]["inferred"] == "美团"
        assert "initial" not in sel["account"]

    def test_explicit_source_recommended_new(self, tmp_db_dir):
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"ledger": "家庭"}, [], sources={"ledger": "recommended_new"})
        assert sel["ledger"]["recommended_new"] == "家庭"

    def test_explicit_source_history_and_custom(self, tmp_db_dir):
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        from _selector import build_selector
        sel = build_selector({"account": "招行"}, [], sources={"account": "history"})
        assert sel["account"]["initial"] == {"name": "招行", "source": "history"}
        sel2 = build_selector({"account": "新账户"}, [], sources={"account": "custom"})
        assert sel2["account"]["initial"] == {"name": "新账户", "source": "custom"}

    def test_category_hint_fallback_existing(self, tmp_db_dir):
        """AI 只给分类 hint 且命中已有 → inferred"""
        from _selector import build_selector
        sel = build_selector({"amount": "35"}, [],
                             category_suggestions=[{"name": "餐饮", "kind": "existing"}])
        assert sel["category"]["inferred"] == "餐饮"

    def test_category_hint_fallback_new(self, tmp_db_dir):
        """AI 只给分类 hint 且全新 → recommended_new"""
        from _selector import build_selector
        sel = build_selector({"amount": "35"}, [],
                             category_suggestions=[{"name": "试验分类", "kind": "new"}])
        assert sel["category"]["recommended_new"] == "试验分类"

    def test_ai_category_wins_over_suggestion(self, tmp_db_dir):
        """AI 已给 --category → 分类建议兜底不生效"""
        from _selector import build_selector
        sel = build_selector({"category": "餐饮"}, [],
                             category_suggestions=[{"name": "餐饮", "kind": "existing"}])
        assert sel["category"]["initial"] == {"name": "餐饮", "source": "existing"}
        assert "inferred" not in sel["category"]  # 兜底被 AI 显式值压过

    def test_history_prefill_not_in_selector(self, tmp_db_dir):
        """历史预填（_prefill 补的 account/ledger）不进 selector —— 走 input.value 通道（组件推导 history）"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35, "2026-08-01 12:00", account="微信", ledger="旅行")
        import render_write as rw
        payload = rw.build_payload("expense", {"amount": "35", "category": "餐饮/外卖/午餐"},
                                   "", "", _load_records(tmp_db_dir))
        form = payload["data"]["form"]
        # 历史预填生效在 fields（→ 模板 input.value）
        assert form["fields"]["account"] == "微信"
        assert form["fields"]["ledger"] == "旅行"
        # selector 无 AI 键（组件由 input.value 推导 source=history）
        assert "initial" not in form["selector"]["account"]
        assert "inferred" not in form["selector"]["account"]
        assert "initial" not in form["selector"]["ledger"]


# ── CLI 端到端（子进程 · 闭环 T6 消费端契约）────────────────────────────────────

class TestCliE2E:
    def test_photo_account_inferred_meituan(self, tmp_db_dir):
        """#298 场景: 拍账单识别美团 → --account 美团 --account-source inferred → selector.account.inferred"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        out = tmp_db_dir / "photo.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["photo", "--amount", "38.9", "--category-hint", "外卖",
                                "--account", "美团", "--account-source", "inferred",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        payload = _payload_from_html(out.read_text(encoding="utf-8-sig"))
        sel = payload["data"]["form"]["selector"]
        assert sel["account"]["inferred"] == "美团"
        assert "支付宝" in [o["name"] for o in sel["account"]["options"]]
        # 分类 hint「外卖」→ 全新 → recommended_new
        assert sel["category"]["recommended_new"] == "外卖"
        assert sel["ledger"]["options"] == GOALS_WITH_ACCOUNTS["ledgers"]

    def test_expense_account_new_recommended(self, tmp_db_dir):
        """记支出: --account 美团月付（不在候选）→ recommended_new"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        out = tmp_db_dir / "expense.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--category", "餐饮",
                                "--account", "美团月付", "--out", str(out)])
        assert result.returncode == 0, result.stderr
        payload = _payload_from_html(out.read_text(encoding="utf-8-sig"))
        sel = payload["data"]["form"]["selector"]
        assert sel["account"]["recommended_new"] == "美团月付"
        assert sel["category"]["initial"] == {"name": "餐饮", "source": "existing"}

    def test_expense_category_hint_existing_inferred(self, tmp_db_dir):
        """记支出: --category-hint 餐饮（命中 L1）→ inferred"""
        out = tmp_db_dir / "expense2.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--category-hint", "餐饮",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        payload = _payload_from_html(out.read_text(encoding="utf-8-sig"))
        sel = payload["data"]["form"]["selector"]
        assert sel["category"]["inferred"] == "餐饮"

    def test_link_form_selector_with_sources(self, tmp_db_dir):
        """联动采集表单: 三字段 selector 齐 + 来源生效"""
        _write_goals(tmp_db_dir, GOALS_WITH_ACCOUNTS)
        out = tmp_db_dir / "purchase.html"
        result = _run_renderer(tmp_db_dir, "link/cli.py",
                               ["form", "purchase", "--amount", "199", "--item", "空气炸锅",
                                "--account", "美团", "--account-source", "inferred",
                                "--category", "居家", "--ledger", "生活",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        payload = _payload_from_html(out.read_text(encoding="utf-8-sig"))
        sel = payload["data"]["form"]["selector"]
        assert sel["account"]["inferred"] == "美团"
        assert sel["category"]["initial"] == {"name": "居家", "source": "existing"}
        assert sel["ledger"]["initial"] == {"name": "生活", "source": "existing"}

    def test_cli_bad_source_rejected(self, tmp_db_dir):
        """非法 --*-source 值 → argparse 拒绝（非零退出）"""
        out = tmp_db_dir / "x.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--account-source", "guessed",
                                "--out", str(out)])
        assert result.returncode != 0

    def test_cli_history_prefill_fills_account_ledger(self, tmp_db_dir):
        """CLI 路径历史预填修复（#312）: fields 恒含空串键时预填仍生效（原 setdefault 永不生效 bug）"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35, "2026-08-01 12:00", account="微信", ledger="旅行")
        out = tmp_db_dir / "expense_prefill.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--category", "餐饮/外卖/午餐",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        payload = _payload_from_html(out.read_text(encoding="utf-8-sig"))
        f = payload["data"]["form"]
        assert f["fields"]["account"] == "微信"
        assert f["fields"]["ledger"] == "旅行"
        assert f["prefill_source"] and "预填" in f["prefill_source"]
        # 历史预填不进 selector(AI 键), 走 input.value 通道
        assert "initial" not in f["selector"]["account"]
        assert "inferred" not in f["selector"]["account"]
