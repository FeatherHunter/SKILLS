/* 作息记录 5 模板共享 JS 引擎(2026-07-23)
 * 由 meta.mode 分发:record-day / record-range / record-compare / record-category / record-anomaly
 * 数据契约:{status, data:{meta, ...模式字段, ai_questions:[]}, message}
 * 严格遵守预置 HTML 手册 §11(XSS escapeHTML) + §7(5 状态)
 */
(function(){
  "use strict";
  var MODE_LABELS = {
    "record-day":     "作息记录 · 单日报告",
    "record-range":   "作息记录 · 区间报告",
    "record-compare": "作息记录 · 区间对比",
    "record-category":"作息记录 · 类别深挖",
    "record-anomaly": "作息记录 · 异常检测",
    "record-detail":  "作息记录 · 详情溯源"
  };

  function escapeHTML(s){
    return String(s ?? "").replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
    });
  }
  function pad2(n){ return n<10 ? "0"+n : ""+n; }
  function fmtMin(m){ if(!m||m<0) return "0m"; var h=Math.floor(m/60),mm=m%60; return h?(mm?h+"h"+mm+"m":h+"h"):mm+"m"; }

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
  document.title = (data.meta && data.meta.title) || "作息记录报告";
  document.getElementById("page-title").textContent = meta.title || "作息记录报告";
  document.getElementById("page-subtitle").textContent = meta.subtitle || "";
  document.getElementById("page-meta").innerHTML =
    "由作息管家 · schedule_cli render-record-* 生成 · " + (meta.generated_at || "");

  // M3: 字典分发,缺 key 报错清晰(替代原 5 个 if 链)
  var MODE_HANDLERS = {
    "record-day":      renderDay,
    "record-range":    renderRange,
    "record-compare":  renderCompare,
    "record-category": renderCategory,
    "record-anomaly":  renderAnomaly,
    "record-detail":   renderDetail
  };
  var handler = MODE_HANDLERS[meta.mode];
  if (handler) return handler(data, meta);

  // 列出所有支持的 mode 帮用户排查
  var supportedModes = Object.keys(MODE_HANDLERS).join(", ");
  document.getElementById("root").innerHTML =
    '<div class="error"><h3>❌ 未知 mode: ' + escapeHTML(meta.mode || "(空)") + '</h3>' +
    '<div class="highlight-row" style="background:#fff0f0;color:#a83228;margin-top:8px">' +
    '<span class="h-emoji">💡</span><div class="h-text">支持的 mode: ' + escapeHTML(supportedModes) +
    '<br/>字段 --mode 由 schedule_html_render.py render_record_* 设置,可能版本不匹配。</div></div></div>';

  // ===== T1: 单日 =====
  function renderDay(data, meta){
    var records = data.records || [];
    var summaryItems = data.summary_items || [];
    var timeline = data.timeline || [];
    var sleepData = data.sleep_data || {};
    var health = data.health || null;
    var aiQs = data.ai_questions || [];

    if (records.length === 0) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>' + escapeHTML(meta.date || "这一天") + ' · 无作息记录</h3>' +
        '<p>该日 schedule_records 表没有记录</p></div>';
      return;
    }

    var html = "";
    var totalMin = meta.total_minutes || summaryItems.reduce(function(s,x){return s+(x.total_minutes||0);}, 0);
    html += statBlock(totalMin >= 24*60 ? "good" : "warn", fmtMin(totalMin), "总记录时长", totalMin >= 24*60 ? "✓ 24h 满" : "未满 24h");
    html += statBlock("", summaryItems.length + " 类", "活跃分类", "");
    if (health !== null) {
      var hs = health.score || 0;
      var hcls = hs >= 80 ? "good" : (hs >= 60 ? "" : (hs >= 40 ? "warn" : "danger"));
      html += statBlock(hcls, hs + " 分", "健康分", health.label || "");
    }
    var sleepItem = summaryItems.find(function(s){ return /睡眠|午睡/.test(s.category); });
    if (sleepItem) {
      var sleepClass = sleepItem.total_minutes >= 7*60 ? "good" : (sleepItem.total_minutes >= 5*60 ? "warn" : "danger");
      html += statBlock(sleepClass, fmtMin(sleepItem.total_minutes), "睡眠", sleepClass === "good" ? "✓ 充足" : "⚠ 偏短");
    }

    html += '<div class="card">';
    html += '<h2><span class="icon">📊</span> 分类时长</h2>';
    html += '<div class="cat-grid">';
    summaryItems.forEach(function(s){
      var pctNum = parseFloat(s.pct) || 0;  // M6 防御:强制数字
      html += '<div class="cat-row"><span class="emoji">' + escapeHTML(s.emoji) + '</span>' +
              '<div style="flex:1"><div style="display:flex;justify-content:space-between"><span class="name">' + escapeHTML(s.category) + '</span><span class="dur">' + escapeHTML(s.duration_text) + '</span></div>' +
              '<div class="bar"><div class="bar-fill" style="width:' + pctNum + '%;background:' + escapeHTML(s.color || "#8E8E93") + '"></div></div></div></div>';
    });
    html += '</div></div>';

    html += '<div class="card"><h2><span class="icon">⏰</span> 24小时时间轴</h2>';
    html += '<div class="tl">';
    timeline.forEach(function(t){
      var bg = t.color || "#f5f5f7";
      var tip = t.tip || (t.hour + ":00");
      html += '<div class="tl-block" style="background:' + escapeHTML(bg) + '"><div class="tip">' + escapeHTML(tip) + '</div></div>';
    });
    html += '</div><div class="tl-labels"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>';
    var seen = {}; var seenCats = [];
    timeline.forEach(function(t){ if (!seen[t.category]) { seen[t.category]=1; seenCats.push(t); } });
    if (seenCats.length > 0) {
      html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:10px;color:var(--fg2)">';
      seenCats.forEach(function(t){
        html += '<span style="display:flex;align-items:center;gap:3px"><span style="width:8px;height:8px;border-radius:2px;background:' + escapeHTML(t.color) + '"></span>' + escapeHTML(t.category) + '</span>';
      });
      html += '</div>';
    }
    html += '</div>';

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

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子(看完可追问用户)</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }
    html += recordsCollapsible(records);

    document.getElementById("root").innerHTML = html;
  }

  // ===== 辅助:记录明细折叠区(11 字段全暴露,苹果风白底卡片) =====
  function fmtDurShort(mins){
    var h = Math.floor(mins / 60), m = mins % 60;
    if (h && m) return h + 'h' + m + 'm';
    if (h) return h + 'h';
    return m + 'm';
  }

  function recordFieldRow(label, value){
    return '<div><div style="color:var(--fg3);font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">' + escapeHTML(label) + '</div>' +
           '<div style="color:var(--fg);font-weight:500;font-size:12.5px">' + escapeHTML(value || '—') + '</div></div>';
  }

  function recordsCollapsible(records){
    if (!records || records.length === 0) return '';
    var html = '<div class="card">';
    html += '<h2 style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">';
    html += '<span><span class="icon">📋</span> 记录明细</span>';
    html += '<span style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:var(--blue2);background:var(--soft);padding:5px 12px;border-radius:999px">' + records.length + ' 条 · 每条 11 字段</span>';
    html += '</h2>';
    records.forEach(function(r, i){
      var dur = fmtDurShort(r.duration_minutes || 0);
      html += '<details style="margin-bottom:10px;border:1px solid var(--line);border-radius:14px;background:var(--card);overflow:hidden;transition:border-color .15s,box-shadow .15s">';
      html += '<summary style="list-style:none;cursor:pointer;padding:16px 20px;display:flex;align-items:center;gap:14px;user-select:none;transition:background .15s" onmouseover="this.style.background=\'var(--soft)\'" onmouseout="this.style.background=\'\'">';
      html += '<span style="flex-shrink:0;width:32px;height:32px;border-radius:10px;background:var(--blue);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;letter-spacing:-.02em">' + (i + 1) + '</span>';
      html += '<div style="flex:1;min-width:0;line-height:1.45">';
      html += '<div style="font-size:14.5px;font-weight:600;color:var(--fg);letter-spacing:-.01em">' + escapeHTML(r.time_start) + ' – ' + escapeHTML(r.time_end) + ' · ' + escapeHTML(r.activity) + '</div>';
      html += '<div style="font-size:12.5px;color:var(--fg3);margin-top:3px;display:flex;gap:8px;flex-wrap:wrap">';
      html += '<span style="color:var(--blue2);font-weight:500">' + escapeHTML(r.category) + '</span>';
      html += '<span>·</span><span>' + dur + '</span>';
      html += '<span>·</span><span>id=' + r.id + '</span>';
      html += '</div></div>';
      html += '<span style="flex-shrink:0;color:var(--fg3);font-size:20px;line-height:1;font-weight:300;transition:transform .2s" class="chevron">›</span>';
      html += '</summary>';

      html += '<div style="padding:4px 20px 18px;border-top:1px solid var(--line);background:#fafbfd">';
      html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px 24px;margin:14px 0;padding:14px 16px;background:var(--card);border-radius:10px;border:1px solid var(--line);font-size:12.5px">';
      html += recordFieldRow('ID', String(r.id));
      html += recordFieldRow('日期', r.date);
      html += recordFieldRow('时段', r.time_start + '–' + r.time_end);
      html += recordFieldRow('时长', dur + ' (' + r.duration_minutes + ' 分钟)');
      html += recordFieldRow('分类', r.category);
      html += recordFieldRow('创建时间', r.created_at);
      html += '</div>';

      html += '<div style="margin:14px 0">';
      html += '<div style="font-size:10.5px;font-weight:700;color:var(--fg3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">消息原文</div>';
      html += '<div style="font-size:13px;line-height:1.7;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">' + escapeHTML(r.source_contents || '（无）') + '</div>';
      html += '</div>';

      html += '<div style="margin:14px 0">';
      html += '<div style="font-size:10.5px;font-weight:700;color:var(--fg3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">消息时间戳</div>';
      html += '<div style="font-size:12px;line-height:1.7;color:var(--fg2);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">' + escapeHTML(r.source_timestamps || '（无）') + '</div>';
      html += '</div>';

      html += '<div style="margin:14px 0 6px">';
      html += '<div style="font-size:10.5px;font-weight:700;color:var(--fg3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">人工智能推理链</div>';
      html += '<div style="font-size:13px;line-height:1.7;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;white-space:pre-wrap">' + escapeHTML(r.analysis_reasoning || '（无）') + '</div>';
      html += '</div>';

      html += '</div></details>';
    });
    html += '</div>';
    return html;
  }

  // ===== T2: 区间 =====
  function renderRange(data, meta){
    var records = data.records || [];
    var summaryItems = data.summary_items || [];
    var dimTotals = data.dim_totals || {};
    var health = data.health || null;
    var aiQs = data.ai_questions || [];
    var days = data.days || [];
    var trend = data.trend_chart || "";

    if (days === 0) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>' + escapeHTML(meta.start || "") + ' ~ ' + escapeHTML(meta.end || "") + ' · 无数据</h3></div>';
      return;
    }

    var html = "";
    html += statBlock("", days + " 天", "区间长度", "");
    html += statBlock("", (data.total_records || 0) + " 条", "总记录数", "");
    if (health) {
      var hs = health.score || 0;
      var hcls = hs >= 80 ? "good" : (hs >= 60 ? "" : (hs >= 40 ? "warn" : "danger"));
      html += statBlock(hcls, hs + " 分", "区间健康分", "");
    }
    if (dimTotals["维持"] !== undefined) {
      var sleep = dimTotals["维持"];
      var sc = sleep >= 7*60*days ? "good" : (sleep >= 5*60*days ? "warn" : "danger");
      html += statBlock(sc, fmtMin(sleep), "总睡眠", "日均 " + fmtMin(Math.round(sleep/days)));
    }

    html += '<div class="card"><h2><span class="icon">📊</span> 分类时长</h2><div class="cat-grid">';
    summaryItems.forEach(function(s){
      html += '<div class="cat-row"><span class="emoji">' + escapeHTML(s.emoji) + '</span>' +
              '<div style="flex:1"><div style="display:flex;justify-content:space-between"><span class="name">' + escapeHTML(s.category) + '</span><span class="dur">' + escapeHTML(s.duration_text) + '</span></div>' +
              '<div class="bar"><div class="bar-fill" style="width:' + s.pct + '%;background:' + escapeHTML(s.color || "#8E8E93") + '"></div></div></div></div>';
    });
    html += '</div></div>';

    if (trend) {
      html += '<div class="card"><h2><span class="icon">📈</span> 7 维趋势</h2><div class="trend">' + trend + '</div></div>';
    }

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }
    html += recordsCollapsible(data.records || []);

    document.getElementById("root").innerHTML = html;
  }

  // ===== T3: 对比 =====
  function renderCompare(data, meta){
    var ranges = data.ranges || [];
    var diffs = data.diffs || [];
    var aiQs = data.ai_questions || [];

    if (ranges.length < 2) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>对比需要 ≥ 2 个区间</h3><p>当前 ' + ranges.length + ' 个</p></div>';
      return;
    }

    var html = "";
    if (ranges[0] && ranges[1]) {
      var dDays = (ranges[0].days || 1) - (ranges[1].days || 1);
      var dTotal = (ranges[0].total || 0) - (ranges[1].total || 0);
      html += statBlock("", ranges[0].label || "A", "区间 A", "");
      html += statBlock("", ranges[1].label || "B", "区间 B", "");
      html += statBlock("mute", (dDays >= 0 ? "+" : "") + dDays + " 天", "时长差", dDays > 0 ? "A 更长" : (dDays < 0 ? "B 更长" : "持平"));
      html += statBlock("mute", (dTotal >= 0 ? "+" : "") + fmtMin(Math.abs(dTotal)), "总分钟差", dTotal === 0 ? "持平" : "");
    }

    html += '<div class="card"><h2><span class="icon">📊</span> 7 维对比</h2><div class="compare">';
    diffs.forEach(function(d){
      var maxV = Math.max(d.a || 0, d.b || 0, 1);
      html += '<div class="cmp-bar">' +
              '<div class="label">' + escapeHTML(d.emoji) + ' ' + escapeHTML(d.dim) + '</div>' +
              '<div class="track">' +
                '<div class="seg" style="width:' + Math.round((d.a||0)/maxV*100) + '%;background:#5E5CE6;justify-content:flex-start">' + escapeHTML(fmtMin(d.a || 0)) + '</div>' +
                '<div class="seg" style="width:' + Math.round((d.b||0)/maxV*100) + '%;background:#FF9500">' + escapeHTML(fmtMin(d.b || 0)) + '</div>' +
              '</div>' +
              '<div class="delta" style="color:' + escapeHTML(d.color || "#8E8E93") + '">' + escapeHTML(d.direction || "") + ' ' + escapeHTML(d.delta_short) + '</div>' +
              '</div>';
    });
    html += '</div></div>';

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }
    html += recordsCollapsible(data.records || []);

    document.getElementById("root").innerHTML = html;
  }

  // ===== T4: 类别深挖 =====
  function renderCategory(data, meta){
    var records = data.records || [];
    var cat = meta.category || "未知";
    var totalMin = data.total_minutes || 0;
    var days = data.days || [];
    var heatmap = data.heatmap || [];
    var aiQs = data.ai_questions || [];

    var html = "";
    html += statBlock("", escapeHTML(cat), "深挖类别", "");
    html += statBlock("", fmtMin(totalMin), "总时长", "");
    html += statBlock("", days.length + " 天", "活跃天数", "");
    if (data.daily_avg) html += statBlock("good", fmtMin(data.daily_avg), "日均", "");

    if (heatmap.length > 0) {
      html += '<div class="card"><h2><span class="icon">🔥</span> 24h × ' + days.length + ' 天 热力图</h2>';
      html += '<div style="overflow-x:auto"><div class="heatmap" style="grid-template-columns:60px repeat(24,1fr);min-width:600px">';
      html += '<div class="hm-row-label" style="background:#fff"></div>';
      for (var h = 0; h < 24; h++) {
        html += '<div class="hm-col-label" style="background:#fff">' + (h%3===0?pad2(h):"") + '</div>';
      }
      days.forEach(function(d, i){
        html += '<div class="hm-row-label">' + escapeHTML(d) + '</div>';
        for (var j = 0; j < 24; j++) {
          var cell = heatmap[i] && heatmap[i][j] || {color:"#f5f5f7"};
          html += '<div class="hm-cell" style="background:' + escapeHTML(cell.color) + '" title="' + escapeHTML(d + " " + pad2(j) + ":00") + '"></div>';
        }
      });
      html += '</div></div></div>';
    }

    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 AI 思考钩子</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }
    html += recordsCollapsible(data.records || []);

    document.getElementById("root").innerHTML = html;
  }

  // ===== T5: 异常 =====
  function renderAnomaly(data, meta){
    var anomalies = data.anomalies || [];
    var radarSvg = data.radar_svg || "";
    var aiQs = data.ai_questions || [];

    var html = "";
    html += statBlock("", (meta.window || 7) + " 天", "检测窗口", "");
    html += statBlock(anomalies.length > 0 ? "danger" : "good", anomalies.length + " 项", "异常数", anomalies.length > 0 ? "需关注" : "✓ 正常");
    html += statBlock("danger", anomalies.filter(function(a){return a.severity==="red";}).length, "🔴 严重", "");
    html += statBlock("warn", anomalies.filter(function(a){return a.severity==="yellow";}).length, "🟡 警告", "");

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
    html += recordsCollapsible(data.records || []);

    document.getElementById("root").innerHTML = html;
  }

  // ===== T6: 详情页（人工智能推理溯源） =====
  function renderDetail(data, meta){
    var records = data.records || [];
    var selected = data.selected_record || null;
    var aiQs = data.ai_questions || [];

    if (records.length === 0) {
      document.getElementById("root").innerHTML =
        '<div class="empty"><h3>' + escapeHTML(meta.date || "这一天") + ' · 无作息记录</h3>' +
        '<p>该日 schedule_records 表没有记录,无法显示详情</p></div>';
      return;
    }

    var html = "";

    // ① 4 卡摘要
    var totalMin = meta.total_minutes || 0;
    var earliest = records.length > 0 ? records[0].time_start : "";
    var latest = records.length > 0 ? records[records.length - 1].time_end : "";
    var rangeText = (earliest && latest) ? (earliest + "–" + latest) : "—";
    var catCount = 0;
    var seenCats = {};
    records.forEach(function(r){ if (!seenCats[r.category]) { seenCats[r.category] = 1; catCount++; } });
    html += statBlock(totalMin >= 24*60 ? "good" : "warn", fmtMin(totalMin), "总记录时长", "");
    html += statBlock("", records.length + " 条", "当日记录", "");
    html += statBlock("", catCount + " 类", "活跃分类", "");
    html += statBlock("", rangeText, "时段范围", "");

    // ② records 折叠区(11 字段全暴露,默认折叠,展开看完整字段)
    html += recordsCollapsible(records);

    // ③ 人工智能思考钩子卡(苹果风浅黄底,放在末尾)
    if (aiQs.length > 0) {
      html += '<div class="ai-hooks"><h3>💡 人工智能思考钩子（看完可追问用户）</h3><ul>';
      aiQs.forEach(function(q){ html += '<li>' + escapeHTML(q) + '</li>'; });
      html += '</ul></div>';
    }

    document.getElementById("root").innerHTML = html;
  }

  // ===== helper: stat 4 卡块 =====
  function statBlock(variant, value, label, delta){
    variant = variant || "";
    var colorMap = {good:"var(--good)",warn:"var(--warn)",danger:"var(--danger)",mute:"var(--mute)"};
    var color = colorMap[variant] || "var(--fg)";
    return '<div class="card" style="padding:14px 16px;margin-bottom:8px"><div style="display:flex;align-items:baseline;gap:8px">' +
             '<span style="font-size:24px;font-weight:700;color:' + color + '">' + escapeHTML(value) + '</span>' +
             '<span style="font-size:12px;color:var(--fg2)">' + escapeHTML(label) + '</span>' +
             (delta ? '<span style="margin-left:auto;font-size:11px;color:var(--fg3)">' + escapeHTML(delta) + '</span>' : '') +
           '</div></div>';
  }
})();
