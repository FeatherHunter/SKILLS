#!/usr/bin/env python3
"""
私家大厨 - 数据库初始化脚本 v1.0
建表脚本，13张表
"""

import sys
from pathlib import Path

# ── 导入共用DB配置 ───────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from db_config import DB_PATH, get_conn


def init_db():
    """初始化SQLite数据库（创建表和索引，幂等）"""
    conn = get_conn()
    cursor = conn.cursor()

    # ── 表1：recipes ────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            internal_code TEXT,
            name TEXT NOT NULL,
            name_aliases TEXT,
            description TEXT,
            appearance_desc TEXT,
            taste_desc TEXT,
            texture_desc TEXT,
            time_total_minutes INTEGER,
            time_prep_minutes INTEGER,
            time_cook_minutes INTEGER,
            time_cleanup_minutes INTEGER,
            difficulty TEXT,
            difficulty_user TEXT,
            servings INTEGER,
            recipe_version TEXT,
            parent_recipe_id TEXT,
            is_reference INTEGER DEFAULT 0,
            status TEXT DEFAULT '未做',
            times_cooked INTEGER DEFAULT 0,
            user_rating REAL,
            user_feedback TEXT,
            want_to_cook_level INTEGER,
            is_favorite INTEGER DEFAULT 0,
            is_staple INTEGER DEFAULT 0,
            cost_per_serving REAL,
            created_at TEXT,
            updated_at TEXT,
            source_url TEXT,
            source_author TEXT,
            video_url TEXT,
            photo_urls TEXT,
            keywords TEXT,
            notes TEXT,
            energy_level TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_difficulty ON recipes(difficulty)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_status ON recipes(status)')

    # ── 表2：recipe_locations ────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_locations (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            country TEXT,
            province TEXT,
            city TEXT,
            cuisine_type TEXT,
            cuisine_type_secondary TEXT,
            dish_type TEXT,
            meal_type TEXT,
            cooking_method TEXT,
            flavor_profile TEXT,
            flavor_intensity TEXT,
            diet_tags TEXT,
            seasons TEXT,
            occasions TEXT,
            target_demographic TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_locations_recipe ON recipe_locations(recipe_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_locations_cuisine ON recipe_locations(cuisine_type)')

    # ── 表3：ingredients ─────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            sequence INTEGER,
            name TEXT NOT NULL,
            category TEXT,
            quantity REAL,
            quantity_text TEXT,
            unit TEXT,
            state TEXT,
            size TEXT,
            cut_style TEXT,
            quality_grade TEXT,
            brand TEXT,
            purchase_place TEXT,
            supermarkets TEXT,
            price_per_unit REAL,
            purchase_specs TEXT,
            storage_type TEXT,
            frozen_ok INTEGER DEFAULT 0,
            shelf_life_days INTEGER,
            prepped_storage TEXT,
            is_optional INTEGER DEFAULT 0,
            is_staple INTEGER DEFAULT 0,
            substitute TEXT,
            substitute_notes TEXT,
            introduced_method TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # ── 表4：ingredient_preparations ─────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_preparations (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            ingredient_id TEXT,
            step_id TEXT,
            introduced_method TEXT,
            prep_name TEXT,
            prep_details TEXT,
            tools_used TEXT,
            duration_minutes INTEGER,
            temperature TEXT,
            temperature_end TEXT,
            liquid_used TEXT,
            liquid_ratio TEXT,
            seasoning_added TEXT,
            coating_used TEXT,
            coating_ratio TEXT,
            texture_after TEXT,
            color_change TEXT,
            smell_change TEXT,
            storage_method TEXT,
            storage_duration TEXT,
            is_prerequisite INTEGER DEFAULT 0,
            prerequisite_notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE SET NULL,
            FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE SET NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ingredient_preps_recipe ON ingredient_preparations(recipe_id)')

    # ── 表5：cooking_steps ───────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cooking_steps (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            phase TEXT,
            action TEXT NOT NULL,
            purpose TEXT,
            sub_purpose TEXT,
            tools TEXT,
            duration_minutes REAL,
            temperature_value REAL,
            temperature_end_value REAL,
            temperature_unit TEXT,
            heat_level TEXT,
            heat_adjustment TEXT,
            urgency_level TEXT,
            expected_result TEXT,
            visual_signal TEXT,
            audio_signal TEXT,
            smell_signal TEXT,
            texture_signal TEXT,
            doneness_indicator TEXT,
            color_during TEXT,
            color_after TEXT,
            texture_during TEXT,
            texture_after TEXT,
            can_parallel INTEGER DEFAULT 0,
            parallel_with INTEGER,
            parallel_notes TEXT,
            common_mistakes TEXT,
            mistake_causes TEXT,
            mistake_fixes TEXT,
            is_critical INTEGER DEFAULT 0,
            is_safety_critical INTEGER DEFAULT 0,
            warnings TEXT,
            retry_strategy TEXT,
            can_skip INTEGER DEFAULT 0,
            skip_effects TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cooking_steps_recipe ON cooking_steps(recipe_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cooking_steps_sequence ON cooking_steps(recipe_id, sequence)')

    # ── 表6：step_techniques ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS step_techniques (
            id TEXT PRIMARY KEY,
            step_id TEXT,
            recipe_id TEXT,
            technique_code TEXT,
            technique_name TEXT NOT NULL,
            description TEXT,
            key_points TEXT,
            wrist_action TEXT,
            arm_action TEXT,
            fire_control TEXT,
            timing TEXT,
            speed TEXT,
            difficulty_to_learn TEXT,
            learn_stage TEXT,
            common_errors TEXT,
            error_signs TEXT,
            fix_methods TEXT,
            prerequisite_skills TEXT,
            related_techniques TEXT,
            youtube_links TEXT,
            practice_exercises TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE SET NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_techniques_step ON step_techniques(step_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_techniques_code ON step_techniques(technique_code)')

    # ── 表7：tips ────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tips (
            id TEXT PRIMARY KEY,
            recipe_id TEXT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            apply_to_step INTEGER,
            apply_to_ingredient INTEGER,
            cost_level TEXT,
            time_cost TEXT,
            equipment_needed TEXT,
            difficulty TEXT,
            effectiveness_proven INTEGER DEFAULT 0,
            difficulty_proven TEXT,
            effectiveness_rating INTEGER,
            source TEXT,
            author TEXT,
            author_url TEXT,
            is_verified INTEGER DEFAULT 0,
            verified_by_user INTEGER DEFAULT 0,
            verified_date TEXT,
            user_modified_content TEXT,
            user_verified_result TEXT,
            is_public INTEGER DEFAULT 0,
            likes_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tips_recipe ON tips(recipe_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tips_category ON tips(category)')

    # ── 表8：background_knowledge ────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS background_knowledge (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL UNIQUE,
            origin_story TEXT,
            historical_background TEXT,
            era TEXT,
            cultural_significance TEXT,
            story_variants TEXT,
            famous_restaurants TEXT,
            famous_chefs TEXT,
            related_dishes TEXT,
            regional_variants TEXT,
            nutrition_benefits TEXT,
            nutrition_highlights TEXT,
            nutrition_concerns TEXT,
            taboos TEXT,
            wine_pairing TEXT,
            wine_pairing_details TEXT,
            beverage_pairing TEXT,
            staplefood_pairing TEXT,
            side_dish_pairing TEXT,
            weather_suitability TEXT,
            external_links TEXT,
            media_references TEXT,
            cultural_notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_background_recipe ON background_knowledge(recipe_id)')

    # ── 表9：nutrition_info ───────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nutrition_info (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL UNIQUE,
            serving_size REAL,
            serving_unit TEXT,
            servings_total INTEGER,
            calories_kcal INTEGER,
            calories_per_serving INTEGER,
            protein_grams REAL,
            fat_grams REAL,
            saturated_fat_g REAL,
            trans_fat_g REAL,
            carbohydrates_grams REAL,
            fiber_grams REAL,
            sugar_grams REAL,
            added_sugar_g REAL,
            sodium_mg REAL,
            cholesterol_mg REAL,
            vitamin_a_mcg REAL,
            vitamin_b1_mg REAL,
            vitamin_b2_mg REAL,
            vitamin_b3_mg REAL,
            vitamin_c_mg REAL,
            vitamin_d_mcg REAL,
            vitamin_e_mg REAL,
            calcium_mg REAL,
            iron_mg REAL,
            zinc_mg REAL,
            magnesium_mg REAL,
            potassium_mg REAL,
            selenium_mcg REAL,
            calculation_method TEXT,
            data_source TEXT,
            is_estimated INTEGER DEFAULT 1,
            confidence_level TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nutrition_recipe ON nutrition_info(recipe_id)')

    # ── 表10：recipe_history ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_history (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            cook_date TEXT NOT NULL,
            cook_sequence INTEGER,
            modifications TEXT,
            rating_this_time INTEGER,
            feedback TEXT,
            improvements TEXT,
            photos TEXT,
            time_actual_minutes INTEGER,
            cost_actual REAL,
            tools_used TEXT,
            mistakes_made TEXT,
            appetite_rating INTEGER,
            compared_to_last_time INTEGER DEFAULT 0,
            comparison_notes TEXT,
            is_favorite INTEGER DEFAULT 0,
            next_cook_plan TEXT,
            tags TEXT,
            created_at TEXT,
            weather TEXT,
            people_count INTEGER,
            mood_when_cooking TEXT,
            energy_level TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_history_recipe ON recipe_history(recipe_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_history_date ON recipe_history(cook_date)')

    # ── 表11：cookware ───────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cookware (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            size TEXT,
            material TEXT,
            heat_source TEXT,
            quantity INTEGER DEFAULT 1,
            purchase_date TEXT,
            brand TEXT,
            price REAL,
            condition TEXT,
            notes TEXT,
            maintenance_tips TEXT,
            compatible_dishes TEXT,
            incompatible_dishes TEXT,
            user_rating INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cookware_name ON cookware(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cookware_category ON cookware(category)')

    # ── 表12：beverage_pairings ───────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beverage_pairings (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            pairing_type TEXT,
            beverage_name TEXT NOT NULL,
            beverage_category TEXT,
            pairing_reason TEXT,
            flavor_match TEXT,
            temperature TEXT,
            brand_recommendation TEXT,
            price_range TEXT,
            substitute_options TEXT,
            occasion_suitability TEXT,
            region_tradition TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_beverage_recipe ON beverage_pairings(recipe_id)')

    # ── 表13：recipe_collections ─────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_collections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT,
            cover_image TEXT,
            recipe_ids TEXT,
            created_by TEXT,
            is_public INTEGER DEFAULT 0,
            tags TEXT,
            target_audience TEXT,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            notes TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_collections_name ON recipe_collections(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_collections_type ON recipe_collections(type)')

    conn.commit()
    conn.close()
    print(f"✅ 私家大厨数据库初始化完成: {DB_PATH}")
    return True


if __name__ == "__main__":
    init_db()