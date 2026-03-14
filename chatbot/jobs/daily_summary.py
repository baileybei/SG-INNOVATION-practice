"""
每日情绪汇总定时任务
23:59 运行：读今日 emotion_log → LLM 汇总 → 写 emotion_summary
"""
from datetime import datetime
from chatbot.memory.long_term import get_health_store
from chatbot.utils.llm_factory import call_sealion


def _summarize_emotions(entries: list) -> str:
    """调 LLM 汇总当日情绪记录，返回 summary_text。"""
    log_text = "\n".join(
        f"- [{e['emotion_label']}] {e['user_input']}"
        for e in entries
    )
    prompt = (
        f"以下是一位慢性病患者今天的情绪记录：\n{log_text}\n\n"
        "请用1-2句话总结：患者今天的整体情绪状态，以及可能的触发原因。\n"
        "只输出摘要句子，不加任何解释。"
    )
    return call_sealion(
        "你是健康管理系统的记录员，负责简洁记录患者每日情绪状态。",
        prompt,
    )


def run_daily_summary() -> None:
    """遍历今日有情绪记录的用户，逐个汇总并存储。"""
    store = get_health_store()
    today = datetime.now().strftime("%Y-%m-%d")
    user_ids = store.get_today_emotion_user_ids()

    if not user_ids:
        print("[DailySummary] 今日无情绪记录，跳过")
        return

    for user_id in user_ids:
        entries = store.get_today_emotions(user_id)
        if not entries:
            continue

        text = _summarize_emotions(entries)
        store.save_emotion_summary(user_id, text, today)
        print(f"[DailySummary] {user_id} 汇总完成：{text[:40]}…")

    print(f"[DailySummary] 共处理 {len(user_ids)} 位用户")
