"""看实际渲染:note 行到底怎么显示"""
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    # 滚到 note 行附近
    page.evaluate("window.scrollTo(0, 1500)")

    # 整页 + 表格截图
    page.screenshot(path='.scratch/weight-history-table-mobile-redesign/scrolled.png', full_page=False)

    # note 行精确测量
    info = page.evaluate("""() => {
      const noteRows = document.querySelectorAll('#tableSection tbody tr');
      const results = [];
      noteRows.forEach((tr, i) => {
        const tds = tr.querySelectorAll('td');
        if (tds.length === 5) {
          const r = tr.getBoundingClientRect();
          const lastTd = tds[4];
          const lastR = lastTd.getBoundingClientRect();
          results.push({
            rowIdx: i,
            rowHeight: r.height,
            noteText: lastTd.textContent.trim(),
            noteWidth: lastR.width,
            noteX: lastR.left,
            noteScrollWidth: lastTd.scrollWidth,
            noteOverflow: lastTd.scrollWidth > lastR.width
          });
        }
      });
      return results;
    }""")
    import json
    print(json.dumps(info, ensure_ascii=False, indent=2))

    browser.close()