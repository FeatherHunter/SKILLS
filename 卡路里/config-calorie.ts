/**
 * SkillBoard Config - 卡路里技能
 * 卡路里与营养追踪技能
 *
 * 数据库文件: calorie_data.db
 * 包含表: entries | daily_goal | weight_log | exercise_log | nutrition_products | fitness_goals | sleep_records
 */

// === SkillConfig 类型 ===
type SkillConfig = {
  meta: Meta
  schema: Schema
  queries: QueryDef[]
  actions: ActionDef[]
  views: ViewDef[]
}

type Meta = {
  name: string
  label: string
  icon: string
  description: string
  dbFiles: string[]
}

type Schema = {
  tables: TableSchema[]
}

type TableSchema = {
  name: string
  fields: FieldDef[]
}

type FieldDef = {
  name: string
  type: string
  label: string
  primaryKey?: boolean
  nullable?: boolean
  default?: string | number
  format?: string
  unit?: string
  options?: string[]
  editable?: boolean
  visible?: boolean
}

type QueryDef = {
  id: string
  label: string
  sql: string
  params?: ParamDef[]
  chartType?: 'bar' | 'line' | 'pie' | 'doughnut' | 'radar'
  chartConfig?: ChartConfig
}

type ParamDef = {
  name: string
  type: 'date' | 'month' | 'year' | 'range' | 'text' | 'select'
  label: string
  default?: string
  options?: { label: string; value: string }[]
}

type ChartConfig = {
  stack?: boolean
  horizontal?: boolean
  colorScheme?: string[]
}

type ActionDef = {
  id: string
  label: string
  type: 'insert' | 'update' | 'delete'
  targetTable: string
  fields: ActionFieldDef[]
}

type ActionFieldDef = {
  field: string
  required?: boolean
  default?: string
  source: 'fixed' | 'user-input' | 'auto'
  value?: string
  prompt?: string
  format?: string
  unit?: string
  options?: string[]
}

type ViewDef = {
  id: string
  label: string
  icon?: string
  components: {
    table?: {
      queryId: string
      columns?: string[]
      sortable?: boolean
      pageSize?: number
    }
    chart?: {
      queryId: string
    }
    form?: {
      actionId: string
    }
  }
}

