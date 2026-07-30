"""用 Playwright 打开 weight_history.html 在 mobile viewport 看实际效果"""
import json
import asyncio
from pathlib import Path
from playwright.sync_api import sync_playwright

# 1. 复制 template + 注入 24 天数据(从用户实际 HTML)
template_path = Path('templates/weight_history.html')
sample_path = Path('.scratch/weight-history-table-mobile-redesign/sample.html')
sample_path.parent.mkdir(parents=True, exist_ok=True)

# 24 天数据(从用户实测 HTML 提取)
data = {
    "status": "ok",
    "data": {
        "summary": {
            "subtitle": "起始 90.9 → 结束 86.9 · 日均 -0.138 kg",
            "k1": {"label": "当前体重", "value": "86.9 kg", "extra": '<span style="color:#34c759">↓ 4.0 kg</span>'},
            "k2": {"label": "24 天变化", "value": "-4.0 kg", "extra": "-4.4%"},
            "k3": {"label": "日均变化", "value": "-0.138 kg/天", "extra": '<span style="color:#34c759">减重方向</span>'},
            "k4": {"label": "当前 BMI", "value": "27.7", "extra": "异常"},
            "table_header": "<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th><th>注</th></tr>"
        },
        "items": [
            {"date": "2026-07-01", "kg": 90.9, "bmi": 29.0, "delta": 0, "note": ""},
            {"date": "2026-07-02", "kg": 91.9, "bmi": 29.3, "delta": 1.0, "note": ""},
            {"date": "2026-07-03", "kg": 90.3, "bmi": 28.8, "delta": -1.6, "note": ""},
            {"date": "2026-07-04", "kg": 89.25, "bmi": 28.5, "delta": -1.0, "note": ""},
            {"date": "2026-07-05", "kg": 89.85, "bmi": 28.7, "delta": 0.6, "note": ""},
            {"date": "2026-07-07", "kg": 90.0, "bmi": 28.7, "delta": 0.2, "note": ""},
            {"date": "2026-07-10", "kg": 89.85, "bmi": 28.7, "delta": -0.2, "note": ""},
            {"date": "2026-07-11", "kg": 89.15, "bmi": 28.5, "delta": -0.7, "note": ""},
            {"date": "2026-07-11", "kg": 88.9, "bmi": 28.4, "delta": -0.2, "note": ""},
            {"date": "2026-07-12", "kg": 88.9, "bmi": 28.4, "delta": 0.0, "note": ""},
            {"date": "2026-07-14", "kg": 88.85, "bmi": 28.4, "delta": -0.1, "note": ""},
            {"date": "2026-07-15", "kg": 88.5, "bmi": 28.2, "delta": -0.3, "note": ""},
            {"date": "2026-07-16", "kg": 88.25, "bmi": 28.2, "delta": -0.2, "note": ""},
            {"date": "2026-07-17", "kg": 88.8, "bmi": 28.3, "delta": 0.5, "note": ""},
            {"date": "2026-07-19", "kg": 89.3, "bmi": 28.5, "delta": 0.5, "note": ""},
            {"date": "2026-07-21", "kg": 88.2, "bmi": 28.2, "delta": -1.1, "note": ""},
            {"date": "2026-07-22", "kg": 87.85, "bmi": 28.0, "delta": -0.4, "note": ""},
            {"date": "2026-07-24", "kg": 87.85, "bmi": 28.0, "delta": 0.0, "note": ""},
            {"date": "2026-07-25", "kg": 87.8, "bmi": 28.0, "delta": -0.0, "note": ""},
            {"date": "2026-07-26", "kg": 87.4, "bmi": 27.9, "delta": -0.4, "note": ""},
            {"date": "2026-07-27", "kg": 87.75, "bmi": 28.0, "delta": 0.3, "note": "晨起空腹"},
            {"date": "2026-07-28", "kg": 87.3, "bmi": 27.9, "delta": -0.5, "note": ""},
            {"date": "2026-07-28", "kg": 87.05, "bmi": 27.8, "delta": -0.2, "note": ""},
            {"date": "2026-07-30", "kg": 86.9, "bmi": 27.7, "delta": -0.1, "note": "晨起空腹"},
        ],
        "target": 73.0,
        "meta": {"start": "2026-07-01", "end": "2026-07-30", "days": 30, "today": "2026-07-30"},
        "mode": "trend"
    }
}

# 2. Inject data
html = template_path.read_text(encoding='utf-8')
html = html.replace(
    '<!--INJECT-DATA-->',
    f'<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};</script>',
    1
)
sample_path.write_text(html, encoding='utf-8')
print(f'wrote {sample_path}')

# 3. 启动 Playwright(在 iPhone SE 模拟 375x667)
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={'width': 375, 'height': 667},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
    )
    page = context.new_page()
    page.goto(f'file:///{sample_path.resolve()}')
    page.wait_for_load_state('networkidle')

    # 4. 截图整页
    page.screenshot(path='.scratch/weight-history-table-mobile-redesign/full-mobile.png', full_page=True)
    print('screenshot full page saved')

    # 5. 截图表(只明细表)
    table = page.query_selector('#tableSection')
    if table:
        table.screenshot(path='.scratch/weight-history-table-mobile-redesign/table-only.png')
        print('table screenshot saved')

    # 6. 测量关键元素
    measure = page.evaluate("""
() => {
  const out = {};
  // KPI 卡片
  const kpis = document.querySelectorAll('.kpi');
  if (kpis.length > 0) {
    const first = kpis[0];
    const r = first.getBoundingClientRect();
    out.firstKpi = { width: r.width, height: r.height, left: r.left };
  }
  // 表格
  const ths = document.querySelectorAll('#tableSection th');
  out.thCount = ths.length;
  if (ths.length > 0) {
    out.thWidths = Array.from(ths).map(th => {
      const r = th.getBoundingClientRect();
      return { text: th.textContent.trim(), width: r.width };
    });
  }
  // 注 列实际可见字符
  const noteCells = document.querySelectorAll('#tableSection td:last-child');
  out.lastCells = Array.from(noteCells).slice(-3).map(td => ({
    text: td.textContent.trim(),
    clientWidth: td.clientWidth,
    scrollWidth: td.scrollWidth
  }));
  // 整体页面宽
  out.bodyWidth = document.body.clientWidth;
  out.bodyScrollWidth = document.body.scrollWidth;
  // table-wrap 滚动
  const tw = document.querySelector('.table-wrap');
  if (tw) {
    out.tableWrap = { clientWidth: tw.clientWidth, scrollWidth: tw.scrollWidth };
  }
  return out;
}""")
    print('\n=== Mobile 测量 (iPhone SE 375x667) ===')
    import json
    print(json.dumps(measure, ensure_ascii=False, indent=2))

    browser.close()