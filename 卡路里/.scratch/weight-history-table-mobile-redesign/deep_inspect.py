"""深度分析表格列数变化 + 实际 mobile 视觉"""
import asyncio
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={'width': 375, 'height': 667},
        device_scale_factor=2, is_mobile=True, has_touch=True
    )
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    # 深度测量
    info = page.evaluate("""() => {
  const out = {};
  const rows = document.querySelectorAll('#tableSection tbody tr');
  out.rowCount = rows.length;
  out.rowStructure = [];
  rows.forEach((tr, i) => {
    const cells = Array.from(tr.querySelectorAll('td'));
    out.rowStructure.push({
      rowIdx: i,
      cellCount: cells.length,
      widths: cells.map(td => td.getBoundingClientRect().width),
      lastCellText: cells[cells.length-1] ? cells[cells.length-1].textContent.trim() : ''
    });
  });
  // SVG 高
  const svg = document.querySelector('svg');
  if (svg) out.svgHeight = svg.getBoundingClientRect().height;
  // table-wrap 横向滚动
  const tw = document.querySelector('.table-wrap');
  if (tw) {
    out.twOverflow = { sw: tw.scrollWidth, cw: tw.clientWidth, hasScroll: tw.scrollWidth > tw.clientWidth };
  }
  // 视觉高分辨率截图
  return out;
}""")
    import json
    print(json.dumps(info, ensure_ascii=False, indent=2))

    # 截 2 张图(全图 + 表格特写)
    page.screenshot(path='.scratch/weight-history-table-mobile-redesign/full-375.png', full_page=True)
    table_el = page.query_selector('#tableSection')
    if table_el:
        table_el.screenshot(path='.scratch/weight-history-table-mobile-redesign/table-375.png')

    browser.close()