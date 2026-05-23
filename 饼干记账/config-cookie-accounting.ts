// config-cookie-accounting.ts
// SkillBoard 数据层配置文件 - 饼干记账
// 数据库文件：biscuit_accountant.db

interface SkillField {
  name: string;
  type: string;
  label: string;
  primaryKey?: boolean;
  visible?: boolean;
  nullable?: boolean;
  format?: string;
  unit?: string;
  default?: string;
  options?: string[];
}

interface SkillTable {
  name: string;
  fields: SkillField[];
}

interface SkillQuery {
  id: string;
  label: string;
  sql: string;
  params?: Array<{
    name: string;
    type: string;
    label: string;
    options?: Array<{ label: string; value: string }>;
  }>;
  chartType?: string;
  chartConfig?: {
    colorScheme?: string[];
  };
}

interface SkillAction {
  id: string;
  label: string;
  type: string;
  targetTable: string;
  fields: Array<{
    field: string;
    required?: boolean;
    source: string;
    prompt?: string;
    value?: string;
    format?: string;
    unit?: string;
    options?: string[];
  }>;
}

interface SkillView {
  id: string;
  label: string;
  icon: string;
  components: Record<string, any>;
}

interface SkillConfig {
  meta: {
    name: string;
    label: string;
    icon: string;
    description: string;
    dbFiles: string[];
  };
  schema: { tables: SkillTable[] };
  queries: SkillQuery[];
  actions: SkillAction[];
  views: SkillView[];
}

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
          { name: "id",       type: "INTEGER", label: "ID",         primaryKey: true, visible: false },
          { name: "category", type: "TEXT",    label: "分类",        nullable: false,
            options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                      "工资", "奖金", "兼职", "投资", "其他"] },
          { name: "time",     type: "TEXT",    label: "时间",        nullable: false, format: "datetime" },
          { name: "amount",   type: "REAL",    label: "金额",        nullable: false, format: "currency", unit: "元" },
          { name: "account",  type: "TEXT",    label: "账户",        default: "" },
          { name: "ledger",   type: "TEXT",    label: "账本",        default: "生活" },
          { name: "currency", type: "TEXT",    label: "货币",        default: "人民币" },
          { name: "note",     type: "TEXT",    label: "备注",        default: "" },
          { name: "created_at", type: "TEXT", label: "创建时间",    visible: false },
        ],
      },
    ],
  },

  // ── 3. queries（预设查询）───────────────────────────────────
  queries: [
    // 今日记录
    {
      id: "daily-records",
      label: "今日记录",
      sql: "SELECT id, category, time, amount, note FROM bills WHERE time >= '{{date}} 00:00:00' AND time <= '{{date}} 23:59:59' ORDER BY time DESC",
      params: [
        { name: "date", type: "date", label: "日期" },
      ],
    },

    // 月度支出汇总（柱状图）
    {
      id: "monthly-summary",
      label: "月度支出汇总",
      sql: `SELECT
              category,
              SUM(ABS(amount)) as total,
              COUNT(*) as count
            FROM bills
            WHERE time >= '{{month}}-01 00:00:00'
              AND time < '{{month_end}} 00:00:00'
              AND amount < 0
            GROUP BY category
            ORDER BY total DESC`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
      chartType: "bar",
      chartConfig: {
        colorScheme: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"],
      },
    },

    // 分类支出明细（环形图）
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

    // 收支总览（月度计数/支出/收入/净额）
    // 返回标量值，适合用 card 组件展示
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
              AND time < '{{month_end}} 00:00:00'`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
    },

    // 周期对比（本周 vs 上周 / 本月 vs 上月）
    // period 参数由前端用于决定调用两次本查询的日期范围，SQL 中不直接使用
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

    // 最近记录
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

    // 关键词搜索
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
        {
          field: "category",
          required: true,
          source: "user-input",
          prompt: "选择分类",
          options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                    "工资", "奖金", "兼职", "投资", "其他"],
        },
        {
          field: "time",
          required: true,
          source: "user-input",
          prompt: "时间（格式：YYYY-MM-DD HH:MM:SS，留空填当前时间）",
          format: "datetime",
        },
        {
          field: "amount",
          required: true,
          source: "user-input",
          prompt: "输入金额（负数为支出，正数为收入）",
          format: "currency",
          unit: "元",
        },
        {
          field: "account",
          source: "user-input",
          prompt: "账户（可选）",
        },
        {
          field: "ledger",
          source: "fixed",
          value: "生活",
        },
        {
          field: "currency",
          source: "fixed",
          value: "人民币",
        },
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
