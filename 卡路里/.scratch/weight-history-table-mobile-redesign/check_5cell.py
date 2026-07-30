"""确认 Playwright 看到 5-cell rows"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    info = page.evaluate("""() => {
      const rows = Array.from(document.querySelectorAll('#tableSection tbody tr'));
      const result = { totalRows: rows.length, byCells: {}, notes: [] };
      rows.forEach((tr, i) => {
        const cells = tr.querySelectorAll('td');
        const n = cells.length;
        result.byCells[n] = (result.byCells[n] || 0) + 1;
        if (n === 5) {
          const lastTd = cells[4];
          result.notes.push({ rowIdx: i, text: lastTd.textContent.trim(), width: lastTd.getBoundingClientRect().width });
        }
      });
      return result;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))

    # 截 5-cell 行的细节
    page.locator('#tableSection').screenshot(path='.scratch/weight-history-table-mobile-redesign/table-section-actual.png')

    browser.close()