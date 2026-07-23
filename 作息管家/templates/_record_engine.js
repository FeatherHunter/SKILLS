</html>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ title }}</title>
<style>
/* ===== 作息记录 HTML 报告 — 5 模板共享设计系统 ===== */
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --fg:#1d1d1f;--fg2:#6e6e73;--fg3:#86868b;--bg:#f5f5f7;
  --card:#fff;--line:#d2d2d7;--soft:#f5f8ff;
  --blue:#007aff;--blue2:#0a63ce;
  --good:#34c759;--warn:#ff9500;--danger:#ff3b30;--mute:#9b9ba0;
  --shadow:0 1px 2px rgba(0,0,0,.04),0 12px 36px rgba(0,0,0,.06);
}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg);line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 24px 96px}

/* hero */
.hero{background:linear-gradient(180deg,#fff 0%,#f8fbff 100%);border-radius:24px;padding:28px 32px;margin-bottom:20px;box-shadow:var(--shadow)}
.hero .eyebrow{font-size:11px;color:var(--blue);font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
.hero h1{font-size:28px;line-height:1.2;letter-spacing:-.025em;margin-bottom:4px}
.hero .lead{font-size:14px;color:var(--fg2);max-width:780px}
.hero .meta{margin-top:8px;color:var(--fg3);font-size:11px}

/* 5 模板布局主区域 */
#root{margin-top:8px}

/* 通用卡片 */
.card{background:var(--card);border-radius:16px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.card h2{font-size:15px;margin-bottom:14px;color:var(--fg2);text-transform:uppercase;letter-spacing:.06em;display:flex;align-items:center;gap:8px}
.card h2 .icon{font-size:18px}

/* 摘要卡(L1 速读层) */
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.stat{background:var(--card);border-radius:12px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.04);border:1px solid var(--line)}
.stat .l{font-size:10px;color:var(--fg3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.stat .n{font-size:22px;font-weight:700;line-height:1.2}
.stat .d{font-size:11px;color:var(--fg2);margin-top:2px}
.stat.good .n{color:var(--good)}
.stat.warn .n{color:var(--warn)}
.stat.danger .n{color:var(--danger)}
.stat.mute .n{color:var(--mute)}

/* 分类进度条(L1 速读层) */
.cat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.cat-row{display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--soft);border-radius:8px}
.cat-row .emoji{font-size:18px;width:24px;text-align:center;flex-shrink:0}
.cat-row .name{flex:1;font-size:12px;font-weight:500}
.cat-row .dur{font-size:11px;color:var(--fg2);font-variant-numeric:tabular-nums}
.cat-row .bar{height:3px;background:#e5e5e5;border-radius:2px;margin-top:4px;overflow:hidden}
.cat-row .bar-fill{height:100%;border-radius:2px;transition:width .6s ease}

/* 24h 时间轴 */
.tl{display:flex;gap:1px;height:32px;border-radius:6px;overflow:hidden;margin-bottom:6px}
.tl-block{flex:1;position:relative;cursor:pointer;transition:opacity .15s}
.tl-block:hover{opacity:.85}
.tl-block .tip{display:none;position:absolute;bottom:calc(100% + 4px);left:50%;transform:translateX(-50%);background:#1d1d1d;color:#fff;font-size:10px;padding:3px 6px;border-radius:4px;white-space:nowrap;z-index:10;pointer-events:none}
.tl-block:hover .tip{display:block}
.tl-labels{display:flex;justify-content:space-between;font-size:9px;color:var(--fg3);padding:0 1px}

/* 趋势折线图(L2 趋势层) — SVG */
.trend{position:relative;width:100%;height:160px;background:var(--soft);border-radius:8px;padding:12px 8px}
.trend svg{width:100%;height:100%}
.trend .grid{stroke:var(--line);stroke-width:0.5;stroke-dasharray:2 2}
.trend .axis{font-size:9px;fill:var(--fg3)}
.trend .line{fill:none;stroke-width:2}
.trend .dot{fill:#fff;stroke-width:2}
.trend .legend{position:absolute;top:6px;right:8px;display:flex;gap:8px;font-size:9px;color:var(--fg2)}

/* 热力图(L2) */
.heatmap{display:grid;gap:1px;background:var(--line);border-radius:6px;overflow:hidden}
.hm-cell{padding:2px;font-size:8px;text-align:center;color:#fff;min-height:18px;display:flex;align-items:center;justify-content:center}
.hm-row-label{background:#f5f5f7;color:var(--fg2);font-size:10px;padding:4px;min-width:60px;display:flex;align-items:center}
.hm-col-label{background:#f5f5f7;color:var(--fg2);font-size:9px;padding:2px}

/* 对比柱(L3 决策层) */
.compare{display:grid;gap:12px}
.cmp-bar{display:flex;align-items:center;gap:10px}
.cmp-bar .label{width:60px;font-size:12px;font-weight:500}
.cmp-bar .track{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:4px;align-items:center;height:18px}
.cmp-bar .seg{height:100%;border-radius:3px;display:flex;align-items:center;justify-content:flex-end;padding:0 4px;font-size:9px;color:#fff;font-weight:600}
.cmp-bar .delta{width:60px;font-size:11px;text-align:right;font-variant-numeric:tabular-nums}

/* 健康分大圆 */
.health{text-align:center;padding:20px}
.health .circle{display:inline-block;width:120px;height:120px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto;position:relative}
.health .circle svg{position:absolute;top:0;left:0;transform:rotate(-90deg)}
.health .score{font-size:36px;font-weight:700;line-height:1}
.health .lbl{font-size:11px;color:var(--fg3);margin-top:4px}

/* AI 钩子卡(L3 决策层) */
.ai-hooks{background:linear-gradient(180deg,#fff5e0 0%,#fffbf0 100%);border:1px solid #ffd9a8;border-radius:12px;padding:16px 20px;margin-bottom:16px}
.ai-hooks h3{font-size:13px;color:#a25b00;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.ai-hooks ul{margin-left:20px}
.ai-hooks li{font-size:13px;color:#5c3a00;line-height:1.7}

/* 异常点红框 */
.anomaly{border:2px solid var(--danger);background:#fff0ee;border-radius:12px;padding:14px 18px;margin-bottom:8px}
.anomaly.yellow{border-color:var(--warn);background:#fff5e0;color:#a25b00}
.anomaly .head{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;margin-bottom:4px}

/* 雷达图(7 维对比) */
.radar-wrap{position:relative;max-width:420px;margin:0 auto}
.radar-svg{width:100%;height:auto}
.radar-axis{font-size:10px;fill:var(--fg2)}

/* 空态/错误 */
.empty{padding:40px 20px;text-align:center;color:var(--fg2);background:var(--card);border-radius:14px}
.error{background:#fff5f5;border:1px solid #ffd1d1;border-radius:14px;padding:24px;color:var(--danger);text-align:center}

/* 离线 banner */
.offline{background:#fff3e0;border:1px solid #ffb74d;border-radius:8px;padding:8px 12px;margin-bottom:16px;text-align:center;color:#a25b00;font-size:12px}

/* footer */
.footer{margin-top:32px;text-align:center;color:var(--fg3);font-size:11px}

/* 响应式 */
@media(max-width:760px){
  .wrap{padding:20px 12px 60px}
  .hero{padding:20px 18px;border-radius:18px}
  .hero h1{font-size:22px}
  .summary{grid-template-columns:repeat(2,1fr)}
  .cat-grid{grid-template-columns:1fr}
  .cmp-bar .label{width:48px;font-size:11px}
  .cmp-bar .delta{width:48px;font-size:10px}
}
</style>
</head>
<body>
<div class="wrap">

<!-- 离线 banner(预置 HTML 手册 §7 必备) -->
<div class="offline">📡 本页面是作息管家的离线 HTML 报告 — 单文件自包含,无外部依赖,可直接保存或转发</div>

<header class="hero">
  <div class="eyebrow" id="eyebrow">Schedule Record Report</div>
  <h1 id="page-title">…</h1>
  <p class="lead" id="page-subtitle">加载中…</p>
  <div class="meta" id="page-meta">由作息管家 · schedule_cli render-record-* 生成</div>
</header>

<div id="root"></div>

<div class="footer">
  数据源:<code>schedule_records</code> 内部表 · 模板:<code>{{ template_name }}</code> · 输出:<code>SKILLS_DB_PATH/schedule_html/</code>
</div>

</div>

<!-- 模式 B(手册 §5):<script id="payload"> 注入 JSON -->
<script id="payload" type="application/json"></script>

<script>
/* ===== 5 模板通用 JS 引擎 =====
 * 模式由 meta.mode 决定: record-day / record-range / record-compare / record-category / record-anomaly
 * 数据契约: {status, data:{meta, ...模式特定字段, ai_questions:[]}, message}
 * 严格遵守手册 §11:XSS 全部 escapeHTML;§7:5 状态齐全
 */
(function(){
  "use strict";
  var MODE_LABELS = {
    "record-day":     "作息记录 · 单日报告",
    "record-range":   "作息记录 · 区间报告",
    "record-compare": "作息记录 · 区间对比",
    "record-category":"作息记录 · 类别深挖",
    "record-anomaly": "作息记录 · 异常检测"
  };

  function escapeHTML(s){
    return String(s ?? "").replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
    });
  }

  function pad2(n){ return n<10 ? "0"+n : ""+n; }
  function fmtMin(m){ if(!m||m<0) return "0m"; var h=Math.floor(m/60),mm=m%60; return h?(mm?h+"h"+mm+"m":h+"h"):mm+"m"; }
  function pct(part, whole){ if(!whole) return 0; return Math.round(part/whole*1000)/10; }

  var raw = document.getElementById("payload");
  var payload, parseError = null;
  try { payload = JSON.parse(raw.textContent || "{}"); }
  catch(e){ parseError = e && e.message ? e.message : String(e); }

  if (parseError) {
    document.getElementById("root").innerHTML =
      '<div class="error"><h3>❌ 数据解析失败</h3><pre style="text-align:left;background:#fff;padding:12px;border-radius:6px;margin-top:8px;overflow:auto">' +
      escapeHTML(parseError) + '</pre></div>';
    return;
  }

  var status = (payload && payload.status) || "ok";
  var data = (payload && payload.data) || {};
  if (status !== "ok") {
    document.getElementById("root").innerHTML =
      '<div class="error"><h3>❌ 加载失败</h3><p>' + escapeHTML((payload && payload.message) || JSON.stringify(payload)) + '</p></div>';
    return;
  }

  var meta = data.meta || {};
  document.getElementById("eyebrow").textContent = MODE_LABELS[meta.mode] || "作息记录报告";
  document.title = (payload.data && payload.data.meta && payload.data.meta.title) || "作息记录报告";
  document.getElementById("page-title").textContent = meta.title || "作息记录报告";
  document.getElementById("page-subtitle").textContent = meta.subtitle || "";
  document.getElementById("page-meta").innerHTML =
    "由作息管家 · schedule_cli render-record-* 生成 · " + (meta.generated_at || "");

  // 模式分发
  if (meta.mode === "record-day")      return renderDay(payload, data, meta);
  if (meta.mode === "record-range")    return renderRange(payload, data, meta);
  if (meta.mode === "record-compare")  return renderCompare(payload, data, meta);
  if (meta.mode === "record-category") return renderCategory(payload, data, meta);
  if (meta.mode === "record-anomaly")  return renderAnomaly(payload, data, meta);

  document.getElementById("root").innerHTML =
    '<div class="error"><h3>❌ 未知 mode: ' + escapeHTML(meta.mode || "") + '</h3></div>';

  // ===== T1: 单日 =====
  function renderDay(payload, data, meta){
    var summaryItems = data.summary_items || [];
    var timeline = data.timeline || [];
    var sleepData = data.sleep_data || {};
    var health = data.health || null;
    var aiQs = data.ai_questions || [];

    if (summaryItems.length === 0) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>' + escapeHTML(meta.date || "这一天") + ' · 无作息记录</h3>' +
        '<p>该日 schedule_records 表没有记录</p></div>';
      return;
    }

    var html = "";

    // 摘要 4 卡
    html += statBlock("total", summaryItems.length + " 类", "分类", "");
    var totalMin = meta.total_minutes || summaryItems.reduce(function(s,x){return s+(x.total_minutes||0);}, 0);
    html += statBlock("duration", fmtMin(totalMin), "总记录时长", totalMin >= 24*60 ? "✓ 24h 满" : "未满 24h",
                       totalMin >= 24*60 ? "good" : "warn");
    if (health !== null) {
      var hs = health.score || 0;
      var hcls = hs >= 80 ? "good" : (hs >= 60 ? "" : (hs >= 40 ? "warn" : "danger"));
      html += statBlock("health", hs + " 分", "健康分", health.label || "", hcls);
    }
    var sleepItem = summaryItems.find(function(s){ return /睡眠|午睡/.test(s.category); });
    if (sleepItem) {
      var sleepClass = sleepItem.total_minutes >= 7*60 ? "good" : (sleepItem.total_minutes >= 5*60 ? "warn" : "danger");
      html += statBlock("sleep", fmtMin(sleepItem.total_minutes), "睡眠", sleepClass === "good" ? "✓ 充足" : "⚠ 偏短", sleepClass);
    }

    html += '<div class="card">';
    html += '<h2><span class="icon">📊</span> 分类时长</h2>';
    html += '<div class="cat-grid">';
    summaryItems.forEach(function(s){
      var c = s.color || "#8E8E93";
      html += '<div class="cat-row">' +
              '<span class="emoji">' + escapeHTML(s.emoji) + '</span>' +
              '<div style="flex:1">' +
                '<div style="display:flex;justify-content:space-between"><span class="name">' + escapeHTML(s.category) + '</span><span class="dur">' + escapeHTML(s.duration_text) + '</span></div>' +
                '<div class="bar"><div class="bar-fill" style="width:' + s.pct + '%;background:' + escapeHTML(c) + '"></div></div>' +
              '</div></div>';
    });
    html += '</div></div>';

    // 24h 时间轴
    html += '<div class="card"><h2><span class="icon">⏰</span> 24小时时间轴</h2>';
    html += '<div class="tl">';
    timeline.forEach(function(t){
      var bg = t.color || "#f5f5f7";
      var tip = t.tip || (t.hour + ":00");
      html += '<div class="tl-block" style="background:' + escapeHTML(bg) + '"><div class="tip">' + escapeHTML(tip) + '</div></div>';
    });
    html += '</div>';
    html += '<div class="tl-labels"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>';
    // legend
    var seen = {}; var seenCats = [];
    timeline.forEach(function(t){ if (!seen[t.category]) { seen[t.category]=1; seenCats.push(t); } });
    if (seenCats.length > 0) {
      html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:10px;color:var(--fg2)">';
      seenCats.forEach(function(t){
        html += '<span style="display:flex;align-items:center;gap:3px">' +
                '<span style="width:8px;height:8px;border-radius:2px;background:' + escapeHTML(t.color) + '"></span>' +
                escapeHTML(t.category) + '</span>';
      });
      html += '</div>';
    }
    html += '</div>';

    // 睡眠分析
    if (sleepData.main_sleep) {
      html += '<div class="card"><h2><span class="icon">🌙</span> 睡眠分析</h2>';
      var ms = sleepData.main_sleep;
      var suff = sleepData.is_sufficient ? '✅ 充足' : '⚠️ 偏短(建议 ≥7h)';
      html += '<div class="cat-row"><span class="emoji">🛌</span><div style="flex:1">' +
              '<div style="display:flex;justify-content:space-between"><span class="name">主睡眠</span><span class="dur">' + escapeHTML(ms.duration_text) + ' (' + escapeHTML(ms.time_start) + '~' + escapeHTML(ms.time_end) + ')</span></div>' +
              '<div class="bar"><div class="bar-fill" style="width:100%;background:' + escapeHTML(ms.color || "#5E5CE6") + '"></div></div>' +
              '<div style="font-size:10px;color:var(--fg3);margin-top:2px">' + suff + (sleepData.total_records > 1 ? ' · 共 ' + sleepData.total_records + ' 段(含午睡)' : '') + '</div>' +
              '</div></div></div>';
    }

    // AI 钩子
    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子(看完可追问用户)</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== T2: 区间 =====
  function renderRange(payload, data, meta){
    var summaryItems = data.summary_items || [];
    var seriesByDim = data.series_by_dim || {};
    var dimTotals = data.dim_totals || {};
    var health = data.health || null;
    var aiQs = data.ai_questions || [];
    var days = data.days || [];

    if (days === 0) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>' + escapeHTML(meta.start || "") + ' ~ ' + escapeHTML(meta.end || "") + ' · 无数据</h3>' +
        '<p>该区间 schedule_records 表没有记录</p></div>';
      return;
    }

    var html = "";

    // 摘要 4 卡
    html += statBlock("days", days + " 天", "区间", "");
    html += statBlock("rec", (data.total_records || 0) + " 条", "总记录数", "");
    if (health) {
      var hs = health.score || 0;
      var hcls = hs >= 80 ? "good" : (hs >= 60 ? "" : (hs >= 40 ? "warn" : "danger"));
      html += statBlock("health", hs + " 分", "区间健康分", "", hcls);
    }
    if (dimTotals["维持"]) {
      var sleep = dimTotals["维持"];
      var sc = sleep >= 7*60*days ? "good" : (sleep >= 5*60*days ? "warn" : "danger");
      html += statBlock("sleep", fmtMin(sleep), "总睡眠", "日均 " + fmtMin(Math.round(sleep/days)), sc);
    }

    // 分类时长(区间)
    html += '<div class="card"><h2><span class="icon">📊</span> 分类时长</h2>';
    html += '<div class="cat-grid">';
    summaryItems.forEach(function(s){
      var c = s.color || "#8E8E93";
      html += '<div class="cat-row">' +
              '<span class="emoji">' + escapeHTML(s.emoji) + '</span>' +
              '<div style="flex:1">' +
                '<div style="display:flex;justify-content:space-between"><span class="name">' + escapeHTML(s.category) + '</span><span class="dur">' + escapeHTML(s.duration_text) + '</span></div>' +
                '<div class="bar"><div class="bar-fill" style="width:' + s.pct + '%;background:' + escapeHTML(c) + '"></div></div>' +
              '</div></div>';
    });
    html += '</div></div>';

    // 趋势折线 — 7 维 × N 天
    if (data.trend_chart) {
      html += '<div class="card"><h2><span class="icon">📈</span> 7 维趋势</h2>';
      html += '<div class="trend">' + data.trend_chart + '</div></div>';
    }

    // AI 钩子
    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== T3: 对比 =====
  function renderCompare(payload, data, meta){
    var ranges = data.ranges || [];
    var diffs = data.diffs || [];
    var aiQs = data.ai_questions || [];

    if (ranges.length < 2) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>对比需要 ≥ 2 个区间</h3><p>当前 ' + ranges.length + ' 个</p></div>';
      return;
    }

    var html = "";

    // 4 卡:对比 2 段时间长度 + 总分钟差 + 健康分差
    if (ranges[0] && ranges[1]) {
      var dDays = (ranges[0].days || 1) - (ranges[1].days || 1);
      var dTotal = (ranges[0].total || 0) - (ranges[1].total || 0);
      html += statBlock("a", ranges[0].label, "区间 A", "");
      html += statBlock("b", ranges[1].label, "区间 B", "");
      html += statBlock("d-days", (dDays>=0?"+":"") + dDays + " 天", "时长差", dDays > 0 ? "A 更长" : (dDays < 0 ? "B 更长" : ""), dDays === 0 ? "mute" : "");
      html += statBlock("d-total", (dTotal>=0?"+":"") + fmtMin(Math.abs(dTotal)), "总分钟差", dTotal === 0 ? "持平" : "", "mute");
    }

    // 7 维对比柱
    html += '<div class="card"><h2><span class="icon">📊</span> 7 维对比</h2>';
    html += '<div class="compare">';
    diffs.forEach(function(d){
      var maxV = Math.max(d.a || 0, d.b || 0, 1);
      var color = d.color || "#8E8E93";
      html += '<div class="cmp-bar">' +
              '<div class="label">' + escapeHTML(d.emoji) + ' ' + escapeHTML(d.dim) + '</div>' +
              '<div class="track">' +
                '<div class="seg" style="width:' + Math.round((d.a || 0)/maxV*100) + '%;background:#5E5CE6;justify-content:flex-start">' + escapeHTML(fmtMin(d.a || 0)) + '</div>' +
                '<div class="seg" style="width:' + Math.round((d.b || 0)/maxV*100) + '%;background:#FF9500">' + escapeHTML(fmtMin(d.b || 0)) + '</div>' +
              '</div>' +
              '<div class="delta" style="color:' + escapeHTML(color) + '">' + escapeHTML(d.direction || "") + ' ' + escapeHTML(d.delta_short) + '</div>' +
              '</div>';
    });
    html += '</div></div>';

    // AI 钩子
    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== T4: 类别深挖 =====
  function renderCategory(payload, data, meta){
    var cat = meta.category || "未知";
    var totalMin = data.total_minutes || 0;
    var days = data.days || [];
    var heatmap = data.heatmap || [];
    var dayAverages = data.day_averages || [];
    var aiQs = data.ai_questions || [];

    var html = "";

    html += statBlock("cat", cat, "深挖类别", "");
    html += statBlock("total", fmtMin(totalMin), "总时长", "");
    html += statBlock("days", days.length + " 天", "活跃天数", "");
    if (data.daily_avg) {
      html += statBlock("avg", fmtMin(data.daily_avg), "日均", "", "good");
    }

    if (heatmap.length > 0) {
      html += '<div class="card"><h2><span class="icon">🔥</span> 24h × ' + days.length + ' 天 热力图</h2>';
      html += '<div style="overflow-x:auto"><div class="heatmap" style="grid-template-columns:60px repeat(24,1fr);min-width:600px">';
      // 表头:24 小时
      html += '<div class="hm-row-label" style="background:#fff"></div>';
      for (var h = 0; h < 24; h++) {
        html += '<div class="hm-col-label" style="background:#fff">' + (h%3===0?pad2(h):"") + '</div>';
      }
      // 行
      days.forEach(function(d, i){
        html += '<div class="hm-row-label">' + escapeHTML(d) + '</div>';
        for (var h = 0; h < 24; h++) {
          var cell = heatmap[i] && heatmap[i][h] || {color:"#f5f5f7"};
          var col = cell.color || "#f5f5f7";
          html += '<div class="hm-cell" style="background:' + escapeHTML(col) + '" title="' + escapeHTML(d + ' ' + pad2(h) + ':00")"></div>';
        }
      });
      html += '</div></div></div>';
    }

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== T5: 异常 =====
  function renderAnomaly(payload, data, meta){
    var anomalies = data.anomalies || [];
    var radarSvg = data.radar_svg || "";
    var aiQs = data.ai_questions || [];

    var html = "";

    html += statBlock("window", (meta.window || 7) + " 天", "检测窗口", "");
    html += statBlock("anom", anomalies.length + " 项", "异常数", anomalies.length > 0 ? "需关注" : "✓ 正常", anomalies.length > 0 ? "danger" : "good");
    html += statBlock("sev-red", anomalies.filter(function(a){return a.severity==="red";}).length, "🔴 严重", "", "danger");
    html += statBlock("sev-yel", anomalies.filter(function(a){return a.severity==="yellow";}).length, "🟡 警告", "", "warn");

    if (anomalies.length > 0) {
      html += '<div class="card"><h2><span class="icon">🚨</span> 异常详情</h2>';
      anomalies.forEach(function(a){
        var cls = a.severity === "red" ? "anomaly" : "anomaly yellow";
        html += '<div class="' + cls + '"><div class="head">' + escapeHTML(a.message) + '</div>' +
                '<div style="font-size:11px;color:var(--fg2)">基线 ' + escapeHTML(fmtMin(a.baseline)) +
                ' · 当前 ' + escapeHTML(fmtMin(a.current)) +
                ' · 偏差 ' + escapeHTML(String(a.delta_pct)) + '%</div></div>';
      });
      html += '</div>';
    }

    if (radarSvg) {
      html += '<div class="card"><h2><span class="icon">📡</span> 7 维雷达</h2>';
      html += '<div class="radar-wrap">' + radarSvg + '</div></div>';
    }

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== helper: stat 4 卡块 =====
  function statBlock(cls, value, label, delta, variant){
    variant = variant || "";
    return '<div class="card" style="padding:14px 16px;margin-bottom:8px"><div style="display:flex;align-items:baseline;gap:8px">' +
             '<span style="font-size:24px;font-weight:700;color:' + (variant==="good"?"var(--good)":variant==="warn"?"var(--warn)":variant==="danger"?"var(--danger)":variant==="mute"?"var(--mute)":"var(--fg)") + '">' + escapeHTML(value) + '</span>' +
             '<span style="font-size:12px;color:var(--fg2)">' + escapeHTML(label) + '</span>' +
             (delta ? '<span style="margin-left:auto;font-size:11px;color:var(--fg3)">' + escapeHTML(delta) + '</span>' : '') +
           '</div></div>';
  }
})();
</script>
</body>
</html>
