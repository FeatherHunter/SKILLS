/**
 * SkillBoard Config - 私家大厨
 * 食谱管理专家：录入、查看、做菜、搜索、修改、烹饪历史、采购清单
 *
 * 数据库文件: chef_data.db
 * 包含17张表: recipes | recipe_categories | recipe_seasons | recipe_cooking_methods |
 *             recipe_flavors | recipe_diet_tags | recipe_meal_types | ingredients |
 *             cooking_steps | step_ingredients | step_techniques | tips |
 *             recipe_history | background_knowledge | recipe_relations | cookware | nutrition_info
 *
 * AI使用规范：所有数据操作必须通过 CLI，禁止直连数据库
 * 关键约束：
 *   - recipe_manager.py show / shopping_manager.py generate 返回的是格式化文本/JSON，
 *     不是普通 SQL 行列数据，前端需要特殊渲染模式
 *   - 废弃食谱用 discard（status='已废弃'），不物理删除
 *   - 多值字段全部用关联表，不存 JSON 数组
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
  params?: {
    name: string
    type: "date" | "month" | "year" | "range" | "text" | "select"
    label: string
    default?: string
    options?: { label: string; value: string }[]
  }[]
  chartType?: "bar" | "line" | "pie" | "doughnut" | "radar"
  chartConfig?: {
    stack?: boolean
    horizontal?: boolean
    colorScheme?: string[]
  }
}

type ActionDef = {
  id: string
  label: string
  type: "insert" | "update" | "delete"
  targetTable: string
  fields: {
    field: string
    required?: boolean
    default?: string
    source: "fixed" | "user-input" | "auto"
    value?: string
    prompt?: string
    format?: string
    unit?: string
    options?: string[]
  }[]
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

// ══════════════════════════════════════════════════════════════
// 导出配置
// ══════════════════════════════════════════════════════════════
export const ChefCookbookConfig: SkillConfig = {

  // ──────────────────────────────────────────────────────────
  // 1. meta（元数据）
  // ──────────────────────────────────────────────────────────
  meta: {
    name: "chef-cookbook",
    label: "私家大厨",
    icon: "ForkKnife",
    description: "食谱管理专家：录入、查看、做菜、搜索、修改、烹饪历史、采购清单",
    dbFiles: ["chef_data.db"]
  },

  // ──────────────────────────────────────────────────────────
  // 2. schema（数据库结构）— 17张表全覆盖
  // ──────────────────────────────────────────────────────────
  schema: {
    tables: [

      // ▸ 表1：recipes — 食谱主表
      {
        name: "recipes",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "name", type: "TEXT", label: "菜名", nullable: false },
          { name: "description", type: "TEXT", label: "描述" },
          { name: "difficulty", type: "TEXT", label: "难度", options: ["快手菜", "简单", "中等", "困难", "大师"] },
          { name: "servings", type: "INTEGER", label: "份量", unit: "人份" },
          { name: "total_time_minutes", type: "INTEGER", label: "总时间", unit: "分钟", format: "number" },
          { name: "status", type: "TEXT", label: "状态", options: ["未做", "已做", "熟练", "已废弃"] },
          { name: "photo_url", type: "TEXT", label: "照片" },
          { name: "source", type: "TEXT", label: "来源" },
          { name: "source_url", type: "TEXT", label: "来源链接" },
          { name: "created_at", type: "TEXT", label: "创建时间", format: "datetime" },
          { name: "updated_at", type: "TEXT", label: "更新时间", format: "datetime" }
        ]
      },

      // ▸ 表2：recipe_categories — 分类（菜系/地区/国家）
      {
        name: "recipe_categories",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "cuisine_type", type: "TEXT", label: "菜系", options: ["川菜", "粤菜", "湘菜", "闽菜", "浙菜", "苏菜", "鲁菜", "东北菜", "京菜", "沪菜", "台湾菜"] },
          { name: "region", type: "TEXT", label: "地区" },
          { name: "country", type: "TEXT", label: "国家" }
        ]
      },

      // ▸ 表3：recipe_seasons — 适合季节
      {
        name: "recipe_seasons",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "season", type: "TEXT", label: "季节", options: ["春", "夏", "秋", "冬"] }
        ]
      },

      // ▸ 表4：recipe_cooking_methods — 烹饪方式
      {
        name: "recipe_cooking_methods",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "method", type: "TEXT", label: "烹饪方式", options: ["炒", "蒸", "煮", "烤", "炸", "煎", "焖", "炖", "拌", "卤", "熏", "生食"] }
        ]
      },

      // ▸ 表5：recipe_flavors — 口味
      {
        name: "recipe_flavors",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "flavor", type: "TEXT", label: "口味", options: ["酸", "甜", "辣", "咸", "鲜", "苦", "麻"] }
        ]
      },

      // ▸ 表6：recipe_diet_tags — 饮食标签
      {
        name: "recipe_diet_tags",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "tag", type: "TEXT", label: "饮食标签", options: ["素食", "清真", "无辣", "低碳", "无糖", "低脂", "无麸质", "高蛋白"] }
        ]
      },

      // ▸ 表7：recipe_meal_types — 用餐类型
      {
        name: "recipe_meal_types",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "meal_type", type: "TEXT", label: "用餐类型", options: ["早", "中", "晚", "夜宵", "下午茶", "聚会"] }
        ]
      },

      // ▸ 表8：ingredients — 食材清单
      {
        name: "ingredients",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "sequence", type: "INTEGER", label: "顺序" },
          { name: "name", type: "TEXT", label: "食材名称", nullable: false },
          { name: "category", type: "TEXT", label: "分类", options: ["肉类", "海鲜", "蔬菜", "调料", "豆制品", "蛋类", "主食", "干货", "其他"] },
          { name: "quantity", type: "REAL", label: "用量", format: "number" },
          { name: "unit", type: "TEXT", label: "单位", options: ["g", "kg", "ml", "L", "个", "勺", "把", "茶匙", "杯", "段", "瓣"] },
          { name: "quantity_text", type: "TEXT", label: "用量文字" },
          { name: "is_optional", type: "INTEGER", label: "可选", format: "number" },
          { name: "substitute", type: "TEXT", label: "替代食材" }
        ]
      },

      // ▸ 表9：cooking_steps — 烹饪步骤
      {
        name: "cooking_steps",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "sequence", type: "INTEGER", label: "步骤序号", nullable: false },
          { name: "action", type: "TEXT", label: "操作动作", nullable: false },
          { name: "duration_minutes", type: "INTEGER", label: "时长", unit: "分钟", format: "number" },
          { name: "heat_level", type: "TEXT", label: "火候", options: ["微火", "小火", "中火", "大火", "猛火"] },
          { name: "temperature", type: "TEXT", label: "温度" },
          { name: "expected_result", type: "TEXT", label: "预期效果" }
        ]
      },

      // ▸ 表10：step_ingredients — 步骤×食材关联
      {
        name: "step_ingredients",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "step_id", type: "TEXT", label: "步骤ID", nullable: false },
          { name: "ingredient_id", type: "TEXT", label: "食材ID", nullable: false },
          { name: "quantity_used", type: "REAL", label: "步骤中使用量", format: "number" },
          { name: "introduced_at", type: "TEXT", label: "引入时机" }
        ]
      },

      // ▸ 表11：step_techniques — 步骤技法
      {
        name: "step_techniques",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "step_id", type: "TEXT", label: "步骤ID", nullable: false },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "technique_name", type: "TEXT", label: "技法名称", nullable: false },
          { name: "description", type: "TEXT", label: "技法解释" },
          { name: "key_points", type: "TEXT", label: "关键要点" }
        ]
      },

      // ▸ 表12：tips — 小贴士
      {
        name: "tips",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "step_id", type: "TEXT", label: "关联步骤ID" },
          { name: "ingredient_id", type: "TEXT", label: "关联食材ID" },
          { name: "category", type: "TEXT", label: "分类", options: ["火候", "刀工", "调味", "采购", "设备", "保存", "文化"] },
          { name: "content", type: "TEXT", label: "内容", nullable: false },
          { name: "priority", type: "INTEGER", label: "优先级" }
        ]
      },

      // ▸ 表13：recipe_history — 烹饪历史
      {
        name: "recipe_history",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "cook_date", type: "TEXT", label: "烹饪日期", format: "date", nullable: false },
          { name: "cook_sequence", type: "INTEGER", label: "第几次做" },
          { name: "rating", type: "REAL", label: "评分", format: "number" },
          { name: "feedback", type: "TEXT", label: "反馈" }
        ]
      },

      // ▸ 表14：background_knowledge — 背景知识
      {
        name: "background_knowledge",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "origin_story", type: "TEXT", label: "起源故事" },
          { name: "historical_background", type: "TEXT", label: "历史背景" },
          { name: "cultural_significance", type: "TEXT", label: "文化意义" }
        ]
      },

      // ▸ 表15：recipe_relations — 食谱派生关系
      {
        name: "recipe_relations",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "parent_id", type: "TEXT", label: "父食谱ID", nullable: false },
          { name: "child_id", type: "TEXT", label: "子食谱ID", nullable: false },
          { name: "relation_type", type: "TEXT", label: "关系类型", options: ["派生", "变体", "改良"] },
          { name: "change_summary", type: "TEXT", label: "变更说明" }
        ]
      },

      // ▸ 表16：cookware — 炊具设备
      {
        name: "cookware",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "name", type: "TEXT", label: "炊具名称", nullable: false },
          { name: "category", type: "TEXT", label: "分类", options: ["锅", "炉", "刀", "其他"] }
        ]
      },

      // ▸ 表17：nutrition_info — 营养信息
      {
        name: "nutrition_info",
        fields: [
          { name: "id", type: "TEXT", label: "ID", primaryKey: true },
          { name: "recipe_id", type: "TEXT", label: "食谱ID", nullable: false },
          { name: "serving_size", type: "REAL", label: "每份份量", format: "number" },
          { name: "serving_unit", type: "TEXT", label: "每份单位" },
          { name: "calories", type: "INTEGER", label: "热量", unit: "kcal", format: "number" },
          { name: "protein", type: "REAL", label: "蛋白质", unit: "g", format: "number" },
          { name: "fat", type: "REAL", label: "脂肪", unit: "g", format: "number" },
          { name: "carbs", type: "REAL", label: "碳水", unit: "g", format: "number" },
          { name: "fiber", type: "REAL", label: "膳食纤维", unit: "g", format: "number" },
          { name: "sodium", type: "REAL", label: "钠", unit: "mg", format: "number" }
        ]
      }
    ]
  },

  // ──────────────────────────────────────────────────────────
  // 3. queries（预设查询）
  // 数据库：chef_data.db（全部使用同一数据库文件）
  //
  // ⚠️ 重要约束：
  //   - recipe-detail: 调用 recipe_manager.py show 返回格式化文本，
  //     前端需要"CLI输出展示"模式（非普通表格）
  //   - shopping-list: 调用 shopping_manager.py generate 返回嵌套JSON，
  //     前端需要特殊渲染处理
  // ──────────────────────────────────────────────────────────
  queries: [

    // Q1：食谱列表（首页默认）— 标准表格
    {
      id: "recipe-list",
      label: "食谱列表",
      sql: "SELECT id, name, difficulty, total_time_minutes, servings, status FROM recipes WHERE status != '已废弃' ORDER BY name",
      params: []
    },

    // Q2：食谱详情 — ⚠️ 返回格式化文本，前端需特殊展示模式
    {
      id: "recipe-detail",
      label: "食谱详情",
      sql: "SELECT * FROM recipes WHERE (id = '{{id}}' OR name LIKE '%{{id}}%') AND status != '已废弃'",
      params: [
        { name: "id", type: "text", label: "菜名或ID" }
      ]
    },

    // Q3：搜索食谱（按菜名/食材关键词）— 标准表格
    {
      id: "recipe-search",
      label: "搜索食谱",
      sql: "SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, r.status FROM recipes r LEFT JOIN ingredients i ON r.id = i.recipe_id WHERE (r.name LIKE '%{{keyword}}%' OR i.name LIKE '%{{keyword}}%') AND r.status != '已废弃' ORDER BY r.name",
      params: [
        { name: "keyword", type: "text", label: "关键词" }
      ]
    },

    // Q4：采购清单 — 前端将 recipe_ids 分割后用 LIKE 逐条查询
    // ⚠️ 注意：单个 recipe_id 参数由前端自行拼接为多条查询
    {
      id: "shopping-list",
      label: "采购清单（单食谱）",
      sql: "SELECT recipe_id, name, servings FROM recipes WHERE id = '{{recipe_id}}' AND status != '已废弃'",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q5：烹饪历史（某食谱的全部历史记录）— 标准表格
    {
      id: "cooking-history",
      label: "烹饪历史",
      sql: "SELECT rh.id, rh.recipe_id, r.name as recipe_name, rh.cook_date, rh.cook_sequence, rh.rating, rh.feedback FROM recipe_history rh JOIN recipes r ON rh.recipe_id = r.id WHERE rh.recipe_id = '{{recipe_id}}' ORDER BY rh.cook_date DESC",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q6：烹饪统计（次数/评分汇总）— 直接显示数值
    {
      id: "cooking-stats",
      label: "烹饪统计",
      sql: "SELECT COUNT(*) as times, AVG(rating) as avg_rating, MAX(cook_sequence) as max_seq FROM recipe_history WHERE recipe_id = '{{recipe_id}}'",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q7：按菜系筛选 — 标准表格
    {
      id: "recipe-by-cuisine",
      label: "按菜系筛选",
      sql: "SELECT r.id, r.name, r.difficulty, r.total_time_minutes, r.status FROM recipes r JOIN recipe_categories rc ON r.id = rc.recipe_id WHERE rc.cuisine_type = '{{cuisine}}' AND r.status != '已废弃' ORDER BY r.name",
      params: [
        {
          name: "cuisine", type: "select", label: "菜系",
          options: [
            { label: "川菜", value: "川菜" },
            { label: "粤菜", value: "粤菜" },
            { label: "湘菜", value: "湘菜" },
            { label: "闽菜", value: "闽菜" },
            { label: "浙菜", value: "浙菜" },
            { label: "苏菜", value: "苏菜" },
            { label: "鲁菜", value: "鲁菜" },
            { label: "东北菜", value: "东北菜" },
            { label: "京菜", value: "京菜" },
            { label: "沪菜", value: "沪菜" },
            { label: "台湾菜", value: "台湾菜" }
          ]
        }
      ]
    },

    // Q8：按食材搜索食谱 — 标准表格
    {
      id: "recipe-by-ingredient",
      label: "按食材搜索",
      sql: "SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, i.name as ingredient FROM recipes r JOIN ingredients i ON r.id = i.recipe_id WHERE i.name LIKE '%{{ingredient}}%' AND r.status != '已废弃' ORDER BY r.name",
      params: [
        { name: "ingredient", type: "text", label: "食材名称" }
      ]
    },

    // Q9：食材清单（某食谱的全部食材）— 标准表格
    {
      id: "ingredient-list",
      label: "食材清单",
      sql: "SELECT id, name, category, quantity, unit, quantity_text, is_optional, substitute FROM ingredients WHERE recipe_id = '{{recipe_id}}' ORDER BY sequence",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q10：步骤列表（某食谱的全部步骤）— 标准表格
    {
      id: "step-list",
      label: "步骤列表",
      sql: "SELECT id, sequence, action, duration_minutes, heat_level, temperature, expected_result FROM cooking_steps WHERE recipe_id = '{{recipe_id}}' ORDER BY sequence",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q11：营养信息 — 标准表格
    {
      id: "nutrition-info",
      label: "营养信息",
      sql: "SELECT id, serving_size, serving_unit, calories, protein, fat, carbs, fiber, sodium FROM nutrition_info WHERE recipe_id = '{{recipe_id}}'",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ]
    },

    // Q12：评分趋势 — 折线图
    {
      id: "rating-trend",
      label: "评分趋势",
      sql: "SELECT cook_date as label, rating as value FROM recipe_history WHERE recipe_id = '{{recipe_id}}' ORDER BY cook_date ASC",
      params: [
        { name: "recipe_id", type: "text", label: "食谱ID" }
      ],
      chartType: "line",
      chartConfig: {
        colorScheme: ["#4CAF50"]
      }
    }
  ],

  // ──────────────────────────────────────────────────────────
  // 4. actions（操作定义）
  // 私家大厨核心是展示型技能，以查看为主；
  // 写入操作（添加食谱/食材/步骤/历史）由 AI 通过 CLI 引导用户完成，
  // 此处 actions 主要用于 SkillBoard 面板内的快速操作入口。
  // ──────────────────────────────────────────────────────────
  actions: [

    // A1：添加食谱
    {
      id: "add-recipe",
      label: "录入食谱",
      type: "insert",
      targetTable: "recipes",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "name", required: true, source: "user-input", prompt: "菜名" },
        { field: "description", source: "user-input", prompt: "一句话描述（如：川菜经典，虾球Q弹）" },
        { field: "difficulty", source: "user-input", prompt: "难度", options: ["快手菜", "简单", "中等", "困难", "大师"] },
        { field: "servings", source: "user-input", prompt: "份量（人数）", format: "number" },
        { field: "total_time_minutes", source: "user-input", prompt: "总时间（分钟）", format: "number" },
        { field: "status", source: "fixed", value: "未做" },
        { field: "source", source: "user-input", prompt: "来源（如：中餐厅节目）" },
        { field: "source_url", source: "user-input", prompt: "原始食谱链接" },
        { field: "created_at", source: "auto", value: "datetime('now')" },
        { field: "updated_at", source: "auto", value: "datetime('now')" }
      ]
    },

    // A2：更新食谱主信息
    {
      id: "update-recipe",
      label: "修改食谱",
      type: "update",
      targetTable: "recipes",
      fields: [
        { field: "name", source: "user-input", prompt: "新菜名" },
        { field: "description", source: "user-input", prompt: "新描述" },
        { field: "difficulty", source: "user-input", prompt: "新难度", options: ["快手菜", "简单", "中等", "困难", "大师"] },
        { field: "servings", source: "user-input", prompt: "新份量", format: "number" },
        { field: "total_time_minutes", source: "user-input", prompt: "新总时间（分钟）", format: "number" },
        { field: "status", source: "user-input", prompt: "新状态", options: ["未做", "已做", "熟练"] },
        { field: "source", source: "user-input", prompt: "新来源" },
        { field: "updated_at", source: "auto", value: "datetime('now')" }
      ]
    },

    // A3：废弃食谱（标记为已废弃，不物理删除）
    {
      id: "discard-recipe",
      label: "废弃食谱",
      type: "update",
      targetTable: "recipes",
      fields: [
        { field: "status", required: true, source: "fixed", value: "已废弃" },
        { field: "updated_at", source: "auto", value: "datetime('now')" }
      ]
    },

    // A4：添加食材
    {
      id: "add-ingredient",
      label: "添加食材",
      type: "insert",
      targetTable: "ingredients",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "name", required: true, source: "user-input", prompt: "食材名称" },
        { field: "category", source: "user-input", prompt: "分类", options: ["肉类", "海鲜", "蔬菜", "调料", "豆制品", "蛋类", "主食", "干货", "其他"] },
        { field: "quantity", source: "user-input", prompt: "用量（数值）", format: "number" },
        { field: "unit", source: "user-input", prompt: "单位", options: ["g", "kg", "ml", "L", "个", "勺", "把", "茶匙", "杯", "段", "瓣"] },
        { field: "quantity_text", source: "user-input", prompt: "用量文字（如：适量、少许）" },
        { field: "is_optional", source: "user-input", prompt: "是否可选", options: ["否", "是"] },
        { field: "substitute", source: "user-input", prompt: "替代食材" },
        { field: "sequence", source: "auto", value: "auto_increment" }
      ]
    },

    // A5：添加步骤
    {
      id: "add-step",
      label: "添加步骤",
      type: "insert",
      targetTable: "cooking_steps",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "action", required: true, source: "user-input", prompt: "操作动作描述" },
        { field: "duration_minutes", source: "user-input", prompt: "时长（分钟）", format: "number" },
        { field: "heat_level", source: "user-input", prompt: "火候", options: ["微火", "小火", "中火", "大火", "猛火"] },
        { field: "temperature", source: "user-input", prompt: "温度（如：160度）" },
        { field: "expected_result", source: "user-input", prompt: "预期效果" },
        { field: "sequence", source: "auto", value: "auto_increment" }
      ]
    },

    // A6：记录烹饪历史
    {
      id: "add-cooking-history",
      label: "记录做菜",
      type: "insert",
      targetTable: "recipe_history",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "cook_date", source: "auto", value: "date('now')" },
        { field: "cook_sequence", source: "auto", value: "auto_increment_from_history" },
        { field: "rating", source: "user-input", prompt: "评分（1-5分）", format: "number" },
        { field: "feedback", source: "user-input", prompt: "做菜反馈/备注" }
      ]
    },

    // A7：更新烹饪记录
    {
      id: "update-cooking-history",
      label: "修改烹饪记录",
      type: "update",
      targetTable: "recipe_history",
      fields: [
        { field: "cook_date", source: "user-input", prompt: "烹饪日期", format: "date" },
        { field: "rating", source: "user-input", prompt: "新评分（1-5分）", format: "number" },
        { field: "feedback", source: "user-input", prompt: "新反馈" }
      ]
    },

    // A8：添加分类（菜系/地区/国家）
    {
      id: "add-category",
      label: "添加分类",
      type: "insert",
      targetTable: "recipe_categories",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "cuisine_type", source: "user-input", prompt: "菜系", options: ["川菜", "粤菜", "湘菜", "闽菜", "浙菜", "苏菜", "鲁菜", "东北菜", "京菜", "沪菜", "台湾菜"] },
        { field: "region", source: "user-input", prompt: "地区" },
        { field: "country", source: "user-input", prompt: "国家" }
      ]
    },

    // A9：更新步骤
    {
      id: "update-step",
      label: "修改步骤",
      type: "update",
      targetTable: "cooking_steps",
      fields: [
        { field: "action", source: "user-input", prompt: "新操作动作" },
        { field: "duration_minutes", source: "user-input", prompt: "新时长（分钟）", format: "number" },
        { field: "heat_level", source: "user-input", prompt: "新火候", options: ["微火", "小火", "中火", "大火", "猛火"] },
        { field: "temperature", source: "user-input", prompt: "新温度" },
        { field: "expected_result", source: "user-input", prompt: "新预期效果" }
      ]
    },

    // A10：添加小贴士
    {
      id: "add-tip",
      label: "添加小贴士",
      type: "insert",
      targetTable: "tips",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "step_id", source: "user-input", prompt: "关联步骤ID（可选）" },
        { field: "ingredient_id", source: "user-input", prompt: "关联食材ID（可选）" },
        { field: "category", source: "user-input", prompt: "分类", options: ["火候", "刀工", "调味", "采购", "设备", "保存", "文化"] },
        { field: "content", required: true, source: "user-input", prompt: "小贴士内容" },
        { field: "priority", source: "user-input", prompt: "优先级（数字越小越重要）", format: "number" }
      ]
    },

    // A11：添加营养信息
    {
      id: "add-nutrition",
      label: "添加营养信息",
      type: "insert",
      targetTable: "nutrition_info",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "serving_size", source: "user-input", prompt: "每份份量（数值）", format: "number" },
        { field: "serving_unit", source: "user-input", prompt: "每份单位" },
        { field: "calories", source: "user-input", prompt: "热量（kcal）", format: "number" },
        { field: "protein", source: "user-input", prompt: "蛋白质（g）", format: "number" },
        { field: "fat", source: "user-input", prompt: "脂肪（g）", format: "number" },
        { field: "carbs", source: "user-input", prompt: "碳水（g）", format: "number" },
        { field: "fiber", source: "user-input", prompt: "膳食纤维（g）", format: "number" },
        { field: "sodium", source: "user-input", prompt: "钠（mg）", format: "number" }
      ]
    },

    // A12：添加炊具
    {
      id: "add-cookware",
      label: "添加炊具",
      type: "insert",
      targetTable: "cookware",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "name", required: true, source: "user-input", prompt: "炊具名称" },
        { field: "category", source: "user-input", prompt: "分类", options: ["锅", "炉", "刀", "其他"] }
      ]
    },

    // A13：添加背景知识
    {
      id: "add-background",
      label: "添加背景知识",
      type: "insert",
      targetTable: "background_knowledge",
      fields: [
        { field: "id", source: "auto", value: "uuid4()" },
        { field: "recipe_id", required: true, source: "user-input", prompt: "食谱ID" },
        { field: "origin_story", source: "user-input", prompt: "起源故事" },
        { field: "historical_background", source: "user-input", prompt: "历史背景" },
        { field: "cultural_significance", source: "user-input", prompt: "文化意义" }
      ]
    }
  ],

  // ──────────────────────────────────────────────────────────
  // 5. views（视图定义）— SkillBoard 面板子页面
  // ──────────────────────────────────────────────────────────
  views: [

    // V1：食谱列表（首页默认视图）— 标准表格
    {
      id: "recipe-list",
      label: "食谱列表",
      icon: "BookOpen",
      components: {
        table: {
          queryId: "recipe-list",
          columns: ["name", "difficulty", "total_time_minutes", "servings", "status"],
          sortable: true,
          pageSize: 20
        }
      }
    },

    // V2：搜索 — 标准表格
    {
      id: "recipe-search",
      label: "搜索",
      icon: "MagnifyingGlass",
      components: {
        table: {
          queryId: "recipe-search",
          columns: ["name", "difficulty", "total_time_minutes", "status"],
          sortable: true,
          pageSize: 20
        }
      }
    },

    // V3：菜系分类 — 标准表格
    {
      id: "recipe-by-cuisine",
      label: "菜系分类",
      icon: "Globe",
      components: {
        table: {
          queryId: "recipe-by-cuisine",
          columns: ["name", "difficulty", "total_time_minutes", "status"],
          sortable: true,
          pageSize: 20
        }
      }
    },

    // V4：食材搜索 — 标准表格
    {
      id: "recipe-by-ingredient",
      label: "食材搜索",
      icon: "Carrot",
      components: {
        table: {
          queryId: "recipe-by-ingredient",
          columns: ["name", "difficulty", "total_time_minutes", "ingredient"],
          sortable: true,
          pageSize: 20
        }
      }
    },

    // V5：录入新食谱 — 表单
    {
      id: "add-recipe",
      label: "录入新食谱",
      icon: "Plus",
      components: {
        form: {
          actionId: "add-recipe"
        }
      }
    },

    // V6：采购清单 — ⚠️ 需CLI+JSON特殊渲染
    {
      id: "shopping-list",
      label: "采购清单",
      icon: "ShoppingCart",
      components: {
        table: {
          queryId: "shopping-list",
          columns: ["recipe_id", "name", "servings"],
          sortable: false,
          pageSize: 50
        }
      }
    },

    // V7：烹饪历史 — 标准表格
    {
      id: "cooking-history",
      label: "烹饪历史",
      icon: "ClockCounterClockwise",
      components: {
        table: {
          queryId: "cooking-history",
          columns: ["recipe_name", "cook_date", "cook_sequence", "rating", "feedback"],
          sortable: true,
          pageSize: 20
        }
      }
    },

    // V8：评分趋势 — 图表
    {
      id: "cooking-stats",
      label: "烹饪统计",
      icon: "ChartLine",
      components: {
        chart: {
          queryId: "rating-trend"
        }
      }
    },

    // V9：营养信息 — 标准表格
    {
      id: "nutrition",
      label: "营养信息",
      icon: "Heart",
      components: {
        table: {
          queryId: "nutrition-info",
          columns: ["calories", "protein", "fat", "carbs", "fiber", "sodium"],
          sortable: false,
          pageSize: 10
        }
      }
    }
  ]
}