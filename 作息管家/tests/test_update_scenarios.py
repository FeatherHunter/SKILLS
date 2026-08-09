"""update_scenarios.py 场景合并器测试(实施 T1)

锁定契约:
- 片段 → 总账合并:scenario_id 命中 = 覆盖更新(原位保序)/ 未命中 = 追加末尾
- 字段契约校验(§07 §2.2):7 字段必填 / status 二态 / scenario_id 片段内唯一
- 幂等:同一输入连跑两次,输出 byte-identical
- 头部契约注释保留 + 「场景总数」行自动更新
- --dry-run 不写盘 / 任一片段校验失败整体不写盘
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import yaml

import update_scenarios

MASTER = [
    {"wake_word": "#0 记作息", "scenario_id": "record_add_single", "scenario_title": "添加单条作息记录",
     "dimensions": {"activity": "任意活动"}, "prompt": "请帮我记一条作息", "status": "", "result": "写入 1 条记录"},
    {"wake_word": "#0 记作息", "scenario_id": "record_add_json", "scenario_title": "通过 JSON 文件批量添加",
     "dimensions": {"input": "JSON 文件路径"}, "prompt": "请帮我批量导入", "status": "", "result": "逐条校验后写入"},
]

FRAG = [
    {"wake_word": "#0 记作息", "scenario_id": "record_add_single", "scenario_title": "添加单条作息记录(强化)",
     "dimensions": {"activity": "任意活动", "duration_minutes": "1-1440"},
     "prompt": "请帮我记一条作息:今天 14:00 写了代码", "status": "", "result": "写入 1 条,生成回执 HTML"},
    {"wake_word": "批量导入", "scenario_id": "batch_add_new", "scenario_title": "批量导入作息",
     "dimensions": {"input": "JSON 文件路径"}, "prompt": "批量导入这批记录", "status": "【待开发】",
     "result": "逐条校验后写入,生成多条回执"},
]


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ===== 合并语义 =====

def test_merge_append_and_replace(tmp_path):
    master_path = tmp_path / "scenarios.yaml"
    frag_path = tmp_path / "scenes" / "record.yaml"
    _write_yaml(master_path, MASTER)
    _write_yaml(frag_path, FRAG)

    rc = update_scenarios.main(["--scenes-dir", str(frag_path.parent),
                                "--scenarios", str(master_path)])
    assert rc == 0

    merged = yaml.safe_load(master_path.read_text(encoding="utf-8"))
    assert len(merged) == 3  # 2 原有 + 1 新增
    by_id = {s["scenario_id"]: s for s in merged}
    # 命中 → 覆盖更新(字段取自片段)
    assert by_id["record_add_single"]["scenario_title"] == "添加单条作息记录(强化)"
    assert by_id["record_add_single"]["dimensions"] == {"activity": "任意活动", "duration_minutes": "1-1440"}
    # 未命中 → 追加末尾
    assert merged[-1]["scenario_id"] == "batch_add_new"
    assert merged[-1]["status"] == "【待开发】"
    # 原有未被波及的条目原样保留
    assert by_id["record_add_json"]["prompt"] == "请帮我批量导入"


def test_merge_idempotent(tmp_path):
    """连跑两次 → 第二次无新增无更新,文件 byte-identical"""
    master_path = tmp_path / "scenarios.yaml"
    frag_path = tmp_path / "scenes" / "record.yaml"
    _write_yaml(master_path, MASTER)
    _write_yaml(frag_path, FRAG)

    assert update_scenarios.main(["--scenes-dir", str(frag_path.parent),
                                  "--scenarios", str(master_path)]) == 0
    first = master_path.read_bytes()
    assert update_scenarios.main(["--scenes-dir", str(frag_path.parent),
                                  "--scenarios", str(master_path)]) == 0
    assert master_path.read_bytes() == first  # 幂等:输出不变


def test_merge_no_fragments_returns_error(tmp_path):
    rc = update_scenarios.main(["--scenes-dir", str(tmp_path / "none"),
                                "--scenarios", str(tmp_path / "x.yaml")])
    assert rc == 1


# ===== 字段契约校验 =====

def test_validate_requires_fields():
    bad = [dict(MASTER[0])]
    del bad[0]["result"]
    errors = update_scenarios.validate_fragment(bad, "bad.yaml")
    assert errors and "缺字段" in errors[0]


def test_validate_status_only_two_states():
    bad = [dict(MASTER[0])]
    bad[0]["status"] = "WIP"
    errors = update_scenarios.validate_fragment(bad, "bad.yaml")
    assert errors and "status 非法" in errors[0]


def test_validate_duplicate_id_in_fragment():
    errors = update_scenarios.validate_fragment([MASTER[0], MASTER[0]], "dup.yaml")
    assert errors and "重复" in errors[0]


def test_main_aborts_on_invalid_fragment(tmp_path):
    """任一片段非法 → 整体不写盘"""
    master_path = tmp_path / "scenarios.yaml"
    frag_path = tmp_path / "scenes"
    _write_yaml(master_path, MASTER)
    _write_yaml(frag_path / "record.yaml", FRAG)
    bad = [dict(MASTER[1])]
    del bad[0]["prompt"]
    _write_yaml(frag_path / "bad.yaml", bad)

    assert update_scenarios.main(["--scenes-dir", str(frag_path),
                                  "--scenarios", str(master_path)]) == 1
    # 总账未被改动
    assert yaml.safe_load(master_path.read_text(encoding="utf-8")) == MASTER


# ===== 写回格式 =====

def test_dump_preserves_header_and_updates_count(tmp_path):
    out = tmp_path / "scenarios.yaml"
    update_scenarios.dump_scenarios([MASTER[0]] * 2 + [FRAG[1]], out)
    text = out.read_text(encoding="utf-8")
    assert "# 作息管家 · 场景资产(§07 契约)" in text
    assert "# 字段契约(§07 §2.2)" in text
    assert "# 场景总数: 3" in text
    # 写回后仍可被 safe_load 正常解析(help_render 契约)
    assert len(yaml.safe_load(text)) == 3


def test_main_dry_run_does_not_write(tmp_path):
    master_path = tmp_path / "scenarios.yaml"
    frag_path = tmp_path / "scenes"
    _write_yaml(master_path, MASTER)
    _write_yaml(frag_path / "record.yaml", FRAG)
    before = master_path.read_bytes()
    assert update_scenarios.main(["--scenes-dir", str(frag_path),
                                  "--scenarios", str(master_path), "--dry-run"]) == 0
    assert master_path.read_bytes() == before
