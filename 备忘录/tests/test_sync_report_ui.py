"""T09 · sync_report.html UI 一致性 钉死。

- 状态卡左侧 6px accent bar(OK=绿 / warn=橙 / err=红 / idle=灰)
- 状态卡渐变色强化(OK 偏绿 / err 偏粉)
- KPI 顶条 4px(原 3px)
- DOM 顺序:状态卡 → KPI → 明细(消除 KPI→详情→KPI 跳动)
- command 字段中文化
"""
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / "templates" / "sync_report.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


class TestSyncReportAccentBar:
    """#299 VLM 视觉审查:状态卡左侧 6px 竖条已移除(割裂感),保留渐变色区分状态。"""

    def test_status_card_no_accent_bar(self):
        """设计变更:不再有 .status-card::before 竖条(视觉审查拍板)"""
        assert ".status-card::before" not in TEMPLATE_TEXT, (
            "竖条装饰应已移除(视觉审查:与圆角卡片风格割裂)"
        )

    def test_status_card_gradient_states_kept(self):
        """状态渐变色保留:ok 偏绿 / err 偏粉"""
        assert ".status-card.ok" in TEMPLATE_TEXT, "OK 状态卡渐变应保留"
        assert ".status-card.err" in TEMPLATE_TEXT, "err 状态卡渐变应保留"
        assert ".status-card.warn" in TEMPLATE_TEXT, "warn 状态卡渐变应保留"


class TestSyncReportKpiBar:
    def test_kpi_bar_height_4px(self):
        """KPI 顶条 .kpi-bar 高度应是 4px(原 3px 太轻)"""
        import re
        m = re.search(r"\.kpi-bar\s*\{[^}]*\}", TEMPLATE_TEXT)
        assert m, ".kpi-bar CSS 块必须存在"
        css = m.group(0)
        h = re.search(r"height:\s*([^;}\s]+)", css)
        assert h and h.group(1) == "4px", (
            f".kpi-bar height 必须是 4px(原 3px 太轻) · 实际:{h.group(1) if h else 'NONE'}"
        )


class TestSyncReportDOMOrder:
    def test_status_then_kpi_then_details(self):
        """DOM 顺序应是 statusCard → kpis → details(消除跳动)"""
        idx_status = TEMPLATE_TEXT.find('id="statusCard"')
        idx_kpis = TEMPLATE_TEXT.find('id="kpis"')
        idx_details = TEMPLATE_TEXT.find('id="details"')
        assert idx_status > 0 and idx_kpis > 0 and idx_details > 0, (
            "三个 section 节点都必须在场"
        )
        assert idx_status < idx_kpis < idx_details, (
            f"DOM 顺序应是 statusCard < kpis < details · "
            f"实际 {idx_status}, {idx_kpis}, {idx_details}"
        )


class TestSyncReportCommandLocalization:
    def test_command_chinese_alias_table_exists(self):
        """JS 端应有 CMD_CN / command 中文 alias 映射"""
        # 至少应出现 CMD_CN 字面或类似的 command_to_cn 映射常量
        assert ("CMD_CN" in TEMPLATE_TEXT
                or "command_cn" in TEMPLATE_TEXT
                or "commandAlias" in TEMPLATE_TEXT
                or "sync-from-feishu" in TEMPLATE_TEXT and "同步飞书" in TEMPLATE_TEXT), (
            "应提供 command 中文化映射表 · 当前 sync-from-feishu 显示是英文"
        )
