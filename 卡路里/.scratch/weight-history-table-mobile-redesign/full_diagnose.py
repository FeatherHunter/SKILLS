"""完整诊断 mobile 视觉问题"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    # 全屏快照 + 多个区域快照
    page.screenshot(path='.scratch/weight-history-table-mobile-redesign/mobile-full.png', full_page=True)

    # KPI 卡片
    kpis = page.locator('.kpi-grid')
    if kpis.count() > 0:
        kpis.screenshot(path='.scratch/weight-history-table-mobile-redesign/mobile-kpis.png')

    # Chart
    page.locator('#chartSection').screenshot(path='.scratch/weight-history-table-mobile-redesign/mobile-chart.png')

    # Table
    page.locator('#tableSection').screenshot(path='.scratch/weight-history-table-mobile-redesign/mobile-table.png')

    # 单个 note 行(看怎么显示)
    note_rows = page.locator('#tableSection tbody tr:has(td:last-child:text("晨起空腹"))')
    if note_rows.count() > 0:
        note_rows.first.screenshot(path='.scratch/weight-history-table-mobile-redesign/mobile-note-row.png')
        print(f"note rows: {note_rows.count()}")

    # 完整测量
    info = page.evaluate("""() => {
      const out = {};
      // 整体页面
      out.body = {
        clientWidth: document.body.clientWidth,
        scrollWidth: document.body.scrollWidth,
        hasHScroll: document.body.scrollWidth > document.body.clientWidth
      };
      // table-wrap
      const tw = document.querySelector('.table-wrap');
      out.tableWrap = {
        clientWidth: tw.clientWidth,
        scrollWidth: tw.scrollWidth,
        hasHScroll: tw.scrollWidth > tw.clientWidth
      };
      // SVG
      const svg = document.querySelector('svg');
      if (svg) out.svg = { clientHeight: svg.clientHeight, viewBox: svg.getAttribute('viewBox') };
      // 表格
      const t = document.querySelector('#tableSection table');
      if (t) {
        const r = t.getBoundingClientRect();
        out.table = { clientWidth: t.clientWidth, scrollWidth: t.scrollWidth, height: r.height };
      }
      return out;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    browser.close()