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


_ID_SEQ = [100]


def _rec(category, amount, time_str, note="", account="", ledger="生活", rid=None):
    if rid is None:
        rid = _ID_SEQ[0]
        _ID_SEQ[0] += 1
    return {"id": rid, "category": category, "amount": amount, "time": time_str, "note": note,
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
        assert "category_suggestions" in text          # 分类推荐(payload 数据)
        assert "window.smartSelect" in text            # #312: 三字段走 Base smartSelect 组件
        assert "id=\"fCategory\"" in text and "id=\"fAccount\"" in text and "id=\"fLedger\"" in text
        assert "actionbar-zone" in text and "window.actionBar" in text  # Base actionBar(#300)
        assert "<!--SHARED-HELPERS-->" in text          # Base 管线占位符(渲染时注入 base.js)
        assert '"snapshot"' in text                      # 信封 scene.snapshot(人类可读快照)


class TestPhoto:
    def test_photo_payload(self):
        p = rw.build_payload("photo", {"amount": "35.5", "category": "餐饮/外卖/午餐"}, "午餐", "",
                             RECORDS, photo_meta={"image_count": 1, "note": "AI 识别结果，请核对金额"})
        d = p["data"]
        assert d["meta"]["wake_word"] == "拍账单"
        assert d["form"]["type"] == "photo"
        assert d["form"]["photo_meta"]["image_count"] == 1
        # photo 模式:不显示预填/重复(识别来源标注替代)
        assert d["form"]["prefill_source"] is None
        assert d["form"]["duplicate_hint"] is None

    def test_photo_html_has_identify_banner(self, tmp_path):
        p = rw.build_payload("photo", {"amount": "35.5", "category": "餐饮/外卖/午餐"}, "午餐", "",
                             RECORDS, photo_meta={"image_count": 1, "note": "AI 识别结果，请核对金额"})
        template = rw.TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "photo.html"
        out.write_text(html, encoding="utf-8-sig")
        text = out.read_text(encoding="utf-8-sig")
        assert "拍账单" in text
        # 识别标注在 payload JSON(JS 渲染 prefillBox),静态断言 payload 数据
        assert '"photo_meta"' in text
        assert '"image_count": 1' in text
        # photo 模式模板含识别标注渲染逻辑(JS 分支)
        assert "AI 识别结果，请核对金额" in text


class TestBatch:
    def test_batch_payload_normal(self):
        items = [{"amount": "35", "category": "餐饮/外卖/午餐", "note": "午饭"},
                 {"amount": "25", "category": "餐饮/咖啡奶茶/奶茶", "note": "奶茶"}]
        p = rw.build_batch_payload(items, "生活", RECORDS)
        d = p["data"]
        assert d["meta"]["wake_word"] == "批量录入"
        assert d["form"]["type"] == "batch"
        assert len(d["form"]["items"]) == 2
        assert d["form"]["missing_count"] == 0

    def test_batch_missing_amount_flagged(self):
        items = [{"amount": "", "category": "餐饮", "note": "午饭"},
                 {"amount": "25", "category": "奶茶", "note": ""}]
        p = rw.build_batch_payload(items, "", RECORDS)
        form = p["data"]["form"]
        assert form["missing_count"] == 1
        assert form["items"][0]["missing"] is True
        assert form["items"][1]["missing"] is False

    def test_batch_html_table(self, tmp_path):
        items = [{"amount": "35", "category": "餐饮/外卖/午餐", "note": "午饭"},
                 {"amount": "", "category": "奶茶", "note": "下午茶"}]
        p = rw.build_batch_payload(items, "生活", RECORDS)
        template = rw.BATCH_TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "batch.html"
        out.write_text(html, encoding="utf-8-sig")
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"rows\"" in text            # 表格行容器
        assert "缺金额" in text                 # 缺金额标记
        assert "missingBanner" in text          # 缺金额警示条
        assert "id=\"totalAmt\"" in text        # 总计
        assert "copyPromptBtn" in text and "actionbar-zone" in text and "window.actionBar" in text
        assert "<!--SHARED-HELPERS-->" in text  # Base 管线占位符
        assert '"snapshot"' in text


class TestReimburse:
    def test_reimburse_payload_adds_tag(self):
        p = rw.build_payload("reimburse", {"amount": "120", "category": "餐饮/堂食/晚餐"}, "晚餐", "", RECORDS)
        form = p["data"]["form"]
        assert form["type"] == "reimburse"
        assert "#待报销" in form["fields"]["note"]
        assert p["data"]["meta"]["wake_word"] == "记报销"

    def test_reimburse_html_marks_tag(self, tmp_path):
        p = rw.build_payload("reimburse", {"amount": "120", "category": "餐饮/堂食/晚餐"}, "晚餐", "", RECORDS)
        template = rw.TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "reimburse.html"
        out.write_text(html, encoding="utf-8-sig")
        text = out.read_text(encoding="utf-8-sig")
        assert "记报销" in text
        assert "#待报销" in text  # 自动标记标注


class TestFlow:
    def test_refund_payload_finds_candidates(self):
        p = rw.build_flow_payload("refund", "35", "午饭", "退货", RECORDS)
        form = p["data"]["form"]
        assert form["type"] == "refund"
        assert form["reason"] == "退货"
        assert len(form["candidates"]) >= 1
        assert form["candidates"][0]["note"] == "午饭" or "午饭" in form["candidates"][0]["category"]
        ops = form["operations"]
        assert len(ops) == 2
        assert "退款/冲销" in ops[0]["text"]
        assert "#已退款" in ops[1]["text"]

    def test_refund_no_hint_falls_back_recent(self):
        p = rw.build_flow_payload("refund", "35", "", "", RECORDS)
        assert len(p["data"]["form"]["candidates"]) >= 1

    def test_refund_ai_candidates_priority(self):
        """AI 显式候选优先(对抗审查修复:AI 语义定位 → 脚本组装)"""
        ai_cands = [
            {"id": 999, "time": "2026-08-01 12:00:00", "category": "餐饮/外卖/午餐",
             "amount": -35.0, "note": "午饭(用户确认那笔)"},
        ]
        p = rw.build_flow_payload("refund", "35", "", "退货", RECORDS, explicit_candidates=ai_cands)
        cands = p["data"]["form"]["candidates"]
        assert len(cands) == 1
        assert cands[0]["id"] == 999
        assert "用户确认那笔" in cands[0]["note"]

    def test_ai_candidates_limited_to_five(self):
        ai_cands = [
            {"id": i, "time": f"2026-08-0{i} 12:00:00", "category": "餐饮", "amount": -10.0, "note": ""}
            for i in range(1, 8)
        ]
        p = rw.build_flow_payload("refund", "35", "", "", RECORDS, explicit_candidates=ai_cands)
        assert len(p["data"]["form"]["candidates"]) == 5

    def test_reimburse_done_finds_pending(self):
        recs = RECORDS + [_rec("餐饮/差旅", -100.0, "2026-07-28 10:00:00", "#待报销 出差餐")]
        p = rw.build_flow_payload("reimburse_done", "100", "出差", "", recs)
        form = p["data"]["form"]
        assert form["type"] == "reimburse_done"
        assert len(form["candidates"]) >= 1
        assert "#待报销" in form["candidates"][0]["note"]

    def test_flow_html_structure(self, tmp_path):
        p = rw.build_flow_payload("refund", "35", "午饭", "退货", RECORDS)
        template = rw.FLOW_TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "flow.html"
        out.write_text(html, encoding="utf-8-sig")
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"ops\"" in text          # 两步操作预览
        assert "id=\"cands\"" in text        # 候选 radio
        assert "id=\"warnBox\"" in text      # 超支警示
        assert "copyPromptBtn" in text and "actionbar-zone" in text and "window.actionBar" in text
        assert "<!--SHARED-HELPERS-->" in text  # Base 管线占位符
        assert '"snapshot"' in text


class TestLendBorrow:
    def test_lend_payload_single_op(self):
        p = rw.build_flow_payload("lend", "500", "小明", "月底还", RECORDS)
        form = p["data"]["form"]
        assert form["type"] == "lend"
        assert len(form["candidates"]) == 0  # 单操作无候选
        ops = form["operations"]
        assert len(ops) == 1
        assert "借贷/借出" in ops[0]["text"]
        assert "#借出" in ops[0]["detail"] and "#未还" in ops[0]["detail"]
        assert p["data"]["meta"]["wake_word"] == "记借出"

    def test_borrow_payload(self):
        p = rw.build_flow_payload("borrow", "500", "小明", "", RECORDS)
        form = p["data"]["form"]
        assert form["type"] == "borrow"
        assert "借贷/借入" in form["operations"][0]["text"]
        assert p["data"]["meta"]["wake_word"] == "记借入"


class TestCollectPayback:
    def test_collect_finds_unpaid_lend(self):
        recs = RECORDS + [_rec("借贷/借出", -500.0, "2026-07-01 10:00:00", "#借出 #借给小明 #未还")]
        p = rw.build_flow_payload("collect", "", "小明", "", recs)
        form = p["data"]["form"]
        assert form["type"] == "collect"
        assert len(form["candidates"]) >= 1
        assert "#借出" in form["candidates"][0]["note"]
        ops = form["operations"]
        assert len(ops) == 2
        assert "借贷/收回" in ops[0]["text"]
        assert "#未还 → #已还" in ops[1]["text"]

    def test_payback_finds_unpaid_borrow(self):
        recs = RECORDS + [_rec("借贷/借入", 500.0, "2026-07-02 10:00:00", "#借入 #向小明借 #未还")]
        p = rw.build_flow_payload("payback", "", "小明", "", recs)
        form = p["data"]["form"]
        assert form["type"] == "payback"
        assert len(form["candidates"]) >= 1
        assert "#借入" in form["candidates"][0]["note"]
        assert "借贷/偿还" in form["operations"][0]["text"]

    def test_lend_borrow_html_has_target_field(self, tmp_path):
        """借贷单操作:无候选卡 + 对象/期限字段"""
        p = rw.build_flow_payload("lend", "500", "小明", "月底还", RECORDS)
        template = rw.FLOW_TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "lend.html"
        out.write_text(html, encoding="utf-8-sig")
        text = out.read_text(encoding="utf-8-sig")
        assert "记借出" in text
        assert "fDeadline" in text  # 期限字段(JS 动态,payload 有值)
        assert "月底还" in text


class TestInstallment:
    def test_divisible(self):
        """整除:6000/24 = 250,首期 = 250"""
        items = rw.compute_installments(6000, 24, "2026-08-15")
        assert len(items) == 24
        assert all(it["amount"] == 250.0 for it in items)
        assert items[0]["date"] == "2026-08-15"
        assert items[1]["date"] == "2026-09-15"
        assert sum(it["amount"] for it in items) == 6000.0

    def test_remainder_first_period_pads(self):
        """除不尽:6001/24,首期补差额保证总和 = 6001"""
        items = rw.compute_installments(6001, 24, "2026-08-15")
        assert len(items) == 24
        assert items[0]["amount"] == round(6001 - 250.04 * 23, 2)
        assert abs(sum(it["amount"] for it in items) - 6001.0) < 0.001

    def test_month_end_fallback(self):
        """月末回退:31 号首期 → 2月28(29)/4月30"""
        items = rw.compute_installments(3100, 6, "2026-01-31")
        dates = [it["date"] for it in items]
        assert dates == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-30"]

    def test_cross_year(self):
        items = rw.compute_installments(1200, 3, "2026-12-15")
        assert items[1]["date"] == "2027-01-15"
        assert items[2]["date"] == "2027-02-15"

    def test_build_installment_payload(self):
        p = rw.build_installment_payload("手机", "6000", 24, "2026-08-15", "招行", "生活")
        form = p["data"]["form"]
        assert form["type"] == "installment"
        assert form["name"] == "手机"
        assert len(form["items"]) == 24
        assert p["data"]["meta"]["wake_word"] == "记分期"

    def test_installment_html_structure(self, tmp_path):
        p = rw.build_installment_payload("手机", "6000", 24, "2026-08-15")
        template = rw.INSTALLMENT_TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "inst.html"
        out.write_text(html, encoding="utf-8-sig")
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"params\"" in text      # 参数回显
        assert "id=\"rows\"" in text        # 分摊预览
        assert "copyPromptBtn" in text and "actionbar-zone" in text and "window.actionBar" in text
        assert "<!--SHARED-HELPERS-->" in text  # Base 管线占位符(渲染时注入 base.js)
        assert '"snapshot"' in text


class TestUpdate:
    def _seed(self, tmp_db_dir):
        from db import add_bill
        return add_bill("餐饮/外卖/午餐", -35.0, "2026-08-05 12:00:00", account="支付宝", ledger="生活", note="午饭")["id"]

    def test_update_diff(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        p = rw.build_update_payload(rid, {"amount": -38.0, "note": "午饭+牛奶"})
        form = p["data"]["form"]
        assert form["type"] == "update"
        assert form["original"]["id"] == rid
        fields = {c["field"]: c for c in form["changes"]}
        assert fields["amount"]["old"] == "-35.00" and fields["amount"]["new"] == "-38.00"
        assert fields["note"]["old"] == "午饭" and fields["note"]["new"] == "午饭+牛奶"

    def test_update_no_change_raises(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        import pytest as _pt
        with _pt.raises(ValueError):
            rw.build_update_payload(rid, {"amount": -35.0})  # 原值 = 新值

    def test_update_missing_id_raises(self, tmp_db_dir):
        import pytest as _pt
        with _pt.raises(ValueError):
            rw.build_update_payload(99999, {"note": "x"})

    def test_update_html_structure(self, tmp_db_dir, tmp_path):
        rid = self._seed(tmp_db_dir)
        p = rw.build_update_payload(rid, {"amount": -38.0})
        template = rw.UPDATE_TEMPLATE.read_text(encoding="utf-8")
        html = template.replace("<!--INJECT-DATA-->",
                                json.dumps(p, ensure_ascii=False).replace("</", "<\\/"), 1)
        out = tmp_path / "update.html"
        out.write_text(html, encoding="utf-8-sig")
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"orig\"" in text       # 原记录
        assert "id=\"diff\"" in text       # diff 表
        assert "class=\"old\"" in text and "class=\"new\"" in text  # 原值划线/新值蓝
        assert "copyPromptBtn" in text and "actionbar-zone" in text and "window.actionBar" in text
        assert "<!--SHARED-HELPERS-->" in text  # Base 管线占位符
