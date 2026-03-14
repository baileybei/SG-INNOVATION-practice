"""
main.py — 项目统一入口
运行方式：python main.py（从项目根目录）

History 由 LangGraph Checkpointer 自动持久化，main.py 无需手动维护。
"""
from apscheduler.schedulers.background import BackgroundScheduler
from chatbot.graph.builder import app
from chatbot.jobs.daily_summary import run_daily_summary
from chatbot.utils.memory import get_user_profile


# ── 每轮重置的字段（不依赖 checkpointer）──────────────────────────
def _per_turn(
    user_input: str,
    user_id: str,
    input_mode: str = "text",
    audio_path: str = None,
    image_paths: list = None,
    chat_mode: str = "personal",
) -> dict:
    return {
        "user_id":            user_id,
        "user_input":         user_input,
        "input_mode":         input_mode,
        "chat_mode":          chat_mode,
        "audio_path":         audio_path,
        "transcribed_text":   None,
        "emotion_label":      "neutral",
        "emotion_confidence": 0.0,
        "intent":             None,
        "all_intents":        None,
        "response":           None,
        "emotion_log":        None,

        "image_paths":        image_paths,
        "vision_result":      None,
    }


# ── 初始化新线程（首次对话 / reset 后）────────────────────────────
def _init_thread(config: dict, user_id: str, force_reset: bool = False) -> None:
    """
    首次启动只写 user_profile，保留 checkpointer 中的历史记录。
    force_reset=True（reset 命令）时才清空 history。
    """
    existing = app.get_state(config)
    has_state = existing and existing.values

    if force_reset or not has_state:
        app.update_state(config, {
            "user_profile":    get_user_profile(user_id),
            "history":         [],
            "recent_emotions": [],
        })
    else:
        # 恢复旧 session：只刷新 user_profile
        app.update_state(config, {"user_profile": get_user_profile(user_id)})


def run_cli():
    print("=" * 55)
    print("  Health Companion — 对话测试")
    print("  输入 'quit' 退出 | 'reset' 清空历史 | 'voice 路径' 语音 | 'image 路径 [文字]' 图片")
    print("=" * 55)

    user_id = "user_001"
    config  = {"configurable": {"thread_id": user_id}}

    # 每日 23:59 情绪汇总定时任务
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_daily_summary, 'cron', hour=23, minute=59)
    scheduler.start()

    # 初始化线程持久状态
    _init_thread(config, user_id)

    profile = get_user_profile(user_id)
    print(f"\n  当前用户：{profile['name']} | 病症：{', '.join(profile['conditions'])}\n")

    while True:
        user_input = input("你：").strip()

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "reset":
            _init_thread(config, user_id, force_reset=True)
            print("[系统] 对话历史已清空\n")
            continue

        # 图片模式：输入 "image 图片路径" 或 "image 图片路径 附带文字"
        if user_input.lower().startswith("image "):
            parts    = user_input[6:].strip().split(" ", 1)
            img_path = parts[0]
            text     = parts[1] if len(parts) > 1 else ""
            print(f"[图片模式] 正在识别：{img_path}")
            state = _per_turn(text, user_id, image_paths=[img_path])

        # 语音模式：输入 "voice 音频文件路径"
        elif user_input.lower().startswith("voice "):
            audio_path = user_input[6:].strip()
            print(f"[语音模式] 处理音频：{audio_path}")
            state = _per_turn("", user_id, input_mode="voice", audio_path=audio_path)

        else:
            state = _per_turn(user_input, user_id)

        result = app.invoke(state, config=config)

        if result.get("vision_result"):
            for vr in result["vision_result"]:
                scene = vr.get("scene_type", "?")
                conf  = vr.get("confidence", 0.0)
                print(f"  [Vision] 识别结果：{scene}（置信度 {conf:.0%}）")

        intent  = result.get("intent", "?")
        emotion = result.get("emotion_label", "neutral")
        print(f"  [{intent} | {emotion}]\n")

        if result.get("emotion_log"):
            print("  📊 → 集成数据库：情绪记录已写入")
        print()


if __name__ == "__main__":
    run_cli()