// ============================================================
// META
// ============================================================
export const CalorieConfig: SkillConfig = {

  // ============================================================
  // META
  // ============================================================
  meta: {
    name: 'calorie',
    label: '卡路里',
    icon: 'ForkKnife',
    description: '热量与营养追踪，记录饮食、体重、运动、睡眠，支持每日目标和目标进度分析',
    dbFiles: ['calorie_data.db']
  },

  // ============================================================
  // SCHEMA
  // ============================================================
  schema: {
    tables: [

      // --- entries：食物记录 ---
      {
        name: 'entries',
        fields: [
          { name: 'id',           type: 'INTEGER', label: 'ID',           primaryKey: true },
          { name: 'date',         type: 'TEXT',    label: '日期',          format: 'date',    nullable: false, default: "date('now')" },
          { name: 'time',         type: 'TEXT',    label: '时间',          format: 'datetime' },
          { name: 'food_name',    type: 'TEXT',    label: '食物名称',      nullable: false },
          { name: 'grams',        type: 'INTEGER', label: '重量',          unit: '克' },
          { name: 'calories',     type: 'REAL',    label: '热量',          unit: '千卡', editable: true },
          { name: 'protein',      type: 'REAL',    label: '蛋白质',        unit: '克' },
          { name: 'carbs',        type: 'REAL',    label: '碳水',          unit: '克' },
          { name: 'fat',          type: 'REAL',    label: '脂肪',          unit: '克' },
          { name: 'note',         type: 'TEXT',    label: '备注' },
          { name: 'created_at',   type: 'TEXT',    label: '创建时间',      format: 'datetime', visible: false }
        ]
      },

      // --- daily_goal：每日目标（含体重目标）---
      {
        name: 'daily_goal',
        fields: [
          { name: 'id',               type: 'INTEGER', label: 'ID',              primaryKey: true },
          { name: 'calorie_goal',      type: 'INTEGER', label: '热量目标',        unit: '千卡', default: 1800, editable: true },
          { name: 'protein_goal',      type: 'INTEGER', label: '蛋白质目标',      unit: '克',   default: 150, editable: true },
          { name: 'carbs_goal',        type: 'INTEGER', label: '碳水目标',        unit: '克',   default: 200, editable: true },
          { name: 'fat_goal',          type: 'INTEGER', label: '脂肪目标',        unit: '克',   default: 60,  editable: true },
          { name: 'weight_goal',       type: 'REAL',    label: '体重目标',        unit: '公斤', editable: true },
          { name: 'goal_deadline',    type: 'TEXT',    label: '目标截止日期',   format: 'date' },
          { name: 'updated_at',        type: 'TEXT',    label: '更新时间',       format: 'datetime', visible: false }
        ]
      },

      // --- weight_log：体重记录 ---
      {
        name: 'weight_log',
        fields: [
          { name: 'id',           type: 'INTEGER', label: 'ID',          primaryKey: true },
          { name: 'date',         type: 'TEXT',    label: '日期',        format: 'date',    nullable: false, default: "date('now')" },
          { name: 'time',         type: 'TEXT',    label: '时间',        format: 'datetime' },
          { name: 'weight_kg',    type: 'REAL',    label: '体重',        unit: '公斤', nullable: false, editable: true },
          { name: 'height_cm',    type: 'REAL',    label: '身高',        unit: '厘米' },
          { name: 'bmi',          type: 'REAL',    label: 'BMI' },
          { name: 'note',         type: 'TEXT',    label: '备注' },
          { name: 'created_at',   type: 'TEXT',    label: '创建时间',    format: 'datetime', visible: false }
        ]
      },

      // --- exercise_log：运动记录 ---
      {
        name: 'exercise_log',
        fields: [
          { name: 'id',                  type: 'INTEGER', label: 'ID',            primaryKey: true },
          { name: 'date',                type: 'TEXT',    label: '日期',          format: 'date',    nullable: false, default: "date('now')" },
          { name: 'time',                type: 'TEXT',    label: '时间',          format: 'datetime' },
          { name: 'exercise_type',       type: 'TEXT',    label: '运动类型',      nullable: false, editable: true },
          { name: 'duration_minutes',   type: 'INTEGER', label: '时长',          unit: '分钟', editable: true },
          { name: 'calories_burned',     type: 'INTEGER', label: '消耗热量',      unit: '千卡', nullable: false, editable: true },
          { name: 'note',                type: 'TEXT',    label: '备注' },
          { name: 'reps',                type: 'INTEGER', label: '动作次数' },
          { name: 'created_at',          type: 'TEXT',    label: '创建时间',      format: 'datetime', visible: false }
        ]
      },

      // --- nutrition_products：食品营养成分库 ---
      {
        name: 'nutrition_products',
        fields: [
          { name: 'id',              type: 'INTEGER', label: 'ID',              primaryKey: true },
          { name: 'product_name',    type: 'TEXT',    label: '产品名称',        nullable: false, editable: true },
          { name: 'brand',           type: 'TEXT',    label: '品牌' },
          { name: 'calories',        type: 'REAL',    label: '热量',            unit: '千卡/100g', nullable: false, editable: true },
          { name: 'protein',         type: 'REAL',    label: '蛋白质',          unit: '克/100g',  nullable: false, editable: true },
          { name: 'fat',             type: 'REAL',    label: '脂肪',            unit: '克/100g',  nullable: false, editable: true },
          { name: 'saturated_fat',   type: 'REAL',    label: '饱和脂肪',        unit: '克/100g' },
          { name: 'carbohydrates',   type: 'REAL',    label: '碳水化合物',      unit: '克/100g',  nullable: false, editable: true },
          { name: 'sugar',           type: 'REAL',    label: '糖',              unit: '克/100g' },
          { name: 'dietary_fiber',  type: 'REAL',    label: '膳食纤维',        unit: '克/100g' },
          { name: 'sodium',          type: 'REAL',    label: '钠',              unit: '毫克/100g', nullable: false },
          { name: 'note',            type: 'TEXT',    label: '备注' },
          { name: 'created_at',      type: 'TEXT',    label: '创建时间',        format: 'datetime', visible: false },
          { name: 'updated_at',      type: 'TEXT',    label: '更新时间',        format: 'datetime', visible: false }
        ]
      },

      // --- fitness_goals：健身目标 ---
      {
        name: 'fitness_goals',
        fields: [
          { name: 'id',             type: 'INTEGER', label: 'ID',            primaryKey: true },
          { name: 'name',           type: 'TEXT',    label: '目标名称',      nullable: false, editable: true },
          { name: 'goal_type',      type: 'TEXT',    label: '目标类型',
            options: ['daily', 'weekly', 'monthly', 'longterm'], editable: true },
          { name: 'exercise_type',  type: 'TEXT',    label: '运动类型',      nullable: false, editable: true },
          { name: 'target_unit',    type: 'TEXT',    label: '单位',          nullable: false, editable: true },
          { name: 'target_value',   type: 'INTEGER', label: '目标值',        nullable: false, editable: true },
          { name: 'start_date',      type: 'TEXT',    label: '开始日期',      format: 'date',    nullable: false },
          { name: 'end_date',        type: 'TEXT',    label: '截止日期',      format: 'date' },
          { name: 'status',          type: 'TEXT',    label: '状态',
            options: ['active', 'paused'], default: 'active', editable: true },
          { name: 'note',            type: 'TEXT',    label: '备注' },
          { name: 'created_at',      type: 'INTEGER', label: '创建时间戳',    visible: false },
          { name: 'updated_at',      type: 'INTEGER', label: '更新时间戳',    visible: false }
        ]
      },

      // --- sleep_records：睡眠记录（归属于就寝日）---
      {
        name: 'sleep_records',
        fields: [
          { name: 'id',            type: 'INTEGER', label: 'ID',             primaryKey: true },
          { name: 'date',          type: 'TEXT',    label: '日期（就寝日）', format: 'date',    nullable: false },
          { name: 'sleep_hours',   type: 'REAL',    label: '睡眠时长',        unit: '小时',   nullable: false, editable: true },
          { name: 'bedtime',        type: 'TEXT',    label: '就寝时间',        format: 'datetime' },
          { name: 'wake_time',     type: 'TEXT',    label: '起床时间',        format: 'datetime' },
          { name: 'note',           type: 'TEXT',    label: '备注' },
          { name: 'created_at',     type: 'INTEGER', label: '创建时间戳',      visible: false },
          { name: 'updated_at',     type: 'INTEGER', label: '更新时间戳',      visible: false }
        ]
      }
    ]
  },

  // ============================================================
  // QUERIES
  // ============================================================
  queries: [

    // ---- 每日摘要 ----
    {
      id: 'daily-summary',
      label: '每日摘要',
      sql: `SELECT
              e.date,
              COALESCE(SUM(e.calories), 0)  AS total_cal,
              COALESCE(SUM(e.protein), 0)    AS total_protein,
              COALESCE(SUM(e.carbs), 0)     AS total_carbs,
              COALESCE(SUM(e.fat), 0)        AS total_fat,
              COUNT(e.id)                   AS entry_count,
              g.calorie_goal, g.protein_goal, g.carbs_goal, g.fat_goal
            FROM entries e
            LEFT JOIN daily_goal g ON g.id = 1
            WHERE e.date = '{{date}}'
            GROUP BY e.date`,
      params: [{ name: 'date', type: 'date', label: '日期', default: 'TODAY' }]
    },

    // ---- 每日饮食记录（表格）----
    {
      id: 'daily-entries',
      label: '饮食记录',
      sql: `SELECT id, time, food_name, grams, calories, protein, carbs, fat, note
            FROM entries
            WHERE date = '{{date}}'
            ORDER BY time`,
      params: [{ name: 'date', type: 'date', label: '日期', default: 'TODAY' }]
    },

    // ---- 热量历史 ----
    {
      id: 'calorie-history',
      label: '热量历史',
      sql: `SELECT
              e.date,
              COALESCE(SUM(e.calories), 0) AS total_cal,
              COALESCE(SUM(e.protein), 0)   AS total_protein,
              COALESCE(SUM(e.carbs), 0)    AS total_carbs,
              COALESCE(SUM(e.fat), 0)      AS total_fat,
              g.calorie_goal
            FROM entries e
            LEFT JOIN daily_goal g ON g.id = 1
            WHERE e.date >= '{{start_date}}' AND e.date <= '{{end_date}}'
            GROUP BY e.date
            ORDER BY e.date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'bar',
      chartConfig: { colorScheme: ['#ff6b6b'] }
    },

    // ---- 营养素占比趋势（堆叠柱状图）----
    {
      id: 'macro-ratio-history',
      label: '营养素占比',
      sql: `SELECT
              e.date,
              COALESCE(SUM(e.protein)*4, 0) AS cal_protein,
              COALESCE(SUM(e.carbs)*4, 0)   AS cal_carbs,
              COALESCE(SUM(e.fat)*9, 0)     AS cal_fat
            FROM entries e
            WHERE e.date >= '{{start_date}}' AND e.date <= '{{end_date}}'
            GROUP BY e.date
            ORDER BY e.date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'bar',
      chartConfig: { stack: true, colorScheme: ['#51cf66', '#ffd43b', '#ff922b'] }
    },

    // ---- 体重历史 ----
    {
      id: 'weight-history',
      label: '体重历史',
      sql: `SELECT date, time, weight_kg, bmi, note
            FROM weight_log
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            ORDER BY date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'line',
      chartConfig: { colorScheme: ['#339af0'] }
    },

    // ---- 体重目标进度 ----
    {
      id: 'weight-goal-progress',
      label: '体重目标进度',
      sql: `SELECT
              w.date,
              w.weight_kg,
              g.weight_goal,
              g.goal_deadline,
              w.weight_kg - g.weight_goal AS gap
            FROM weight_log w
            CROSS JOIN daily_goal g ON g.id = 1
            WHERE g.weight_goal IS NOT NULL
            ORDER BY w.date DESC
            LIMIT 1`,
      params: []
    },

    // ---- 运动记录 ----
    {
      id: 'exercise-log',
      label: '运动记录',
      sql: `SELECT id, date, time, exercise_type, duration_minutes, calories_burned, reps, note
            FROM exercise_log
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            ORDER BY date DESC, time DESC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ]
    },

    // ---- 运动汇总 ----
    {
      id: 'exercise-summary',
      label: '运动汇总',
      sql: `SELECT
              date,
              SUM(calories_burned)  AS total_cal,
              SUM(duration_minutes) AS total_dur,
              COUNT(*)              AS ex_count
            FROM exercise_log
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            GROUP BY date
            ORDER BY date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'bar',
      chartConfig: { colorScheme: ['#22b2da'] }
    },

    // ---- 运动类型分布 ----
    {
      id: 'exercise-type-breakdown',
      label: '运动类型分布',
      sql: `SELECT
              exercise_type,
              SUM(calories_burned)  AS total_cal,
              SUM(duration_minutes) AS total_dur,
              COUNT(*)              AS ex_count
            FROM exercise_log
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            GROUP BY exercise_type
            ORDER BY total_cal DESC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'doughnut'
    },

    // ---- 热量缺口分析 ----
    {
      id: 'calorie-deficit',
      label: '热量缺口',
      sql: `SELECT
              e.date,
              COALESCE(SUM(e.calories), 0) AS intake,
              COALESCE(x.burned, 0)       AS burned,
              (COALESCE(x.burned, 0) + {{bmr_est}}) - COALESCE(SUM(e.calories), 0) AS deficit
            FROM entries e
            LEFT JOIN (
              SELECT date, SUM(calories_burned) AS burned
              FROM exercise_log
              WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
              GROUP BY date
            ) x ON x.date = e.date
            WHERE e.date >= '{{start_date}}' AND e.date <= '{{end_date}}'
            GROUP BY e.date
            ORDER BY e.date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' },
        { name: 'bmr_est',    type: 'text', label: '基础代谢估算' }
      ],
      chartType: 'line',
      chartConfig: { colorScheme: ['#be4bdb'] }
    },

    // ---- 食品库列表 ----
    {
      id: 'product-list',
      label: '食品营养库',
      sql: `SELECT id, product_name, brand, calories, protein, fat, saturated_fat,
                    carbohydrates, sugar, dietary_fiber, sodium, note, updated_at
            FROM nutrition_products
            ORDER BY updated_at DESC
            LIMIT {{limit}}`,
      params: [{ name: 'limit', type: 'text', label: '条数限制', default: '50' }]
    },

    // ---- 食品搜索 ----
    {
      id: 'product-search',
      label: '搜索食品',
      sql: `SELECT id, product_name, brand, calories, protein, fat, carbohydrates, sodium
            FROM nutrition_products
            WHERE product_name LIKE '{{keyword}}' OR brand LIKE '{{keyword}}'
            ORDER BY product_name`,
      params: [{ name: 'keyword', type: 'text', label: '关键词' }]
    },

    // ---- 健身目标列表 ----
    {
      id: 'fitness-goals-list',
      label: '健身目标',
      sql: `SELECT id, name, goal_type, exercise_type, target_unit, target_value,
                    start_date, end_date, status, note, created_at
            FROM fitness_goals
            ORDER BY created_at DESC`,
      params: []
    },

    // ---- 睡眠记录 ----
    {
      id: 'sleep-records',
      label: '睡眠记录',
      sql: `SELECT id, date, sleep_hours, bedtime, wake_time, note
            FROM sleep_records
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            ORDER BY date DESC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ]
    },

    // ---- 睡眠时长趋势 ----
    {
      id: 'sleep-trend',
      label: '睡眠时长趋势',
      sql: `SELECT date, sleep_hours
            FROM sleep_records
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            ORDER BY date ASC`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' }
      ],
      chartType: 'line',
      chartConfig: { colorScheme: ['#7950f2'] }
    },

    // ---- 热量炸弹榜 ----
    {
      id: 'food-ranking-high-cal',
      label: '热量炸弹榜',
      sql: `SELECT food_name,
                    SUM(calories)  AS total_cal,
                    SUM(grams)     AS total_grams,
                    SUM(protein)   AS total_pro,
                    SUM(carbs)     AS total_carbs,
                    SUM(fat)       AS total_fat,
                    COUNT(*)       AS eat_count
            FROM entries
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            GROUP BY food_name
            ORDER BY total_cal DESC
            LIMIT {{top_n}}`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' },
        { name: 'top_n',      type: 'text', label: 'Top N', default: '10' }
      ]
    },

    // ---- 低热量健康榜 ----
    {
      id: 'food-ranking-low-cal',
      label: '低热量健康榜',
      sql: `SELECT food_name,
                    SUM(calories) AS total_cal,
                    ROUND(SUM(calories) * 1.0 / COUNT(*), 0) AS avg_cal_per_time,
                    COUNT(*) AS eat_count
            FROM entries
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            GROUP BY food_name
            HAVING COUNT(*) >= 2
            ORDER BY avg_cal_per_time ASC
            LIMIT {{top_n}}`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' },
        { name: 'top_n',      type: 'text', label: 'Top N', default: '10' }
      ]
    },

    // ---- 频繁吃榜 ----
    {
      id: 'food-ranking-frequent',
      label: '频繁吃榜',
      sql: `SELECT food_name,
                    COUNT(*)       AS eat_count,
                    SUM(calories)  AS total_cal,
                    ROUND(SUM(calories) * 1.0 / COUNT(*), 0) AS avg_cal
            FROM entries
            WHERE date >= '{{start_date}}' AND date <= '{{end_date}}'
            GROUP BY food_name
            ORDER BY eat_count DESC
            LIMIT {{top_n}}`,
      params: [
        { name: 'start_date', type: 'date', label: '开始日期' },
        { name: 'end_date',   type: 'date', label: '结束日期' },
        { name: 'top_n',      type: 'text', label: 'Top N', default: '10' }
      ]
    }
  ],

  // ============================================================
  // ACTIONS
  // ============================================================
  actions: [

    // --- entries ---
    {
      id: 'add-entry',
      label: '添加饮食记录',
      type: 'insert',
      targetTable: 'entries',
      fields: [
        { field: 'date',      required: true, source: 'auto',  value: "date('now')" },
        { field: 'time',      source: 'auto',  value: "time('now')" },
        { field: 'food_name', required: true, source: 'user-input', prompt: '输入食物名称' },
        { field: 'grams',     required: true, source: 'user-input', prompt: '输入重量（克）', unit: '克' },
        { field: 'calories', required: true, source: 'user-input', prompt: '输入热量（千卡）', unit: '千卡' },
        { field: 'protein',  source: 'user-input', prompt: '输入蛋白质（克）', unit: '克' },
        { field: 'carbs',    source: 'user-input', prompt: '输入碳水（克）', unit: '克' },
        { field: 'fat',      source: 'user-input', prompt: '输入脂肪（克）', unit: '克' },
        { field: 'note',     source: 'user-input', prompt: '备注（可选）' }
      ]
    },
    {
      id: 'delete-entry',
      label: '删除饮食记录',
      type: 'delete',
      targetTable: 'entries',
      fields: [
        { field: 'id', required: true, source: 'user-input', prompt: '输入记录ID' }
      ]
    },

    // --- daily_goal ---
    {
      id: 'set-daily-goal',
      label: '设置每日目标',
      type: 'insert',
      targetTable: 'daily_goal',
      fields: [
        { field: 'id',              required: true, source: 'fixed', value: '1' },
        { field: 'calorie_goal',    required: true, source: 'user-input', prompt: '每日热量目标（千卡）', unit: '千卡' },
        { field: 'protein_goal',    source: 'user-input', prompt: '蛋白质目标（克）', unit: '克' },
        { field: 'carbs_goal',      source: 'user-input', prompt: '碳水目标（克）', unit: '克' },
        { field: 'fat_goal',        source: 'user-input', prompt: '脂肪目标（克）', unit: '克' }
      ]
    },
    {
      id: 'set-weight-goal',
      label: '设置体重目标',
      type: 'update',
      targetTable: 'daily_goal',
      fields: [
        { field: 'id',            required: true, source: 'fixed', value: '1' },
        { field: 'weight_goal',   required: true, source: 'user-input', prompt: '目标体重（公斤）', unit: '公斤' },
        { field: 'goal_deadline', source: 'user-input', prompt: '目标截止日期（YYYY-MM-DD）', format: 'date' }
      ]
    },

    // --- weight_log ---
    {
      id: 'add-weight',
      label: '记录体重',
      type: 'insert',
      targetTable: 'weight_log',
      fields: [
        { field: 'date',       required: true, source: 'auto',  value: "date('now')" },
        { field: 'time',       source: 'auto',  value: "time('now')" },
        { field: 'weight_kg', required: true, source: 'user-input', prompt: '输入体重（公斤）', unit: '公斤' },
        { field: 'height_cm', source: 'user-input', prompt: '身高（厘米）', unit: '厘米' },
        { field: 'note',      source: 'user-input', prompt: '备注（可选）' }
      ]
    },

    // --- exercise_log ---
    {
      id: 'add-exercise',
      label: '记录运动',
      type: 'insert',
      targetTable: 'exercise_log',
      fields: [
        { field: 'date',              required: true, source: 'auto',  value: "date('now')" },
        { field: 'time',             source: 'auto',  value: "time('now')" },
        { field: 'exercise_type',    required: true, source: 'user-input', prompt: '运动类型（如骑行/跑步/俯卧撑）' },
        { field: 'duration_minutes', source: 'user-input', prompt: '运动时长（分钟）', unit: '分钟' },
        { field: 'calories_burned',  required: true, source: 'user-input', prompt: '消耗热量（千卡）', unit: '千卡' },
        { field: 'reps',             source: 'user-input', prompt: '动作次数（如俯卧撑个数）' },
        { field: 'note',             source: 'user-input', prompt: '备注（可选）' }
      ]
    },

    // --- nutrition_products ---
    {
      id: 'add-product',
      label: '添加营养成分',
      type: 'insert',
      targetTable: 'nutrition_products',
      fields: [
        { field: 'product_name',   required: true, source: 'user-input', prompt: '产品名称' },
        { field: 'brand',          source: 'user-input', prompt: '品牌（可选）' },
        { field: 'calories',      required: true, source: 'user-input', prompt: '热量（千卡/100g）', unit: '千卡/100g' },
        { field: 'protein',        required: true, source: 'user-input', prompt: '蛋白质（克/100g）', unit: '克/100g' },
        { field: 'fat',            required: true, source: 'user-input', prompt: '脂肪（克/100g）', unit: '克/100g' },
        { field: 'saturated_fat',  source: 'user-input', prompt: '饱和脂肪（克/100g）', unit: '克/100g' },
        { field: 'carbohydrates', required: true, source: 'user-input', prompt: '碳水化合物（克/100g）', unit: '克/100g' },
        { field: 'sugar',         source: 'user-input', prompt: '糖（克/100g）', unit: '克/100g' },
        { field: 'dietary_fiber', source: 'user-input', prompt: '膳食纤维（克/100g）', unit: '克/100g' },
        { field: 'sodium',       required: true, source: 'user-input', prompt: '钠（毫克/100g）', unit: '毫克/100g' },
        { field: 'note',          source: 'user-input', prompt: '备注（可选）' }
      ]
    },
    {
      id: 'update-product',
      label: '更新营养成分',
      type: 'update',
      targetTable: 'nutrition_products',
      fields: [
        { field: 'id',            required: true, source: 'user-input', prompt: '输入产品ID' },
        { field: 'product_name',  source: 'user-input', prompt: '产品名称' },
        { field: 'brand',         source: 'user-input', prompt: '品牌' },
        { field: 'calories',       source: 'user-input', prompt: '热量（千卡/100g）', unit: '千卡/100g' },
        { field: 'protein',        source: 'user-input', prompt: '蛋白质（克/100g）', unit: '克/100g' },
        { field: 'fat',            source: 'user-input', prompt: '脂肪（克/100g）', unit: '克/100g' },
        { field: 'carbohydrates', source: 'user-input', prompt: '碳水化合物（克/100g）', unit: '克/100g' },
        { field: 'note',          source: 'user-input', prompt: '备注' }
      ]
    },

    // --- fitness_goals ---
    {
      id: 'add-fitness-goal',
      label: '添加健身目标',
      type: 'insert',
      targetTable: 'fitness_goals',
      fields: [
        { field: 'name',           required: true, source: 'user-input', prompt: '目标名称（如每日俯卧撑）' },
        { field: 'goal_type',      required: true, source: 'user-input', prompt: '目标类型',
          options: ['daily', 'weekly', 'monthly', 'longterm'] },
        { field: 'exercise_type',  required: true, source: 'user-input', prompt: '运动类型' },
        { field: 'target_unit',    required: true, source: 'user-input', prompt: '单位（如个/分钟/公里）' },
        { field: 'target_value', required: true, source: 'user-input', prompt: '目标值' },
        { field: 'start_date',    required: true, source: 'user-input', prompt: '开始日期（YYYY-MM-DD）', format: 'date' },
        { field: 'end_date',      source: 'user-input', prompt: '截止日期（YYYY-MM-DD，可选）', format: 'date' },
        { field: 'status',        source: 'fixed', value: 'active' },
        { field: 'note',          source: 'user-input', prompt: '备注（可选）' }
      ]
    },
    {
      id: 'update-fitness-goal',
      label: '更新健身目标',
      type: 'update',
      targetTable: 'fitness_goals',
      fields: [
        { field: 'id',             required: true, source: 'user-input', prompt: '输入目标ID' },
        { field: 'name',           source: 'user-input', prompt: '目标名称' },
        { field: 'target_value',   source: 'user-input', prompt: '目标值' },
        { field: 'status',         source: 'user-input', prompt: '状态',
          options: ['active', 'paused'] },
        { field: 'note',            source: 'user-input', prompt: '备注' }
      ]
    },
    {
      id: 'delete-fitness-goal',
      label: '删除健身目标',
      type: 'delete',
      targetTable: 'fitness_goals',
      fields: [
        { field: 'id', required: true, source: 'user-input', prompt: '输入目标ID' }
      ]
    },

    // --- sleep_records ---
    {
      id: 'add-sleep',
      label: '添加睡眠记录',
      type: 'insert',
      targetTable: 'sleep_records',
      fields: [
        { field: 'date',        required: true, source: 'user-input', prompt: '就寝日期（YYYY-MM-DD，归属于就寝日）', format: 'date' },
        { field: 'sleep_hours',  required: true, source: 'user-input', prompt: '睡眠时长（小时）', unit: '小时' },
        { field: 'bedtime',       source: 'user-input', prompt: '就寝时间（HH:MM）' },
        { field: 'wake_time',    source: 'user-input', prompt: '起床时间（HH:MM）' },
        { field: 'note',         source: 'user-input', prompt: '备注（可选）' }
      ]
    },
    {
      id: 'update-sleep',
      label: '更新睡眠记录',
      type: 'update',
      targetTable: 'sleep_records',
      fields: [
        { field: 'date',        required: true, source: 'user-input', prompt: '就寝日期（YYYY-MM-DD）' },
        { field: 'sleep_hours',  source: 'user-input', prompt: '睡眠时长（小时）', unit: '小时' },
        { field: 'bedtime',      source: 'user-input', prompt: '就寝时间（HH:MM）' },
        { field: 'wake_time',   source: 'user-input', prompt: '起床时间（HH:MM）' },
        { field: 'note',         source: 'user-input', prompt: '备注' }
      ]
    }
  ],

  // ============================================================
  // VIEWS
  // ============================================================
  views: [

    // ---- 每日记录 ----
    {
      id: 'daily',
      label: '每日记录',
      icon: 'CalendarBlank',
      components: {
        table: { queryId: 'daily-entries', sortable: true, pageSize: 20 },
        form:  { actionId: 'add-entry' }
      }
    },

    // ---- 每日摘要 ----
    {
      id: 'daily-summary',
      label: '每日摘要',
      icon: 'ChartPieSlice',
      components: {
        chart: { queryId: 'daily-summary' }
      }
    },

    // ---- 营养素占比 ----
    {
      id: 'macro-ratio',
      label: '营养素占比',
      icon: 'ChartBar',
      components: {
        chart: { queryId: 'macro-ratio-history' }
      }
    },

    // ---- 体重追踪 ----
    {
      id: 'weight',
      label: '体重追踪',
      icon: 'Scale',
      components: {
        table: { queryId: 'weight-history', sortable: true, pageSize: 30 },
        chart: { queryId: 'weight-history' },
        form:  { actionId: 'add-weight' }
      }
    },

    // ---- 体重目标 ----
    {
      id: 'weight-goal',
      label: '体重目标',
      icon: 'Target',
      components: {
        table: { queryId: 'weight-goal-progress' },
        form:  { actionId: 'set-weight-goal' }
      }
    },

    // ---- 运动记录 ----
    {
      id: 'exercise',
      label: '运动记录',
      icon: 'Barbell',
      components: {
        table: { queryId: 'exercise-log', sortable: true, pageSize: 20 },
        form:  { actionId: 'add-exercise' }
      }
    },

    // ---- 运动汇总 ----
    {
      id: 'exercise-summary',
      label: '运动汇总',
      icon: 'ChartLineUp',
      components: {
        chart: { queryId: 'exercise-summary' }
      }
    },

    // ---- 运动类型分布 ----
    {
      id: 'exercise-type',
      label: '运动类型分布',
      icon: 'PieChart',
      components: {
        chart: { queryId: 'exercise-type-breakdown' }
      }
    },

    // ---- 热量趋势 ----
    {
      id: 'calorie-trend',
      label: '热量趋势',
      icon: 'Fire',
      components: {
        chart: { queryId: 'calorie-history' }
      }
    },

    // ---- 热量缺口 ----
    {
      id: 'calorie-deficit',
      label: '热量缺口',
      icon: 'TrendDown',
      components: {
        chart: { queryId: 'calorie-deficit' }
      }
    },

    // ---- 热量炸弹榜 ----
    {
      id: 'food-ranking-high-cal',
      label: '热量炸弹榜',
      icon: 'Trophy',
      components: {
        table: { queryId: 'food-ranking-high-cal', pageSize: 10 }
      }
    },

    // ---- 频繁吃榜 ----
    {
      id: 'food-ranking-frequent',
      label: '频繁吃榜',
      icon: 'Star',
      components: {
        table: { queryId: 'food-ranking-frequent', pageSize: 10 }
      }
    },

    // ---- 每日目标 ----
    {
      id: 'goal',
      label: '每日目标',
      icon: 'Flag',
      components: {
        form: { actionId: 'set-daily-goal' }
      }
    },

    // ---- 食品营养库 ----
    {
      id: 'products',
      label: '食品营养库',
      icon: 'Cookie',
      components: {
        table: { queryId: 'product-list', sortable: true, pageSize: 20 },
        form:  { actionId: 'add-product' }
      }
    },

    // ---- 健身目标 ----
    {
      id: 'fitness-goals',
      label: '健身目标',
      icon: 'Medal',
      components: {
        table: { queryId: 'fitness-goals-list', pageSize: 20 },
        form:  { actionId: 'add-fitness-goal' }
      }
    },

    // ---- 睡眠记录 ----
    {
      id: 'sleep',
      label: '睡眠记录',
      icon: 'Moon',
      components: {
        table: { queryId: 'sleep-records', sortable: true, pageSize: 14 },
        chart: { queryId: 'sleep-trend' },
        form:  { actionId: 'add-sleep' }
      }
    }
  ]
}