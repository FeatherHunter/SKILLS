"""render_write.py 采集表单渲染测试(#201 第二块)

覆盖:expense/income 表单生成 / 智能预填 / 重复检测 / 分类建议(existing/new)/
     历史分类提取 / 模板注入(BOM+payload)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_write as rw  # noqa: E402


def _rec(category, amount, time_str, note="", account="", ledger="生活"):
    return {"category": category, "amount": amount, "time": time_str, "note": note,
            "account": account, "ledger": ledger, "currency": "人民币"}


RECORDS = [
    _rec("餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭", "支付宝"),
    _rec("餐饮/咖啡奶茶/奶茶", -18.0, "2026-08-02 15:00:00", "奶茶"),
    _rec("居家/房租水电", -2500.0, "2026-08-01 10:00:00", "房租", "招行"),
]


class TestPreFill:
    def test_prefill_by_category(self):
        fields = {"amount": "-35.0", "category": "餐饮/外卖/午餐"}
        filled, src = rw._prefill(RECORDS, fields, "", "")
        assert filled["account"] == "支付宝"
        assert src and "餐饮/外卖/午餐" in src

    def test_prefill_by_note_keyword(self):
        fields = {"amount": "-2500.0", "category": ""}
        filled, src = rw._prefill(RECORDS, fields, "", "房租")
        assert filled["ledger"] == "生活"
        assert src

    def test_no_history_no_prefill(self):
        fields = {"amount": "100", "category": ""}
        filled, src = rw._prefill([], fields, "新东西", "")
        assert src is None
        assert filled == fields


class TestDupCheck:
    def test_dup_detected(self):
        """同分类+同金额 → 提示(纯计算)"""
        recs = RECORDS + [_rec("餐饮/外卖/午餐", -35.0, "2026-08-05 12:00:00", "午饭")]
        hint = rw._dup_check(recs, "餐饮/外卖/午餐", -35.0)
        assert hint and "很像" in hint

    def test_no_dup(self):
        hint = rw._dup_check([], "餐饮", -35.0)
        assert hint is None


class TestCategorySuggestions:
    def test_existing_hit_history(self):
        """hint 命中历史分类(确定性包含匹配;语义判断属 AI 职责)"""
        suggs = rw._category_suggestions(RECORDS, "午餐", "expense")
        assert suggs and suggs[0]["kind"] == "existing"
        assert "餐饮" in suggs[0]["name"]

    def test_existing_l1(self):
        suggs = rw._category_suggestions(RECORDS, "餐饮", "expense")
        assert suggs[0]["kind"] == "existing"

    def test_new_category(self):
        suggs = rw._category_suggestions(RECORDS, "健身卡", "expense")
        assert suggs[0]["kind"] == "new"
        assert suggs[0]["name"] == "健身卡"


class TestPayload:
    def test_build_payload_expense(self):
        p = rw.build_payload("expense", {"amount": "35", "category": "餐饮/外卖/午餐"}, "午餐", "午饭", RECORDS)
        assert p["status"] == "ok"
        d = p["data"]
        assert d["meta"]["wake_word"] == "记支出"
        assert d["form"]["type"] == "expense"
        assert "餐饮/外卖/午餐" in d["form"]["categories_history"]
        assert d["form"]["prefill_source"]  # 命中午饭记录
        assert d["form"]["duplicate_hint"]  # 35 元午饭重复

    def test_build_payload_income(self):
        p = rw.build_payload("income", {"amount": "8000", "category": "工资/基本工资"}, "工资", "", RECORDS)
        d = p["data"]
        assert d["meta"]["wake_word"] == "记收入"
        assert d["form"]["category_suggestions"][0]["kind"] == "existing"

    def test_render_to_html(self, tmp_path):
        p = rw.build_payload("expense", {"amount": "35", "category": "餐饮/外卖/午餐"}, "午餐", "午饭", RECORDS)
        template = rw.TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "form.html"
        out.write_text(html, encoding="utf-8-sig")
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"copyPromptBtn\"" in text          # 复制确认 prompt
        assert "id=\"fAmount\"" in text                # 金额输入
        assert "category_suggestions" in text          # 分类推荐
        assert "AI 推荐的已有分类" in text             # 已有标记
        assert "copyDataBtn" in text and "copyLogBtn" in text  # 复制数据/日志
        assert "toastClose" in text                    # B1 toast
