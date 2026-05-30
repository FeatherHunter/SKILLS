// 自动生成 by generate_ts_config.py
// 生成时间: 2026-05-23 12:51:58
// 表结构从数据库动态读取（方案三）
// queries/actions/views 由 AI 根据表能力设计

{
  "meta": {
    "name": "calorie",
    "label": "卡路里",
    "icon": "ForkKnife",
    "description": "热量与营养追踪，记录饮食、体重、运动、睡眠，支持每日目标和目标进度分析",
    "dbFiles": [
      "calorie_data.db"
    ]
  },
  "schema": {
    "tables": [
      {
        "name": "entries",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "date",
            "type": "string",
            "label": "Date",
            "format": "date",
            "editable": true
          },
          {
            "name": "time",
            "type": "string",
            "label": "Time",
            "format": "datetime",
            "visible": false,
            "editable": true
          },
          {
            "name": "food_name",
            "type": "string",
            "label": "Food name",
            "editable": true
          },
          {
            "name": "grams",
            "type": "number",
            "label": "Grams",
            "unit": "克",
            "editable": true
          },
          {
            "name": "calories",
            "type": "number",
            "label": "Calories",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "protein",
            "type": "number",
            "label": "Protein",
            "default": "0",
            "unit": "克",
            "editable": true
          },
          {
            "name": "carbs",
            "type": "number",
            "label": "Carbs",
            "default": "0",
            "unit": "克",
            "editable": true
          },
          {
            "name": "fat",
            "type": "number",
            "label": "Fat",
            "default": "0",
            "unit": "克",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "default": "''",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "string",
            "label": "Created at",
            "default": "CURRENT_TIMESTAMP",
            "format": "datetime",
            "visible": false,
            "editable": false
          }
        ]
      },
      {
        "name": "daily_goal",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "calorie_goal",
            "type": "number",
            "label": "Calorie goal",
            "default": "1800",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "protein_goal",
            "type": "number",
            "label": "Protein goal",
            "default": "150",
            "unit": "克",
            "editable": true
          },
          {
            "name": "carbs_goal",
            "type": "number",
            "label": "Carbs goal",
            "default": "200",
            "unit": "克",
            "editable": true
          },
          {
            "name": "fat_goal",
            "type": "number",
            "label": "Fat goal",
            "default": "60",
            "unit": "克",
            "editable": true
          },
          {
            "name": "updated_at",
            "type": "string",
            "label": "Updated at",
            "default": "CURRENT_TIMESTAMP",
            "format": "date",
            "editable": false
          },
          {
            "name": "weight_goal",
            "type": "number",
            "label": "Weight goal",
            "unit": "公斤",
            "editable": true
          },
          {
            "name": "goal_deadline",
            "type": "string",
            "label": "Goal deadline",
            "editable": true
          }
        ]
      },
      {
        "name": "weight_log",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "date",
            "type": "string",
            "label": "Date",
            "format": "date",
            "editable": true
          },
          {
            "name": "time",
            "type": "string",
            "label": "Time",
            "format": "datetime",
            "visible": false,
            "editable": true
          },
          {
            "name": "weight_kg",
            "type": "number",
            "label": "Weight kg",
            "unit": "公斤",
            "editable": true
          },
          {
            "name": "height_cm",
            "type": "number",
            "label": "Height cm",
            "unit": "厘米",
            "editable": true
          },
          {
            "name": "bmi",
            "type": "number",
            "label": "Bmi",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "default": "''",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "string",
            "label": "Created at",
            "default": "CURRENT_TIMESTAMP",
            "format": "datetime",
            "visible": false,
            "editable": false
          }
        ]
      },
      {
        "name": "nutrition_products",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "product_name",
            "type": "string",
            "label": "Product name",
            "editable": true
          },
          {
            "name": "brand",
            "type": "string",
            "label": "Brand",
            "editable": true
          },
          {
            "name": "calories",
            "type": "number",
            "label": "Calories",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "protein",
            "type": "number",
            "label": "Protein",
            "unit": "克",
            "editable": true
          },
          {
            "name": "fat",
            "type": "number",
            "label": "Fat",
            "unit": "克",
            "editable": true
          },
          {
            "name": "saturated_fat",
            "type": "number",
            "label": "Saturated fat",
            "unit": "克",
            "editable": true
          },
          {
            "name": "carbohydrates",
            "type": "number",
            "label": "Carbohydrates",
            "unit": "克",
            "editable": true
          },
          {
            "name": "sugar",
            "type": "number",
            "label": "Sugar",
            "editable": true
          },
          {
            "name": "dietary_fiber",
            "type": "number",
            "label": "Dietary fiber",
            "editable": true
          },
          {
            "name": "sodium",
            "type": "number",
            "label": "Sodium",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "default": "''",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "string",
            "label": "Created at",
            "default": "CURRENT_TIMESTAMP",
            "format": "datetime",
            "visible": false,
            "editable": false
          },
          {
            "name": "updated_at",
            "type": "string",
            "label": "Updated at",
            "default": "CURRENT_TIMESTAMP",
            "format": "date",
            "editable": false
          }
        ]
      },
      {
        "name": "exercise_log",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "date",
            "type": "string",
            "label": "Date",
            "format": "date",
            "editable": true
          },
          {
            "name": "time",
            "type": "string",
            "label": "Time",
            "format": "datetime",
            "visible": false,
            "editable": true
          },
          {
            "name": "exercise_type",
            "type": "string",
            "label": "Exercise type",
            "editable": true
          },
          {
            "name": "duration_minutes",
            "type": "number",
            "label": "Duration minutes",
            "unit": "分钟",
            "editable": true
          },
          {
            "name": "calories_burned",
            "type": "number",
            "label": "Calories burned",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "default": "''",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "string",
            "label": "Created at",
            "default": "CURRENT_TIMESTAMP",
            "format": "datetime",
            "visible": false,
            "editable": false
          },
          {
            "name": "reps",
            "type": "number",
            "label": "Reps",
            "unit": "个",
            "editable": true
          }
        ]
      },
      {
        "name": "fitness_goals",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "name",
            "type": "string",
            "label": "Name",
            "editable": true
          },
          {
            "name": "goal_type",
            "type": "string",
            "label": "Goal type",
            "editable": true
          },
          {
            "name": "exercise_type",
            "type": "string",
            "label": "Exercise type",
            "editable": true
          },
          {
            "name": "target_unit",
            "type": "string",
            "label": "Target unit",
            "editable": true
          },
          {
            "name": "target_value",
            "type": "number",
            "label": "Target value",
            "editable": true
          },
          {
            "name": "start_date",
            "type": "string",
            "label": "Start date",
            "format": "date",
            "editable": true
          },
          {
            "name": "end_date",
            "type": "string",
            "label": "End date",
            "format": "date",
            "editable": true
          },
          {
            "name": "status",
            "type": "string",
            "label": "Status",
            "default": "'active'",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "number",
            "label": "Created at",
            "format": "datetime",
            "visible": false,
            "editable": false
          },
          {
            "name": "updated_at",
            "type": "number",
            "label": "Updated at",
            "format": "date",
            "editable": false
          }
        ]
      },
      {
        "name": "sleep_records",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "date",
            "type": "string",
            "label": "Date",
            "format": "date",
            "editable": true
          },
          {
            "name": "sleep_hours",
            "type": "number",
            "label": "Sleep hours",
            "editable": true
          },
          {
            "name": "bedtime",
            "type": "string",
            "label": "Bedtime",
            "format": "time",
            "visible": true,
            "editable": true
          },
          {
            "name": "wake_time",
            "type": "string",
            "label": "Wake time",
            "format": "time",
            "visible": true,
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "number",
            "label": "Created at",
            "format": "datetime",
            "visible": false,
            "editable": false
          },
          {
            "name": "updated_at",
            "type": "number",
            "label": "Updated at",
            "format": "date",
            "editable": false
          }
        ]
      },
      {
        "name": "body_photos",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "date",
            "type": "string",
            "label": "Date",
            "format": "date",
            "editable": true
          },
          {
            "name": "time",
            "type": "string",
            "label": "Time",
            "format": "time",
            "editable": true
          },
          {
            "name": "photo_path",
            "type": "string",
            "label": "Photo path",
            "editable": true
          },
          {
            "name": "tag",
            "type": "string",
            "label": "Tag",
            "editable": true
          },
          {
            "name": "note",
            "type": "string",
            "label": "Note",
            "editable": true
          },
          {
            "name": "created_at",
            "type": "string",
            "label": "Created at",
            "default": "CURRENT_TIMESTAMP",
            "format": "datetime",
            "visible": false,
            "editable": false
          }
        ]
      }
    ]
  },
  "queries": [
    {
      "id": "entries-daily",
      "label": "今日饮食记录",
      "sql": "SELECT * FROM entries WHERE date = '{date}' ORDER BY time",
      "params": [
        {
          "name": "date",
          "type": "date",
          "label": "日期",
          "default": "TODAY"
        }
      ]
    },
    {
      "id": "entries-history",
      "label": "饮食记录历史",
      "sql": "SELECT * FROM entries ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "daily_goal-all",
      "label": "全部每日目标",
      "sql": "SELECT * FROM daily_goal ORDER BY id DESC",
      "params": []
    },
    {
      "id": "weight_log-daily",
      "label": "今日体重记录",
      "sql": "SELECT * FROM weight_log WHERE date = '{date}' ORDER BY time",
      "params": [
        {
          "name": "date",
          "type": "date",
          "label": "日期",
          "default": "TODAY"
        }
      ]
    },
    {
      "id": "weight_log-history",
      "label": "体重记录历史",
      "sql": "SELECT * FROM weight_log ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "nutrition_products-all",
      "label": "全部食品库",
      "sql": "SELECT * FROM nutrition_products ORDER BY id DESC",
      "params": []
    },
    {
      "id": "exercise_log-daily",
      "label": "今日运动记录",
      "sql": "SELECT * FROM exercise_log WHERE date = '{date}' ORDER BY time",
      "params": [
        {
          "name": "date",
          "type": "date",
          "label": "日期",
          "default": "TODAY"
        }
      ]
    },
    {
      "id": "exercise_log-history",
      "label": "运动记录历史",
      "sql": "SELECT * FROM exercise_log ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "fitness_goals-all",
      "label": "全部健身目标",
      "sql": "SELECT * FROM fitness_goals ORDER BY id DESC",
      "params": []
    },
    {
      "id": "sleep_records-daily",
      "label": "今日睡眠记录",
      "sql": "SELECT * FROM sleep_records WHERE date = '{date}' ORDER BY time",
      "params": [
        {
          "name": "date",
          "type": "date",
          "label": "日期",
          "default": "TODAY"
        }
      ]
    },
    {
      "id": "sleep_records-history",
      "label": "睡眠记录历史",
      "sql": "SELECT * FROM sleep_records ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "body_photos-daily",
      "label": "今日身材照片",
      "sql": "SELECT * FROM body_photos WHERE date = '{date}' ORDER BY time",
      "params": [
        {
          "name": "date",
          "type": "date",
          "label": "日期",
          "default": "TODAY"
        }
      ]
    },
    {
      "id": "body_photos-history",
      "label": "身材照片历史",
      "sql": "SELECT * FROM body_photos ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    }
  ],
  "actions": [
    {
      "id": "add-entries",
      "label": "添加饮食记录",
      "type": "insert",
      "targetTable": "entries",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "time",
          "required": false,
          "source": "user-input",
          "prompt": "Time"
        },
        {
          "field": "food_name",
          "required": false,
          "source": "user-input",
          "prompt": "Food name"
        },
        {
          "field": "grams",
          "required": false,
          "source": "user-input",
          "prompt": "Grams"
        },
        {
          "field": "calories",
          "required": false,
          "source": "user-input",
          "prompt": "Calories"
        },
        {
          "field": "protein",
          "required": false,
          "source": "user-input",
          "prompt": "Protein"
        },
        {
          "field": "carbs",
          "required": false,
          "source": "user-input",
          "prompt": "Carbs"
        },
        {
          "field": "fat",
          "required": false,
          "source": "user-input",
          "prompt": "Fat"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    },
    {
      "id": "add-daily_goal",
      "label": "添加每日目标",
      "type": "insert",
      "targetTable": "daily_goal",
      "fields": [
        {
          "field": "calorie_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Calorie goal"
        },
        {
          "field": "protein_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Protein goal"
        },
        {
          "field": "carbs_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Carbs goal"
        },
        {
          "field": "fat_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Fat goal"
        },
        {
          "field": "weight_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Weight goal"
        },
        {
          "field": "goal_deadline",
          "required": false,
          "source": "user-input",
          "prompt": "Goal deadline"
        }
      ]
    },
    {
      "id": "add-weight_log",
      "label": "添加体重记录",
      "type": "insert",
      "targetTable": "weight_log",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "time",
          "required": false,
          "source": "user-input",
          "prompt": "Time"
        },
        {
          "field": "weight_kg",
          "required": false,
          "source": "user-input",
          "prompt": "Weight kg"
        },
        {
          "field": "height_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Height cm"
        },
        {
          "field": "bmi",
          "required": false,
          "source": "user-input",
          "prompt": "Bmi"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    },
    {
      "id": "add-nutrition_products",
      "label": "添加食品库",
      "type": "insert",
      "targetTable": "nutrition_products",
      "fields": [
        {
          "field": "product_name",
          "required": false,
          "source": "user-input",
          "prompt": "Product name"
        },
        {
          "field": "brand",
          "required": false,
          "source": "user-input",
          "prompt": "Brand"
        },
        {
          "field": "calories",
          "required": false,
          "source": "user-input",
          "prompt": "Calories"
        },
        {
          "field": "protein",
          "required": false,
          "source": "user-input",
          "prompt": "Protein"
        },
        {
          "field": "fat",
          "required": false,
          "source": "user-input",
          "prompt": "Fat"
        },
        {
          "field": "saturated_fat",
          "required": false,
          "source": "user-input",
          "prompt": "Saturated fat"
        },
        {
          "field": "carbohydrates",
          "required": false,
          "source": "user-input",
          "prompt": "Carbohydrates"
        },
        {
          "field": "sugar",
          "required": false,
          "source": "user-input",
          "prompt": "Sugar"
        },
        {
          "field": "dietary_fiber",
          "required": false,
          "source": "user-input",
          "prompt": "Dietary fiber"
        },
        {
          "field": "sodium",
          "required": false,
          "source": "user-input",
          "prompt": "Sodium"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    },
    {
      "id": "add-exercise_log",
      "label": "添加运动记录",
      "type": "insert",
      "targetTable": "exercise_log",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "time",
          "required": false,
          "source": "user-input",
          "prompt": "Time"
        },
        {
          "field": "exercise_type",
          "required": false,
          "source": "user-input",
          "prompt": "Exercise type"
        },
        {
          "field": "duration_minutes",
          "required": false,
          "source": "user-input",
          "prompt": "Duration minutes"
        },
        {
          "field": "calories_burned",
          "required": false,
          "source": "user-input",
          "prompt": "Calories burned"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        },
        {
          "field": "reps",
          "required": false,
          "source": "user-input",
          "prompt": "Reps"
        }
      ]
    },
    {
      "id": "add-fitness_goals",
      "label": "添加健身目标",
      "type": "insert",
      "targetTable": "fitness_goals",
      "fields": [
        {
          "field": "name",
          "required": false,
          "source": "user-input",
          "prompt": "Name"
        },
        {
          "field": "goal_type",
          "required": false,
          "source": "user-input",
          "prompt": "Goal type"
        },
        {
          "field": "exercise_type",
          "required": false,
          "source": "user-input",
          "prompt": "Exercise type"
        },
        {
          "field": "target_unit",
          "required": false,
          "source": "user-input",
          "prompt": "Target unit"
        },
        {
          "field": "target_value",
          "required": false,
          "source": "user-input",
          "prompt": "Target value"
        },
        {
          "field": "start_date",
          "required": false,
          "source": "user-input",
          "prompt": "Start date"
        },
        {
          "field": "end_date",
          "required": false,
          "source": "user-input",
          "prompt": "End date"
        },
        {
          "field": "status",
          "required": false,
          "source": "user-input",
          "prompt": "Status"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    },
    {
      "id": "add-sleep_records",
      "label": "添加睡眠记录",
      "type": "insert",
      "targetTable": "sleep_records",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "sleep_hours",
          "required": false,
          "source": "user-input",
          "prompt": "Sleep hours"
        },
        {
          "field": "bedtime",
          "required": false,
          "source": "user-input",
          "prompt": "Bedtime"
        },
        {
          "field": "wake_time",
          "required": false,
          "source": "user-input",
          "prompt": "Wake time"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    },
    {
      "id": "add-body_photos",
      "label": "添加身材照片",
      "type": "insert",
      "targetTable": "body_photos",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "time",
          "required": true,
          "source": "user-input",
          "prompt": "Time"
        },
        {
          "field": "photo_path",
          "required": true,
          "source": "user-input",
          "prompt": "Photo path"
        },
        {
          "field": "tag",
          "required": true,
          "source": "user-input",
          "prompt": "Tag"
        },
        {
          "field": "note",
          "required": true,
          "source": "user-input",
          "prompt": "Note"
        }
      ]
    }
  ],
  "views": [
    {
      "id": "entries",
      "label": "饮食记录",
      "components": {
        "table": {
          "queryId": "entries-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-entries"
        }
      }
    },
    {
      "id": "daily_goal",
      "label": "每日目标",
      "components": {
        "table": {
          "queryId": "daily_goal-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-daily_goal"
        }
      }
    },
    {
      "id": "weight_log",
      "label": "体重记录",
      "components": {
        "table": {
          "queryId": "weight_log-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-weight_log"
        }
      }
    },
    {
      "id": "nutrition_products",
      "label": "食品库",
      "components": {
        "table": {
          "queryId": "nutrition_products-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-nutrition_products"
        }
      }
    },
    {
      "id": "exercise_log",
      "label": "运动记录",
      "components": {
        "table": {
          "queryId": "exercise_log-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-exercise_log"
        }
      }
    },
    {
      "id": "fitness_goals",
      "label": "健身目标",
      "components": {
        "table": {
          "queryId": "fitness_goals-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-fitness_goals"
        }
      }
    },
    {
      "id": "sleep_records",
      "label": "睡眠记录",
      "components": {
        "table": {
          "queryId": "sleep_records-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-sleep_records"
        }
      }
    },
    {
      "id": "body_photos",
      "label": "身材照片",
      "components": {
        "table": {
          "queryId": "body_photos-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-body_photos"
        }
      }
    }
  ]
}