"""检查 goal line 为什么不渲染"""
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    # 看 SVG 内所有 line/rect 包含的 attribute + 计算后的 y 位置
    info = page.evaluate("""() => {
      const svg = document.querySelector('svg#chart');
      const all = Array.from(svg.querySelectorAll('*'));
      return all.map(el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return {
          tag: el.tagName,
          text: (el.textContent || '').slice(0, 30),
          y_attr: el.getAttribute('y1') || el.getAttribute('y2') || el.getAttribute('y') || '-',
          stroke: s.stroke,
          dash: s.strokeDasharray,
          top: r.top,
          left: r.left,
          width: r.width,
        };
      });
    }""")
    import json
    print(json.dumps(info, ensure_ascii=False, indent=2))