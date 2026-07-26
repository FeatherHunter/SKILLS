// 自动生成 by generate_ts_config.py
// 生成时间: 2026-07-26 12:11:26
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
        "name": "food_log",
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
          },
          {
            "name": "water_goal",
            "type": "number",
            "label": "Water goal",
            "default": "2000",
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
          },
          {
            "name": "source",
            "type": "string",
            "label": "Source",
            "default": "'未知'",
            "editable": true
          },
          {
            "name": "is_deprecated",
            "type": "number",
            "label": "Is deprecated",
            "default": "0",
            "editable": true
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
          },
          {
            "name": "category",
            "type": "string",
            "label": "Category",
            "editable": true
          },
          {
            "name": "intensity",
            "type": "string",
            "label": "Intensity",
            "editable": true
          },
          {
            "name": "distance_km",
            "type": "number",
            "label": "Distance km",
            "editable": true
          },
          {
            "name": "avg_heart_rate",
            "type": "number",
            "label": "Avg heart rate",
            "editable": true
          },
          {
            "name": "set_index",
            "type": "number",
            "label": "Set index",
            "editable": true
          },
          {
            "name": "load_kg",
            "type": "number",
            "label": "Load kg",
            "editable": true
          },
          {
            "name": "difficulty",
            "type": "string",
            "label": "Difficulty",
            "editable": true
          },
          {
            "name": "xunji_localid",
            "type": "string",
            "label": "Xunji localid",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "xunji_title",
            "type": "string",
            "label": "Xunji title",
            "editable": true
          },
          {
            "name": "updated_at",
            "type": "string",
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
            "format": "datetime",
            "visible": false,
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
      },
      {
        "name": "workout_plan_config",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "title",
            "type": "string",
            "label": "Title",
            "editable": true
          },
          {
            "name": "version",
            "type": "string",
            "label": "Version",
            "editable": true
          },
          {
            "name": "description",
            "type": "string",
            "label": "Description",
            "editable": true
          },
          {
            "name": "total_weeks",
            "type": "number",
            "label": "Total weeks",
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
        "name": "workout_plans",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "week_number",
            "type": "number",
            "label": "Week number",
            "editable": true
          },
          {
            "name": "day_of_week",
            "type": "number",
            "label": "Day of week",
            "editable": true
          },
          {
            "name": "session_index",
            "type": "number",
            "label": "Session index",
            "default": "1",
            "editable": true
          },
          {
            "name": "session_label",
            "type": "string",
            "label": "Session label",
            "editable": true
          },
          {
            "name": "time_start",
            "type": "string",
            "label": "Time start",
            "format": "datetime",
            "visible": false,
            "editable": true
          },
          {
            "name": "time_end",
            "type": "string",
            "label": "Time end",
            "format": "datetime",
            "visible": false,
            "editable": true
          },
          {
            "name": "is_rest_day",
            "type": "number",
            "label": "Is rest day",
            "default": "0",
            "editable": true
          },
          {
            "name": "total_sets",
            "type": "number",
            "label": "Total sets",
            "editable": true
          },
          {
            "name": "movements",
            "type": "string",
            "label": "Movements",
            "default": "'[]'",
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
        "name": "user_profile",
        "fields": [
          {
            "name": "id",
            "type": "number",
            "label": "Id",
            "primaryKey": true,
            "editable": false
          },
          {
            "name": "age",
            "type": "number",
            "label": "Age",
            "editable": true
          },
          {
            "name": "gender",
            "type": "string",
            "label": "Gender",
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
        "name": "body_composition",
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
            "name": "source",
            "type": "string",
            "label": "Source",
            "editable": true
          },
          {
            "name": "age",
            "type": "number",
            "label": "Age",
            "editable": true
          },
          {
            "name": "sex",
            "type": "string",
            "label": "Sex",
            "editable": true
          },
          {
            "name": "caliper_chest_mm",
            "type": "number",
            "label": "Caliper chest mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_abdominal_mm",
            "type": "number",
            "label": "Caliper abdominal mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_thigh_mm",
            "type": "number",
            "label": "Caliper thigh mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_tricep_mm",
            "type": "number",
            "label": "Caliper tricep mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_subscapular_mm",
            "type": "number",
            "label": "Caliper subscapular mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_suprailiac_mm",
            "type": "number",
            "label": "Caliper suprailiac mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "caliper_midaxillary_mm",
            "type": "number",
            "label": "Caliper midaxillary mm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "body_fat_pct",
            "type": "number",
            "label": "Body fat pct",
            "unit": "克",
            "editable": true
          },
          {
            "name": "calculated_at",
            "type": "string",
            "label": "Calculated at",
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
            "name": "is_deprecated",
            "type": "number",
            "label": "Is deprecated",
            "default": "0",
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
        "name": "body_measurements",
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
            "name": "chest_cm",
            "type": "number",
            "label": "Chest cm",
            "editable": true
          },
          {
            "name": "waist_cm",
            "type": "number",
            "label": "Waist cm",
            "editable": true
          },
          {
            "name": "abdomen_cm",
            "type": "number",
            "label": "Abdomen cm",
            "editable": true
          },
          {
            "name": "hip_cm",
            "type": "number",
            "label": "Hip cm",
            "editable": true
          },
          {
            "name": "left_thigh_cm",
            "type": "number",
            "label": "Left thigh cm",
            "editable": true
          },
          {
            "name": "right_thigh_cm",
            "type": "number",
            "label": "Right thigh cm",
            "editable": true
          },
          {
            "name": "left_calf_cm",
            "type": "number",
            "label": "Left calf cm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "right_calf_cm",
            "type": "number",
            "label": "Right calf cm",
            "unit": "千卡",
            "editable": true
          },
          {
            "name": "left_arm_cm",
            "type": "number",
            "label": "Left arm cm",
            "editable": true
          },
          {
            "name": "right_arm_cm",
            "type": "number",
            "label": "Right arm cm",
            "editable": true
          },
          {
            "name": "left_forearm_cm",
            "type": "number",
            "label": "Left forearm cm",
            "editable": true
          },
          {
            "name": "right_forearm_cm",
            "type": "number",
            "label": "Right forearm cm",
            "editable": true
          },
          {
            "name": "shoulder_cm",
            "type": "number",
            "label": "Shoulder cm",
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
            "name": "is_deprecated",
            "type": "number",
            "label": "Is deprecated",
            "default": "0",
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
      }
    ]
  },
  "queries": [
    {
      "id": "food_log-daily",
      "label": "今日food_log",
      "sql": "SELECT * FROM food_log WHERE date = '{date}' ORDER BY time",
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
      "id": "food_log-history",
      "label": "food_log历史",
      "sql": "SELECT * FROM food_log ORDER BY date DESC, time DESC LIMIT 100",
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
      "id": "body_photos-daily",
      "label": "今日body_photos",
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
      "label": "body_photos历史",
      "sql": "SELECT * FROM body_photos ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "workout_plan_config-all",
      "label": "全部workout_plan_config",
      "sql": "SELECT * FROM workout_plan_config ORDER BY id DESC",
      "params": []
    },
    {
      "id": "workout_plans-all",
      "label": "全部workout_plans",
      "sql": "SELECT * FROM workout_plans ORDER BY id DESC",
      "params": []
    },
    {
      "id": "user_profile-all",
      "label": "全部user_profile",
      "sql": "SELECT * FROM user_profile ORDER BY id DESC",
      "params": []
    },
    {
      "id": "body_composition-daily",
      "label": "今日body_composition",
      "sql": "SELECT * FROM body_composition WHERE date = '{date}' ORDER BY time",
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
      "id": "body_composition-history",
      "label": "body_composition历史",
      "sql": "SELECT * FROM body_composition ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    },
    {
      "id": "body_measurements-daily",
      "label": "今日body_measurements",
      "sql": "SELECT * FROM body_measurements WHERE date = '{date}' ORDER BY time",
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
      "id": "body_measurements-history",
      "label": "body_measurements历史",
      "sql": "SELECT * FROM body_measurements ORDER BY date DESC, time DESC LIMIT 100",
      "params": []
    }
  ],
  "actions": [
    {
      "id": "add-food_log",
      "label": "添加food_log",
      "type": "insert",
      "targetTable": "food_log",
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
        },
        {
          "field": "water_goal",
          "required": false,
          "source": "user-input",
          "prompt": "Water goal"
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
        },
        {
          "field": "source",
          "required": false,
          "source": "user-input",
          "prompt": "Source"
        },
        {
          "field": "is_deprecated",
          "required": false,
          "source": "user-input",
          "prompt": "Is deprecated"
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
        },
        {
          "field": "category",
          "required": false,
          "source": "user-input",
          "prompt": "Category"
        },
        {
          "field": "intensity",
          "required": false,
          "source": "user-input",
          "prompt": "Intensity"
        },
        {
          "field": "distance_km",
          "required": false,
          "source": "user-input",
          "prompt": "Distance km"
        },
        {
          "field": "avg_heart_rate",
          "required": false,
          "source": "user-input",
          "prompt": "Avg heart rate"
        },
        {
          "field": "set_index",
          "required": false,
          "source": "user-input",
          "prompt": "Set index"
        },
        {
          "field": "load_kg",
          "required": false,
          "source": "user-input",
          "prompt": "Load kg"
        },
        {
          "field": "difficulty",
          "required": false,
          "source": "user-input",
          "prompt": "Difficulty"
        },
        {
          "field": "xunji_localid",
          "required": false,
          "source": "user-input",
          "prompt": "Xunji localid"
        },
        {
          "field": "xunji_title",
          "required": false,
          "source": "user-input",
          "prompt": "Xunji title"
        }
      ]
    },
    {
      "id": "add-body_photos",
      "label": "添加body_photos",
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
          "required": false,
          "source": "user-input",
          "prompt": "Time"
        },
        {
          "field": "photo_path",
          "required": false,
          "source": "user-input",
          "prompt": "Photo path"
        },
        {
          "field": "tag",
          "required": false,
          "source": "user-input",
          "prompt": "Tag"
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
      "id": "add-workout_plan_config",
      "label": "添加workout_plan_config",
      "type": "insert",
      "targetTable": "workout_plan_config",
      "fields": [
        {
          "field": "title",
          "required": false,
          "source": "user-input",
          "prompt": "Title"
        },
        {
          "field": "version",
          "required": false,
          "source": "user-input",
          "prompt": "Version"
        },
        {
          "field": "description",
          "required": false,
          "source": "user-input",
          "prompt": "Description"
        },
        {
          "field": "total_weeks",
          "required": false,
          "source": "user-input",
          "prompt": "Total weeks"
        },
        {
          "field": "start_date",
          "required": false,
          "source": "user-input",
          "prompt": "Start date"
        }
      ]
    },
    {
      "id": "add-workout_plans",
      "label": "添加workout_plans",
      "type": "insert",
      "targetTable": "workout_plans",
      "fields": [
        {
          "field": "week_number",
          "required": false,
          "source": "user-input",
          "prompt": "Week number"
        },
        {
          "field": "day_of_week",
          "required": false,
          "source": "user-input",
          "prompt": "Day of week"
        },
        {
          "field": "session_index",
          "required": false,
          "source": "user-input",
          "prompt": "Session index"
        },
        {
          "field": "session_label",
          "required": false,
          "source": "user-input",
          "prompt": "Session label"
        },
        {
          "field": "time_start",
          "required": false,
          "source": "user-input",
          "prompt": "Time start"
        },
        {
          "field": "time_end",
          "required": false,
          "source": "user-input",
          "prompt": "Time end"
        },
        {
          "field": "is_rest_day",
          "required": false,
          "source": "user-input",
          "prompt": "Is rest day"
        },
        {
          "field": "total_sets",
          "required": false,
          "source": "user-input",
          "prompt": "Total sets"
        },
        {
          "field": "movements",
          "required": false,
          "source": "user-input",
          "prompt": "Movements"
        }
      ]
    },
    {
      "id": "add-user_profile",
      "label": "添加user_profile",
      "type": "insert",
      "targetTable": "user_profile",
      "fields": [
        {
          "field": "age",
          "required": false,
          "source": "user-input",
          "prompt": "Age"
        },
        {
          "field": "gender",
          "required": false,
          "source": "user-input",
          "prompt": "Gender"
        },
        {
          "field": "height_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Height cm"
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
      "id": "add-body_composition",
      "label": "添加body_composition",
      "type": "insert",
      "targetTable": "body_composition",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "source",
          "required": false,
          "source": "user-input",
          "prompt": "Source"
        },
        {
          "field": "age",
          "required": false,
          "source": "user-input",
          "prompt": "Age"
        },
        {
          "field": "sex",
          "required": false,
          "source": "user-input",
          "prompt": "Sex"
        },
        {
          "field": "caliper_chest_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper chest mm"
        },
        {
          "field": "caliper_abdominal_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper abdominal mm"
        },
        {
          "field": "caliper_thigh_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper thigh mm"
        },
        {
          "field": "caliper_tricep_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper tricep mm"
        },
        {
          "field": "caliper_subscapular_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper subscapular mm"
        },
        {
          "field": "caliper_suprailiac_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper suprailiac mm"
        },
        {
          "field": "caliper_midaxillary_mm",
          "required": false,
          "source": "user-input",
          "prompt": "Caliper midaxillary mm"
        },
        {
          "field": "body_fat_pct",
          "required": false,
          "source": "user-input",
          "prompt": "Body fat pct"
        },
        {
          "field": "calculated_at",
          "required": false,
          "source": "user-input",
          "prompt": "Calculated at"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        },
        {
          "field": "is_deprecated",
          "required": false,
          "source": "user-input",
          "prompt": "Is deprecated"
        }
      ]
    },
    {
      "id": "add-body_measurements",
      "label": "添加body_measurements",
      "type": "insert",
      "targetTable": "body_measurements",
      "fields": [
        {
          "field": "date",
          "required": true,
          "source": "user-input",
          "prompt": "Date"
        },
        {
          "field": "chest_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Chest cm"
        },
        {
          "field": "waist_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Waist cm"
        },
        {
          "field": "abdomen_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Abdomen cm"
        },
        {
          "field": "hip_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Hip cm"
        },
        {
          "field": "left_thigh_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Left thigh cm"
        },
        {
          "field": "right_thigh_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Right thigh cm"
        },
        {
          "field": "left_calf_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Left calf cm"
        },
        {
          "field": "right_calf_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Right calf cm"
        },
        {
          "field": "left_arm_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Left arm cm"
        },
        {
          "field": "right_arm_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Right arm cm"
        },
        {
          "field": "left_forearm_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Left forearm cm"
        },
        {
          "field": "right_forearm_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Right forearm cm"
        },
        {
          "field": "shoulder_cm",
          "required": false,
          "source": "user-input",
          "prompt": "Shoulder cm"
        },
        {
          "field": "note",
          "required": false,
          "source": "user-input",
          "prompt": "Note"
        },
        {
          "field": "is_deprecated",
          "required": false,
          "source": "user-input",
          "prompt": "Is deprecated"
        }
      ]
    }
  ],
  "views": [
    {
      "id": "food_log",
      "label": "food_log",
      "components": {
        "table": {
          "queryId": "food_log-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-food_log"
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
      "id": "body_photos",
      "label": "body_photos",
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
    },
    {
      "id": "workout_plan_config",
      "label": "workout_plan_config",
      "components": {
        "table": {
          "queryId": "workout_plan_config-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-workout_plan_config"
        }
      }
    },
    {
      "id": "workout_plans",
      "label": "workout_plans",
      "components": {
        "table": {
          "queryId": "workout_plans-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-workout_plans"
        }
      }
    },
    {
      "id": "user_profile",
      "label": "user_profile",
      "components": {
        "table": {
          "queryId": "user_profile-all",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-user_profile"
        }
      }
    },
    {
      "id": "body_composition",
      "label": "body_composition",
      "components": {
        "table": {
          "queryId": "body_composition-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-body_composition"
        }
      }
    },
    {
      "id": "body_measurements",
      "label": "body_measurements",
      "components": {
        "table": {
          "queryId": "body_measurements-daily",
          "sortable": true,
          "pageSize": 20
        },
        "form": {
          "actionId": "add-body_measurements"
        }
      }
    }
  ]
}