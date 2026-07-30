"""Generate a complete visual diagnostic report"""
import json
from pathlib import Path

# Combine VLM descriptions + Playwright measurements
report = {
    "screenshots_analyzed": [
        "mobile-table.png",
        "mobile-chart.png",
        "full-375.png",
        "mobile-note-row.png",
        "table-only.png",
    ],
    "playwright_measurements_iPhone_SE_375x667": {
        "SVG_height": "100px (too small — 309px width × 260/800 ratio = 100px)",
        "Note_column_晨起空腹_overflow": "true (padding 6px 4px too tight)",
        "Table_fits_in_309px": True,
        "No_horizontal_scroll_body_or_wrap": True,
        "Table_height_24_rows": "1168.5px (no sticky header)"
    },
    "vlm_findings": {
        "table_5_columns_render": True,
        "color_coding_works": "green for loss, red for gain",
        "note_column_visible_for_2_rows": True,
        "last_row_styling": "reported as 'highlighted in red' by VLM (unclear if real)"
    },
    "user_visible_issues_to_fix": [
        "SVG 100px 太矮 (chart 不清晰)",
        "note 文字 padding 紧",
        "table 1168px 高滚动无 sticky header",
        "5 列 11px 字体在 375px 拥挤"
    ]
}

print(json.dumps(report, ensure_ascii=False, indent=2))