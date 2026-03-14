"""
专家 Agent — 慢性病医疗顾问
数据来源：
  - 血糖：glucose_reader_node 从共享DB直读（精确）
  - 饮食：Vision Agent 拍照识别（有图时）
  - 情绪：triage + policy（对话/语音）
  - 历史：SQLite 长期记忆 + checkpointer 短期 history
无追问链：所有数据进 agent 前已就绪，单轮回答
"""
import re
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion_with_history_stream, format_history_for_sealion
from chatbot.memory.long_term import get_health_store
from chatbot.memory.rag.retriever import get_retriever
from chatbot.agents.glucose_reader import get_weekly_glucose_summary, get_weekly_diet_history


def _detect_language(text: str) -> str:
    """Detect if input is primarily English or Chinese."""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    ascii_letters  = len(re.findall(r'[a-zA-Z]', text))
    return "English" if ascii_letters > chinese_chars else "Chinese"


# ── 格式化辅助 ────────────────────────────────────────────────

def _fmt_glucose(readings: list) -> str:
    if not readings:
        return "暂无近1小时数据"
    return "、".join(
        f"{r.get('recorded_at', '?')[-8:-3]} {r.get('glucose', '?')} mmol/L"
        for r in readings
    )


def _fmt_weekly_glucose(records: list) -> str:
    if not records:
        return ""
    return "、".join(
        f"{r['date'][-5:]} 均{r['avg']} [{r['min']}-{r['max']}] mmol/L"
        for r in records
    )


def _fmt_weekly_diet(records: list) -> str:
    if not records:
        return ""
    return "\n".join(f"  {r['date'][-5:]}：{r['meals']}" for r in records)


def _fmt_diet(vision_result: list) -> str:
    if not vision_result:
        return ""
    foods = []
    for vr in vision_result:
        if vr.get("scene_type") == "FOOD" and not vr.get("error"):
            name = vr.get("food_name", "")
            cal = vr.get("total_calories", "")
            desc = name
            if cal:
                desc += f"（约{cal}大卡）"
            if desc:
                foods.append(desc)
    return "；".join(foods)


# ── 主节点 ────────────────────────────────────────────────────

def expert_agent_node(state: ChatState) -> dict:
    profile     = state.get("user_profile", {})
    name        = profile.get("name", "患者")
    conditions  = profile.get("conditions", ["Type 2 Diabetes"])
    medications = profile.get("medications", [])
    all_intents = state.get("all_intents", ["medical"])
    user_input  = state.get("user_input", "")
    language    = _detect_language(user_input) if user_input.strip() else profile.get("language", "Chinese")

    # ── 近 1 小时血糖（当轮，由 glucose_reader 注入 state）──────
    glucose_str = _fmt_glucose(state.get("glucose_readings") or [])

    # ── 近 7 天血糖每日浓缩（从共享 DB 读取）──────────────────
    weekly_glucose_str = _fmt_weekly_glucose(get_weekly_glucose_summary(user_id))

    # ── 近 7 天饮食历史（从共享 DB 读取）──────────────────────
    weekly_diet_str = _fmt_weekly_diet(get_weekly_diet_history(user_id))

    # ── 当轮饮食（Vision Agent 识别结果）──────────────────────
    diet_str = _fmt_diet(state.get("vision_result") or [])

    # ── RAG：仅在医学相关查询时触发 ──────────────────────────
    _RAG_KEYWORDS = ["药", "血糖", "饮食", "建议", "副作用", "怎么", "为什么", "能不能",
                     "medicine", "glucose", "diet", "recommend", "why", "how"]
    rag_context = ""
    if any(kw in user_input for kw in _RAG_KEYWORDS):
        rag_query   = f"{user_input} 血糖 {glucose_str} 饮食 {diet_str}"
        rag_context = get_retriever().retrieve(rag_query, n=3)

    emotion_label = state.get("emotion_label", "neutral")
    emotion_hint  = f"【当前情绪】{emotion_label}\n" if emotion_label != "neutral" else ""

    system_prompt = (
        f"你是专业的慢性病管理医疗顾问，专注于新加坡患者。\n"
        f"患者：{name} | 病症：{', '.join(conditions)} | "
        f"处方用药：{', '.join(medications) if medications else '未记录'}\n"
        f"请用{language}回复。\n\n"
        f"【近1小时血糖】\n"
        f"- 记录：{glucose_str}\n"
        f"{f'- 当餐饮食：{diet_str}{chr(10)}' if diet_str else ''}"
        f"{f'【近7天血糖趋势】{chr(10)}- {weekly_glucose_str}{chr(10)}' if weekly_glucose_str else ''}"
        f"{f'【近7天饮食历史】{chr(10)}{weekly_diet_str}{chr(10)}' if weekly_diet_str else ''}"
        f"{f'【参考医学资料】{chr(10)}{rag_context}{chr(10)}' if rag_context else ''}"
        f"{emotion_hint}"
        f"请根据以上数据回答患者问题，给出具体可行的建议。\n\n"
        f"通用规则：\n"
        "- 「打卡」指健康任务打卡，不是自我伤害\n"
        f"- 结合新加坡本地饮食文化\n"
        f"- 回复150字以内"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history, reasoning=True)

    print(f"[Expert] 意图：{all_intents} | 情绪：{emotion_label}")
    return {"response": response}
