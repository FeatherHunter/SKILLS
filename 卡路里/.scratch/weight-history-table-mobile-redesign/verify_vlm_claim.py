"""验证 VLM 的"目标线不可见"声称"""
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path(".scratch/weight-history-table-mobile-redesign/sample.html").resolve()}')
    page.wait_for_load_state('networkidle')

    # 查 SVG 内部所有 path/line/rect + 看 goal line 是否渲染
    info = page.evaluate("""() => {
      const svg = document.querySelector('svg#chart');
      if (!svg) return { error: 'no svg' };
      const allLines = Array.from(svg.querySelectorAll('line, path, rect'));
      // 找 goal line(应该是 stroke="#34c759" + stroke-dasharray="6,3")
      const goalLineCandidates = allLines.filter(el => {
        const s = el.getAttribute('stroke') || getComputedStyle(el).stroke;
        const dash = el.getAttribute('stroke-dasharray') || '';
        return s.includes('34, 199, 89') || s.toLowerCase().includes('34c759') || dash.includes('6,3');
      });
      return {
        svgViewBox: svg.getAttribute('viewBox'),
        svgClientHeight: svg.getBoundingClientRect().height,
        totalElements: allLines.length,
        goalLineCount: goalLineCandidates.length,
        goalLineDetails: goalLineCandidates.map(el => ({
          tag: el.tagName,
          y1: el.getAttribute('y1'),
          y2: el.getAttribute('y2'),
          stroke: el.getAttribute('stroke') || getComputedStyle(el).stroke,
          dasharray: el.getAttribute('stroke-dasharray') || getComputedStyle(el).strokeDasharray,
        })),
        // 检查 SVG 实际渲染范围(viewBox 与可视范围)
        allElementsBounds: allLines.slice(0, 5).map(el => {
          const r = el.getBBox();
          return { tag: el.tagName, x: r.x, y: r.y, w: r.width, h: r.height };
        })
      };
    }""")
    import json
    print(json.dumps(info, ensure_ascii=False, indent=2))
    browser.close()