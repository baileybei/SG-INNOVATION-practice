"""
glucose_reader — 读取共享数据库血糖及饮食数据
- 近 1 小时：最多 6 条 raw value → 注入 state（供 expert_agent 当轮使用）
- 近 7 天：每日血糖浓缩 + 饮食历史 → 由 expert_agent 按需读取
生产环境：替换各 _MOCK_* 为真实数据库查询
"""
from chatbot.state.chat_state import ChatState

# ── 近 1 小时 raw CGM data ────────────────────────────────────────────────────
# 生产环境替换为：SELECT * FROM user_cgm_log WHERE user_id=? AND recorded_at >= NOW()-1h ORDER BY recorded_at DESC LIMIT 6
_MOCK_CGM_DATA = {
    "user_001": [
        {"recorded_at": "2026-03-14T14:00:00", "glucose": 6.8},
        {"recorded_at": "2026-03-14T14:10:00", "glucose": 7.2},
        {"recorded_at": "2026-03-14T14:20:00", "glucose": 8.5},
    ],
    "user_002": [
        {"recorded_at": "2026-03-14T14:00:00", "glucose": 7.1},
        {"recorded_at": "2026-03-14T14:10:00", "glucose": 10.3},
    ],
}

# ── 近 7 天每日血糖浓缩 ───────────────────────────────────────────────────────
# 生产环境替换为：SELECT date, avg_glucose, min_glucose, max_glucose FROM daily_glucose_summary WHERE user_id=? AND date >= TODAY-7
_MOCK_WEEKLY_GLUCOSE = {
    "user_001": [
        {"date": "2026-03-08", "avg": 7.4, "min": 5.9, "max": 9.8},
        {"date": "2026-03-09", "avg": 6.9, "min": 5.6, "max": 8.7},
        {"date": "2026-03-10", "avg": 8.1, "min": 6.2, "max": 11.3},
        {"date": "2026-03-11", "avg": 7.6, "min": 6.0, "max": 9.5},
        {"date": "2026-03-12", "avg": 7.0, "min": 5.8, "max": 8.9},
        {"date": "2026-03-13", "avg": 7.8, "min": 6.1, "max": 10.2},
        {"date": "2026-03-14", "avg": 7.5, "min": 6.8, "max": 8.5},
    ],
    "user_002": [
        {"date": "2026-03-08", "avg": 8.2, "min": 6.5, "max": 12.1},
        {"date": "2026-03-09", "avg": 7.9, "min": 6.3, "max": 10.5},
        {"date": "2026-03-10", "avg": 9.1, "min": 7.0, "max": 13.2},
        {"date": "2026-03-11", "avg": 8.5, "min": 6.8, "max": 11.4},
        {"date": "2026-03-12", "avg": 7.7, "min": 6.2, "max": 10.8},
        {"date": "2026-03-13", "avg": 8.3, "min": 6.9, "max": 11.6},
        {"date": "2026-03-14", "avg": 8.7, "min": 7.1, "max": 10.3},
    ],
}

# ── 近 7 天饮食历史 ────────────────────────────────────────────────────────────
# 生产环境替换为：SELECT date, meal_type, food_items, calories FROM diet_log WHERE user_id=? AND date >= TODAY-7
_MOCK_WEEKLY_DIET = {
    "user_001": [
        {"date": "2026-03-08", "meals": "早餐：燕麦粥；午餐：鸡饭（少饭）；晚餐：蒸鱼 + 蔬菜"},
        {"date": "2026-03-09", "meals": "早餐：全麦面包；午餐：杂菜饭；晚餐：汤面"},
        {"date": "2026-03-10", "meals": "早餐：咖椰吐司 + 半熟蛋；午餐：laksa；晚餐：蒸鸡 + 豆腐"},
        {"date": "2026-03-11", "meals": "早餐：燕麦粥；午餐：云吞面（少量）；晚餐：鱼片米粉汤"},
        {"date": "2026-03-12", "meals": "早餐：全麦面包；午餐：沙拉 + 烤鸡；晚餐：蒸鱼 + 糙米"},
        {"date": "2026-03-13", "meals": "早餐：燕麦；午餐：chicken rice；晚餐：炒蔬菜 + 豆腐"},
        {"date": "2026-03-14", "meals": "早餐：全麦面包；午餐：杂菜饭（少饭多菜）"},
    ],
    "user_002": [
        {"date": "2026-03-08", "meals": "Breakfast: Oats; Lunch: Nasi lemak (small portion); Dinner: Grilled chicken + salad"},
        {"date": "2026-03-09", "meals": "Breakfast: Wholemeal bread; Lunch: Mixed rice; Dinner: Fish soup"},
        {"date": "2026-03-10", "meals": "Breakfast: Roti prata (1 piece); Lunch: Chicken rice; Dinner: Stir-fried veg + tofu"},
        {"date": "2026-03-11", "meals": "Breakfast: Oats; Lunch: Wonton noodle (small); Dinner: Steamed fish + brown rice"},
        {"date": "2026-03-12", "meals": "Breakfast: Wholemeal bread; Lunch: Salad + grilled chicken; Dinner: Steamed fish"},
        {"date": "2026-03-13", "meals": "Breakfast: Oats; Lunch: Chicken rice; Dinner: Mixed veg + tofu"},
        {"date": "2026-03-14", "meals": "Breakfast: Wholemeal bread; Lunch: Mixed rice (less carbs)"},
    ],
}


def glucose_reader_node(state: ChatState) -> dict:
    """读取最近 1 小时血糖数据（最多 6 条），注入 state。只读，不写。"""
    user_id  = state["user_id"]
    readings = _MOCK_CGM_DATA.get(user_id, [])[-6:]
    print(f"[GlucoseReader] {len(readings)} 条血糖数据")
    return {"glucose_readings": readings}


def get_weekly_glucose_summary(user_id: str) -> list:
    """返回近 7 天每日血糖浓缩，供 expert_agent 读取。只读，不写。"""
    return _MOCK_WEEKLY_GLUCOSE.get(user_id, [])


def get_weekly_diet_history(user_id: str) -> list:
    """返回近 7 天饮食历史，供 expert_agent 读取。只读，不写。"""
    return _MOCK_WEEKLY_DIET.get(user_id, [])
