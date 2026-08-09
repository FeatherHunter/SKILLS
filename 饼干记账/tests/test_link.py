"""scripts/link/cli.py 联动域测试(#239 · 2 场景:买东西联动 / 吃饭联动)

覆盖:采集表单 payload(meta/预填/重复/分类建议/默认分类)/ 回执 payload(账单数据/联动 prompt/撤销)/
     模板注入(BOM + 标准按钮)/ CLI 子进程(form/receipt 两端到端 + 错误态)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import link.cli as lk  # noqa: E402

TEMPLATE_DIR = SCRIPTS_DIR.parent / "templates" / "联动"

RECORDS = [
    {"id": 1, "category": "居家/家电", "amount": -199.0, "time": "2026-08-05 10:00:00", "note": "空气炸锅",
     "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"id": 2, "category": "餐饮/外卖/午餐", "amount": -35.0, "time": "2026-08-06 12:00:00", "note": "鸡腿饭",
     "account": "微信", "ledger": "生活", "currency": "人民币"},
    {"id": 3, "category": "餐饮/咖啡奶茶/奶茶", "amount": -18.0, "time": "2026-08-07 15:00:00", "note": "奶茶",
     "account": "", "ledger": "生活", "currency": "人民币"},
]


def _inject(payload: dict, template_name: str, tmp_path: Path) -> Path:
    """模板注入(与 CLI _render 同构),返回输出文件"""
    template = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    html = template.replace("<!--INJECT-DATA-->",
                            json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"), 1)
    out = tmp_path / template_name
    out.write_text(html, encoding="utf-8-sig")
    return out


class TestFormPayload:
    def test_purchase_form_meta(self):
        p = lk.build_form_payload("purchase", {"amount": "199", "category": ""}, "家电", "", RECORDS)
        d = p["data"]
        assert d["meta"]["scene_id"] == "link_purchase"          # 对齐 scenes/link.yaml
        assert d["meta"]["wake_word"] == "买东西"
        assert d["form"]["type"] == "purchase"
        assert d["form"]["default_category"] == "居家/家电"
        assert d["form"]["key_label"] == "物  品"

    def test_meal_form_meta(self):
        p = lk.build_form_payload("meal", {"amount": "35"}, "", "", RECORDS)
        d = p["data"]
        assert d["meta"]["scene_id"] == "link_meal"
        assert d["meta"]["wake_word"] == "吃饭"
        assert d["form"]["default_category"] == "餐饮"
        assert d["form"]["key_label"] == "吃  了"

    def test_purchase_prefill_by_category(self):
        p = lk.build_form_payload("purchase", {"amount": "199", "category": "居家/家电"}, "", "", RECORDS)
        form = p["data"]["form"]
        assert form["prefill_source"] and "居家/家电" in form["prefill_source"]
        assert form["fields"]["account"] == "支付宝"

    def test_meal_prefill_by_note_keyword(self):
        p = lk.build_form_payload("meal", {"amount": "35", "category": ""}, "", "鸡腿饭", RECORDS)
        form = p["data"]["form"]
        assert form["prefill_source"]
        assert form["fields"]["account"] == "微信"

    def test_dup_check(self):
        p = lk.build_form_payload("purchase", {"amount": "199", "category": "居家/家电"}, "", "", RECORDS)
        assert p["data"]["form"]["duplicate_hint"]

    def test_category_suggestions_existing(self):
        p = lk.build_form_payload("purchase", {"amount": "199"}, "家电", "", RECORDS)
        suggs = p["data"]["form"]["category_suggestions"]
        assert suggs and suggs[0]["kind"] == "existing"

    def test_category_suggestions_new(self):
        p = lk.build_form_payload("purchase", {"amount": "199"}, "跑步机", "", RECORDS)
        suggs = p["data"]["form"]["category_suggestions"]
        assert suggs[0]["kind"] == "new"
        assert suggs[0]["name"] == "跑步机"

    def test_purchase_form_html_structure(self, tmp_path):
        p = lk.build_form_payload("purchase", {"amount": "199", "category": "居家/家电"}, "家电", "", RECORDS)
        out = _inject(p, "purchase_confirm.html", tmp_path)
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"copyPromptBtn\"" in text          # 确认 prompt
        assert "id=\"fAmount\"" in text                # 金额
        assert "id=\"fKey\"" in text                   # 联动关键字段(物品)
        assert "link-note" in text                     # 联动预告条
        assert "同时录入居家管家" in text               # 预告目标技能
        assert "copyDataBtn" in text and "copyLogBtn" in text  # 复制数据/日志
        assert "toastClose" in text                    # B1 toast

    def test_meal_form_html_structure(self, tmp_path):
        p = lk.build_form_payload("meal", {"amount": "35", "category": "餐饮/外卖/午餐"}, "午餐", "", RECORDS)
        out = _inject(p, "meal_confirm.html", tmp_path)
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"fKey\"" in text
        assert "同时记卡路里" in text
        assert "copyPromptBtn" in text and "copyDataBtn" in text and "copyLogBtn" in text


class TestReceiptPayload:
    def _seed(self, tmp_db_dir, category="居家/家电", amount=-199.0, note="空气炸锅"):
        from db import add_bill
        r = add_bill(category, amount, "2026-08-09 12:00:00", account="支付宝", ledger="生活", note=note)
        return r["id"]

    def test_purchase_receipt_data(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        p = lk.build_receipt_payload("purchase", rid, "空气炸锅")
        d = p["data"]
        assert d["meta"]["scene_id"] == "link_purchase"
        rc = d["receipt"]
        assert rc["bill"]["id"] == rid
        assert rc["bill"]["amount"] == "199.00"
        assert rc["bill"]["amount_sign"] == "-199.00"
        assert rc["bill"]["category"] == "居家/家电"
        assert rc["key"]["item"] == "空气炸锅"

    def test_purchase_link_prompt(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        link = lk.build_receipt_payload("purchase", rid, "空气炸锅")["data"]["receipt"]["link"]
        assert link["target"] == "居家管家"
        assert link["wake_word"] == "录物品"
        assert link["button"] == "同时录入居家管家"
        assert "请加载「居家管家」技能" in link["prompt"]
        assert "空气炸锅" in link["prompt"]
        assert "199.00 元" in link["prompt"]
        assert "居家/家电" in link["prompt"]
        assert link["fields"][0] == {"label": "物  品", "value": "空气炸锅"}

    def test_meal_link_prompt(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir, category="餐饮/外卖/午餐", amount=-35.0, note="午饭 鸡腿饭")
        rc = lk.build_receipt_payload("meal", rid, "鸡腿饭")["data"]["receipt"]
        link = rc["link"]
        assert link["target"] == "卡路里"
        assert link["wake_word"] == "记一餐"
        assert link["button"] == "同时记卡路里"
        assert "请加载「卡路里」技能" in link["prompt"]
        assert "鸡腿饭" in link["prompt"]
        assert "午饭 鸡腿饭" in link["prompt"]          # 备注从 bill 携带
        assert rc["key"]["ate"] == "鸡腿饭"

    def test_receipt_undo_prompt(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        undo = lk.build_receipt_payload("purchase", rid, "空气炸锅")["data"]["receipt"]["undo"]["prompt"]
        assert "撤销" in undo and str(rid) in undo

    def test_receipt_missing_bill_raises(self, tmp_db_dir):
        with pytest.raises(ValueError):
            lk.build_receipt_payload("purchase", 99999, "空气炸锅")

    def test_receipt_missing_key_raises(self, tmp_db_dir):
        rid = self._seed(tmp_db_dir)
        with pytest.raises(ValueError):
            lk.build_receipt_payload("purchase", rid, "")

    def test_receipt_html_structure(self, tmp_db_dir, tmp_path):
        rid = self._seed(tmp_db_dir)
        p = lk.build_receipt_payload("purchase", rid, "空气炸锅")
        out = _inject(p, "receipt.html", tmp_path)
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "id=\"billRows\"" in text        # 已记录账单
        assert "id=\"linkBtn\"" in text         # 联动按钮
        assert "id=\"linkFields\"" in text      # 联动字段预览
        assert "id=\"undoBtn\"" in text         # 撤销
        assert "copyDataBtn" in text and "copyLogBtn" in text
        assert "toastClose" in text
        # payload 内嵌联动 prompt(JS 读取)
        assert "同时录入居家管家" in text

    def test_meal_receipt_html(self, tmp_db_dir, tmp_path):
        rid = self._seed(tmp_db_dir, category="餐饮/外卖/午餐", amount=-35.0, note="鸡腿饭")
        p = lk.build_receipt_payload("meal", rid, "鸡腿饭")
        out = _inject(p, "receipt.html", tmp_path)
        text = out.read_text(encoding="utf-8-sig")
        assert "同时记卡路里" in text
        assert "卡路里" in text


class TestCli:
    def test_form_purchase_cli(self, run_cli, tmp_path):
        rc, out, err = run_cli(["link/cli.py", "form", "purchase", "--amount", "199", "--item", "空气炸锅",
                                "--out", str(tmp_path / "p.html")])
        assert rc == 0, err
        assert "联动采集表单" in out
        assert (tmp_path / "p.html").exists()

    def test_form_meal_cli(self, run_cli, tmp_path):
        rc, out, err = run_cli(["link/cli.py", "form", "meal", "--amount", "35", "--ate", "鸡腿饭",
                                "--out", str(tmp_path / "m.html")])
        assert rc == 0, err
        assert (tmp_path / "m.html").exists()

    def test_receipt_purchase_cli(self, run_cli, tmp_db_dir, tmp_path):
        from db import add_bill
        rid = add_bill("居家/家电", -199.0, "2026-08-09 12:00:00", account="支付宝", note="空气炸锅")["id"]
        rc, out, err = run_cli(["link/cli.py", "receipt", "purchase", "--id", str(rid), "--item", "空气炸锅",
                                "--out", str(tmp_path / "r.html")])
        assert rc == 0, err
        text = (tmp_path / "r.html").read_text(encoding="utf-8-sig")
        assert "同时录入居家管家" in text

    def test_receipt_meal_cli(self, run_cli, tmp_db_dir, tmp_path):
        from db import add_bill
        rid = add_bill("餐饮/外卖/午餐", -35.0, "2026-08-09 12:00:00", note="鸡腿饭")["id"]
        rc, out, err = run_cli(["link/cli.py", "receipt", "meal", "--id", str(rid), "--ate", "鸡腿饭",
                                "--out", str(tmp_path / "r2.html")])
        assert rc == 0, err
        text = (tmp_path / "r2.html").read_text(encoding="utf-8-sig")
        assert "同时记卡路里" in text

    def test_receipt_missing_id_fails(self, run_cli):
        rc, out, err = run_cli(["link/cli.py", "receipt", "purchase", "--item", "空气炸锅"])
        assert rc != 0
        assert "usage" in err.lower() or "required" in err.lower()

    def test_receipt_missing_key_fails(self, run_cli, tmp_db_dir):
        from db import add_bill
        rid = add_bill("居家/家电", -199.0, "2026-08-09 12:00:00")["id"]
        rc, out, err = run_cli(["link/cli.py", "receipt", "purchase", "--id", str(rid)])
        assert rc != 0
        assert "联动关键字段" in err

    def test_receipt_unknown_bill_fails(self, run_cli):
        rc, out, err = run_cli(["link/cli.py", "receipt", "purchase", "--id", "99999", "--item", "x"])
        assert rc != 0
        assert "不存在" in err
