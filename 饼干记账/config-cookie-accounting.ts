// config-cookie-accounting.ts
// SkillBoard 数据层配置文件 - 饼干记账
// 数据库文件：biscuit_accountant.db
// 生成依据：scripts/db.py（表结构/写入逻辑）+ scripts/query.py（查询逻辑）+ scripts/analyze.py（分析逻辑）
//
// 字段来源对应：
//   meta.dbFiles           ← db.py DB_FILENAME = "biscuit_accountant.db"
//   schema                 ← db.py init_db() 建表语句（9字段）
//   queries.daily-records  ← query.py list_today() → fetch_all(from_time, to_time)
//   queries.monthly-summary ← analyze.py monthly_summary()（amount < 0，按 category GROUP BY）
//   queries.category-breakdown ← analyze.py get_category_breakdown()（含 avg）
//   queries.monthly-overview  ← analyze.py _get_totals()（count/expense/income/net）
//   queries.period-compare    ← analyze.py compare_periods()
//   queries.recent-records    ← query.py list_recent(limit) → fetch_all(limit)
//   queries.keyword-search   ← query.py search_keyword() → fetch_all(keyword)
//   actions.add-record       ← db.py insert_record() 入参（7字段，无 id/created_at）

export const CookieAccountingConfig: SkillConfig = {
  // ── 1. meta（元数据）─────────────────────────────────────────
  meta: {
    name: "cookie-accounting",
    label: "饼干记账",
    icon: "Cookie",
    description: "记录饼干购买与消耗，支持日/周/月统计和分类分析",
    dbFiles: ["biscuit_accountant.db"],
  },

  // ── 2. schema（数据库结构）──────────────────────────────────
  schema: {
    tables: [
      {
        name: "bills",
        fields: [
          // id：自增主键，DB 自动生成，UI 不展示
          { name: "id",       type: "INTEGER", label: "ID",         primaryKey: true, visible: false },
          // category：非空，选项覆盖支出9类 + 收入5类
          { name: "category", type: "TEXT",    label: "分类",        nullable: false,
            options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                      "工资", "奖金", "兼职", "投资"] },
          // time：非空，完整时间戳格式
          { name: "time",     type: "TEXT",    label: "时间",        nullable: false, format: "datetime" },
          // amount：非空，负数为支出，正数为收入
          { name: "amount",   type: "REAL",    label: "金额",        nullable: false, format: "currency", unit: "元" },
          // account：默认空字符串
          { name: "account",  type: "TEXT",    label: "账户",        default: "" },
          // ledger：默认"生活"
          { name: "ledger",   type: "TEXT",    label: "账本",        default: "生活" },
          // currency：默认"人民币"
          { name: "currency", type: "TEXT",    label: "货币",        default: "人民币" },
          // note：默认空字符串
          { name: "note",     type: "TEXT",    label: "备注",        default: "" },
          // created_at：DB 自动填充 CURRENT_TIMESTAMP，UI 不展示
          { name: "created_at", type: "TEXT", label: "创建时间",    visible: false },
        ],
      },
    ],
  },

  // ── 3. queries（预设查询）───────────────────────────────────
  queries: [
    // ── 3.1 今日记录 ──────────────────────────────────────────
    // 来自 query.py list_today()：WHERE time >= '{date} 00:00:00' AND time <= '{date} 23:59:59'
    {
      id: "daily-records",
      label: "今日记录",
      sql: "SELECT id, category, time, amount, note FROM bills WHERE time >= '{{date}} 00:00:00' AND time <= '{{date}} 23:59:59' ORDER BY time DESC",
      params: [
        { name: "date", type: "date", label: "日期" },
      ],
    },

    // ── 3.2 月度支出汇总（柱状图）─────────────────────────────
    // 来自 analyze.py monthly_summary()：
    //   WHERE time >= '{month}-01 00:00:00' AND time <= '{month_end} 23:59:59' AND amount < 0
    //   GROUP BY category ORDER BY total DESC
    {
      id: "monthly-summary",
      label: "月度支出汇总",
      sql: `SELECT
              category,
              SUM(ABS(amount)) as total,
              COUNT(*) as count
            FROM bills
            WHERE time >= '{{month}}-01 00:00:00'
              AND time <= '{{month_end}} 23:59:59'
              AND amount < 0
            GROUP BY category
            ORDER BY total DESC`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        // month_end：由前端根据 month 计算当月最后一天（如 2026-05 → 2026-05-31）
        // ⚠️ type 必须是 date，不能是 text（协作指南明确要求）
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
      chartType: "bar",
      chartConfig: {
        colorScheme: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"],
      },
    },

    // ── 3.3 分类支出明细（环形图）─────────────────────────────
    // 来自 analyze.py get_category_breakdown()：
    //   WHERE time >= '{from} 00:00:00' AND time <= '{to} 23:59:59' AND amount < 0
    //   含 AVG(ABS(amount)) as avg
    {
      id: "category-breakdown",
      label: "分类分析",
      sql: `SELECT
              category,
              SUM(ABS(amount)) as total,
              COUNT(*) as count,
              AVG(ABS(amount)) as avg
            FROM bills
            WHERE time >= '{{from}} 00:00:00'
              AND time <= '{{to}} 23:59:59'
              AND amount < 0
            GROUP BY category
            ORDER BY total DESC`,
      params: [
        { name: "from", type: "date", label: "开始日期" },
        { name: "to",   type: "date", label: "结束日期" },
      ],
      chartType: "doughnut",
      chartConfig: {
        colorScheme: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"],
      },
    },

    // ── 3.4 收支总览（月度计数/支出/收入/净额）───────────────
    // 来自 analyze.py _get_totals()：
    //   expense = SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END)
    //   income  = SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)
    //   net     = income - expense
    {
      id: "monthly-overview",
      label: "收支总览",
      sql: `SELECT
              COUNT(*) as count,
              SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
              SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
              SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)
              - SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as net
            FROM bills
            WHERE time >= '{{month}}-01 00:00:00'
              AND time <= '{{month_end}} 23:59:59'`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
    },

    // ── 3.5 周期对比（本周 vs 上周 / 本月 vs 上月）────────────
    // 来自 analyze.py compare_periods()：前端调用两次本查询（本期+上期），前端自行计算 change
    {
      id: "period-compare",
      label: "周期对比",
      sql: `SELECT
              CASE WHEN amount < 0 THEN 'expense' ELSE 'income' END as type,
              SUM(ABS(amount)) as total,
              COUNT(*) as count
            FROM bills
            WHERE time >= '{{from}} 00:00:00'
              AND time <= '{{to}} 23:59:59'
            GROUP BY type`,
      params: [
        { name: "from",   type: "date",  label: "开始日期" },
        { name: "to",     type: "date",  label: "结束日期" },
        { name: "period", type: "select", label: "周期",
          options: [
            { label: "本周 vs 上周", value: "week" },
            { label: "本月 vs 上月", value: "month" },
          ],
        },
      ],
      chartType: "bar",
    },

    // ── 3.6 最近记录 ──────────────────────────────────────────
    // 来自 query.py list_recent(limit)：fetch_all(limit=N) → SELECT ... LIMIT N
    {
      id: "recent-records",
      label: "最近记录",
      sql: "SELECT id, category, time, amount, note FROM bills ORDER BY time DESC LIMIT {{limit}}",
      params: [
        { name: "limit", type: "select", label: "条数",
          options: [
            { label: "10条", value: "10" },
            { label: "20条", value: "20" },
            { label: "50条", value: "50" },
          ],
        },
      ],
    },

    // ── 3.7 关键词搜索 ────────────────────────────────────────
    // 来自 query.py search_keyword()：WHERE note LIKE '%{keyword}%'
    // SQLite 拼接字符串用 ||，不能写成 Python 格式化
    {
      id: "keyword-search",
      label: "关键词搜索",
      sql: "SELECT id, category, time, amount, note FROM bills WHERE note LIKE '%' || '{{keyword}}' || '%' ORDER BY time DESC",
      params: [
        { name: "keyword", type: "text", label: "关键词" },
      ],
    },
  ],

  // ── 4. actions（操作定义）──────────────────────────────────
  actions: [
    {
      id: "add-record",
      label: "新增记账",
      type: "insert",
      targetTable: "bills",
      fields: [
        // category：必填，用户从下拉框选择
        {
          field: "category",
          required: true,
          source: "user-input",
          prompt: "选择分类",
          options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                    "工资", "奖金", "兼职", "投资"],
        },
        // time：必填，用户输入（留空则由前端填当前时间）
        {
          field: "time",
          required: true,
          source: "user-input",
          prompt: "时间（格式：YYYY-MM-DD HH:MM:SS，留空填当前时间）",
          format: "datetime",
        },
        // amount：必填，用户输入（负数为支出，正数为收入）
        {
          field: "amount",
          required: true,
          source: "user-input",
          prompt: "输入金额（负数为支出，正数为收入）",
          format: "currency",
          unit: "元",
        },
        // account：可选，默认空字符串
        {
          field: "account",
          source: "user-input",
          prompt: "账户（可选）",
        },
        // ledger：固定值"生活"
        {
          field: "ledger",
          source: "fixed",
          value: "生活",
        },
        // currency：固定值"人民币"
        {
          field: "currency",
          source: "fixed",
          value: "人民币",
        },
        // note：可选，用户输入
        {
          field: "note",
          source: "user-input",
          prompt: "备注（可选）",
        },
      ],
    },
  ],

  // ── 5. views（视图定义）────────────────────────────────────
  views: [
    { id: "daily",    label: "每日记录",  icon: "CalendarBlank",
      components: { table: { queryId: "daily-records",    sortable: true,  pageSize: 20 } } },
    { id: "monthly",  label: "月度统计",  icon: "ChartBar",
      components: { chart: { queryId: "monthly-summary" } } },
    { id: "overview", label: "收支总览",  icon: "Coins",
      components: { chart: { queryId: "monthly-overview" } } },
    { id: "category", label: "分类分析",  icon: "ChartPieSlice",
      components: { chart: { queryId: "category-breakdown" } } },
    { id: "compare",  label: "周期对比",  icon: "ArrowsLeftRight",
      components: { chart: { queryId: "period-compare" } } },
    { id: "recent",   label: "最近记录",  icon: "Clock",
      components: { table: { queryId: "recent-records",   sortable: true,  pageSize: 10 } } },
    { id: "search",   label: "关键词搜索", icon: "MagnifyingGlass",
      components: { table: { queryId: "keyword-search",   sortable: true,  pageSize: 20 } } },
    { id: "add",      label: "新增记账",  icon: "Plus",
      components: { form: { actionId: "add-record" } } },
  ],
};