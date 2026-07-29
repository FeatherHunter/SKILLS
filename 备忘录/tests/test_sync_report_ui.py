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
    def test_status_card_has_accent_bar(self):
        """状态卡 CSS 必含 ::before accent bar(左缘 6px,且专属状态卡)"""
        import re
        m = re.search(r"\.status-card::before\s*\{[^}]*\}", TEMPLATE_TEXT)
        assert m, ".status-card::before 必须存在(专属状态卡 · 非其他 ::before)"
        css = m.group(0)
        # 必须 width:6px(accent bar 宽度)
        wm = re.search(r"width:\s*([^;}\s]+)", css)
        assert wm and wm.group(1) == "6px", (
            f".status-card::before 必须 width:6px · 实际:{wm.group(1) if wm else 'NONE'}"
        )
        # 必须 left:0(左缘)
        assert "left:0" in css, ".status-card::before 必须 left:0"

    def test_status_card_ok_accent_uses_ok_color(self):
        """.status-card.ok::before{background:var(--ok)} 必须存在"""
        assert ".status-card.ok::before" in TEMPLATE_TEXT, (
            "OK 状态卡 accent bar 必须用 var(--ok) 色相"
        )

    def test_status_card_err_accent_uses_err_color(self):
        """.status-card.err::before{background:var(--err)} 必须存在"""
        assert ".status-card.err::before" in TEMPLATE_TEXT, (
            "err 状态卡 accent bar 必须用 var(--err) 色相"
        )


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
