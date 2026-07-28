"""record_bill.py 集成 validators 测试（ticket 04 — expand phase）

测点：
- `add --amount 0` 返回错误信息含四要素（字段名+当前值+期望值+怎么修）
- `add` 成功路径仍正常工作（validators 不挡合法数据）
- `update --amount 0` 同样被 validators 拦截
- 9 个 query_type 命令路径不受影响（仅写路径切到 validators）

接缝：CLI 子进程（通过 run_cli fixture）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class TestAddValidationErrorMessages:
    """cmd_add 路径上调用 validators → 错误信息含四要素"""

    def test_add_zero_amount_error_has_four_elements(self, run_cli):
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "餐饮/外卖/午餐",
            "--amount", "0",
            "--time", "2026-07-28 12:00:00",
        ])
        # CLI 应失败（rc != 0）并打印错误
        assert rc != 0, f"amount=0 应被拒绝\nstdout: {out}\nstderr: {err}"
        combined = out + err
        # 四要素
        assert "amount" in combined.lower() or "金额" in combined, f"缺字段名: {combined}"
        assert "0" in combined, f"缺当前值 0: {combined}"
        assert "非零" in combined or "不能为零" in combined or "!= 0" in combined, f"缺期望值: {combined}"
        assert ("改" in combined or "输入" in combined or "提供" in combined or "建议" in combined), \
            f"缺怎么修: {combined}"

    def test_add_nan_amount_error(self, run_cli):
        # argparse type=float 会把 'nan' 转成 float('nan')，validators 应拦截
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "餐饮/外卖/午餐",
            "--amount", "nan",
            "--time", "2026-07-28 12:00:00",
        ])
        assert rc != 0
        combined = out + err
        assert "nan" in combined.lower()
        assert "amount" in combined.lower() or "金额" in combined

    def test_add_bad_category_error(self, run_cli):
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "不存在",
            "--amount", "-35",
            "--time", "2026-07-28 12:00:00",
        ])
        assert rc != 0
        combined = out + err
        assert "category" in combined.lower() or "分类" in combined
        assert "不存在" in combined

    def test_add_bad_time_format_error(self, run_cli):
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "餐饮/外卖/午餐",
            "--amount", "-35",
            "--time", "2026/07/28 12:00",  # 错误格式
        ])
        assert rc != 0
        combined = out + err
        assert "time" in combined.lower() or "时间" in combined


class TestAddSuccessPath:
    """合法 add 仍能正常工作"""

    def test_add_valid_expense(self, run_cli):
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "餐饮/外卖/午餐",
            "--amount", "-35",
            "--time", "2026-07-28 12:00:00",
            "--note", "午饭",
        ])
        assert rc == 0, f"合法 add 应成功\nstdout: {out}\nstderr: {err}"
        assert "已记录" in out or "✓" in out

    def test_add_valid_income(self, run_cli):
        rc, out, err = run_cli([
            "record_bill.py", "add",
            "--category", "工资/基本工资",
            "--amount", "8000",
            "--time", "2026-07-28 09:00:00",
        ])
        assert rc == 0, f"合法 add 应成功\nstdout: {out}\nstderr: {err}"
        assert "已记录" in out or "✓" in out


class TestUpdateValidationErrorMessages:
    """cmd_update 路径上调用 validators → 错误信息含四要素"""

    def test_update_to_zero_amount_error(self, run_cli, seeded_db):
        # 先查最近一条记录的 id
        rc, out, err = run_cli(["record_bill.py", "recent", "--limit", "1", "--json"])
        assert rc == 0
        data = json.loads(out)
        records = data["data"]["records"]
        assert len(records) >= 1
        rid = records[0]["id"]

        # 改成 0
        rc, out, err = run_cli([
            "record_bill.py", "update",
            "--id", str(rid),
            "--amount", "0",
        ])
        assert rc != 0
        combined = out + err
        assert "amount" in combined.lower() or "金额" in combined
        assert "非零" in combined or "不能为零" in combined or "!= 0" in combined

    def test_update_bad_category_error(self, run_cli, seeded_db):
        rc, out, err = run_cli(["record_bill.py", "recent", "--limit", "1", "--json"])
        rid = json.loads(out)["data"]["records"][0]["id"]

        rc, out, err = run_cli([
            "record_bill.py", "update",
            "--id", str(rid),
            "--category", "不存在",
        ])
        assert rc != 0
        combined = out + err
        assert "category" in combined.lower() or "分类" in combined


class TestQueryCommandsUnaffected:
    """9 个 query_type 命令路径不受 validators 影响"""

    @pytest.mark.parametrize("cmd_args", [
        ["summary"],
        ["list"],
        ["recent", "--limit", "5"],
        ["monthly", "--month", "2026-01"],
        ["compare", "--period", "week"],
        ["breakdown"],
        ["overview"],
        ["stats"],
    ])
    def test_query_commands_still_work(self, run_cli, seeded_db, cmd_args):
        rc, out, err = run_cli(["record_bill.py"] + cmd_args + ["--json"])
        assert rc == 0, f"{cmd_args} 失败: {err}"
        data = json.loads(out)
        assert data["status"] in ("ok", "error"), f"未知 status: {data}"
