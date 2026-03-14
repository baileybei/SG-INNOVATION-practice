"""
agents/triage.py
意图分类 + 情绪识别合并为一次调用
追问链进行中：只检测退出意图，不判断情绪（省token）
"""
import json
import re
from typing import Optional
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion
from chatbot.utils.meralion import process_voice_input, process_text_input
from chatbot.config.settings import ALL_INTENTS, INTENT_COMPANION
from chatbot.memory.long_term import get_health_store


import concurrent.futures

from src.vision_agent.agent import VisionAgent as _VisionAgent
_vision_agent: "_VisionAgent | None" = None
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def analyze_image(image_path: str):
    """Call Vision Agent to analyze an image. Returns AnalysisResult or None on timeout."""
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = _VisionAgent()
    future = _executor.submit(_vision_agent.analyze, image_path)
    try:
        return future.result(timeout=15)
    except concurrent.futures.TimeoutError:
        print(f"[Triage] Vision 超时（>15s），跳过图片分析：{image_path}")
        return None
    except Exception as e:
        print(f"[Triage] Vision 调用失败：{e}")
        return None


# scene_type → synthetic text (when user sends image with no text)
SCENE_TEXT_MAP = {
    "FOOD":       "我拍了一张食物照片",
    "MEDICATION": "我拍了一张药物照片",
    "REPORT":     "我拍了一张化验单照片",
    "UNKNOWN":    "我发了一张照片",
}



def input_node(state: ChatState) -> dict:
    # ── Voice mode ──────────────────────────────────────
    if state["input_mode"] == "voice":
        audio_path = state.get("audio_path", "")
        result = process_voice_input(audio_path)

        return {
            "user_input":         result["transcribed_text"],
            "transcribed_text":   result["transcribed_text"],
            "emotion_label":      result["emotion_label"],
            "emotion_confidence": result["emotion_confidence"],
        }

    # ── Image handling ──────────────────────────────────
    image_paths = state.get("image_paths") or []
    vision_result = []

    if image_paths:
        for path in image_paths:
            try:
                result = analyze_image(path)
                if result is None:
                    vision_result.append({
                        "scene_type": "UNKNOWN",
                        "error": "Vision 超时或失败",
                        "confidence": 0.0,
                    })
                elif not result.is_error and result.structured_output:
                    vision_result.append(result.structured_output.model_dump())
                else:
                    vision_result.append({
                        "scene_type": "UNKNOWN",
                        "error": result.error or "识别失败",
                        "confidence": 0.0,
                    })
            except Exception as e:
                vision_result.append({
                    "scene_type": "UNKNOWN",
                    "error": str(e),
                    "confidence": 0.0,
                })

    # ── Synthetic text for image-only input ─────────────
    user_input = state["user_input"]
    if image_paths and not user_input.strip():
        scene = vision_result[0].get("scene_type", "UNKNOWN") if vision_result else "UNKNOWN"
        user_input = SCENE_TEXT_MAP.get(scene, "我发了一张照片")

    # ── 文字情绪识别（语义）────────────────────────────────
    emotion_result = process_text_input(user_input)

    updates = {
        "transcribed_text":   user_input,
        "emotion_label":      emotion_result["emotion_label"],
        "emotion_confidence": emotion_result["emotion_confidence"],
    }

    if image_paths:
        updates["user_input"] = user_input
        updates["vision_result"] = vision_result

    return updates


# ── Crisis detection ──────────────────────────────────────────────────────────
_CRISIS_PATTERNS = [
    r"活着.*没.*意思", r"不想.*活", r"去死", r"伤害.*自己", r"结束.*生命",
    r"no\s*point\s*living", r"want\s*to\s*die", r"hurt\s*myself", r"end\s*my\s*life",
]


def is_crisis(text: str) -> bool:
    """Check for suicide/self-harm crisis keywords."""
    return any(re.search(p, text) for p in _CRISIS_PATTERNS)


def _crisis_response(state: ChatState) -> dict:
    """Generate crisis response. Called when triage detects crisis."""
    profile = state.get("user_profile", {})
    name = profile.get("name", "您")
    language = profile.get("language", "Chinese")

    response = (
        f"{name}，您刚才说的话让我很担心。"
        "您的生命很重要，您不需要一个人扛着这些。"
        "请拨打新加坡心理援助热线：1-767（24小时）或 IMH：6389 2222。"
        "我在这里陪您——能告诉我，是什么让您有这样的感受吗？"
    ) if language != "English" else (
        "I'm really concerned about what you said. You matter and you're not alone. "
        "Please call Samaritans of Singapore: 1-767 (24hr) or IMH: 6389 2222."
    )

    return {
        "response": response,
        "intent": "crisis",
    }


def triage_node(state: ChatState) -> dict:
    user_input = state["user_input"]
    # Crisis check first — short-circuits entire pipeline
    if is_crisis(user_input):
        print(f"[Triage] ⚠️ 心理危机检测触发")
        get_health_store().log_emotion(state["user_id"], state.get("emotion_label", "neutral"), user_input)
        return _crisis_response(state)
    return _full_triage(state)



# ── Keyword pre-classification ────────────────────────────────────────────
# 只识别 medical（路由到 expert），其余由 companion 兜底
KEYWORD_RULES = [
    ("medical", [
        "血糖", "glucose", "sugar", "药", "medicine", "metformin",
        "二甲双胍", "饮食", "diet", "吃了什么", "GI", "升糖", "HbA1c", "hba1c",
        "糖化", "胰岛素", "insulin", "blood pressure", "血压", "症状", "symptom",
    ]),
]

def keyword_preclassify(user_input: str) -> Optional[str]:
    """Classify intent by keywords. Returns intent string or None (fall back to LLM)."""
    text = user_input.lower()
    for intent, keywords in KEYWORD_RULES:
        for kw in keywords:
            if re.search(kw, text):
                return intent
    return None


def _full_triage(state: ChatState) -> dict:
    """意图判断：关键词预分类 + LLM兜底。情绪由 input_node 已通过 MERaLiON 设好。"""
    emotion_label = state.get("emotion_label", "neutral")
    user_input    = state["user_input"]

    # ── Step 1: Try keyword pre-classification ──────────
    keyword_intent = keyword_preclassify(user_input)
    if keyword_intent:
        get_health_store().log_emotion(state["user_id"], emotion_label, user_input)
        print(f"[Triage] 关键词命中：{keyword_intent} | 情绪：{emotion_label}")
        return {
            "intent":        keyword_intent,
            "all_intents":   [keyword_intent],
            "emotion_label": emotion_label,
        }

    # ── Step 2: LLM 只判意图，情绪用关键词 ──────────────
    system_prompt = """你是医疗健康助手的分诊系统，服务于新加坡的慢性病患者。
结合【最近对话】和【当前消息】，判断用户意图，返回JSON：
{"intents": ["标签"]}

意图标签（二选一）：
- medical    （血糖、血压、药物、饮食建议、症状、身体不适等任何健康医疗话题）
- companion  （情绪倾诉、日常闲聊、问候、确认词、其他非医疗话题）

规则：
- 只返回一个标签
- 有任何医疗/健康相关内容，优先归为 medical
- 只返回JSON，不要任何解释"""

    history = state.get("history", [])
    recent  = history[-4:] if len(history) >= 4 else history
    context = ""
    if recent:
        context = "【最近对话】\n"
        for h in recent:
            role     = "用户" if h["role"] == "user" else "助手"
            context += f"{role}：{h['content']}\n"
        context += "\n【当前消息】\n"

    raw = call_sealion(system_prompt, context + user_input)

    try:
        clean   = raw.strip().replace("```json","").replace("```","").strip()
        data    = json.loads(clean)
        intents = [i for i in data.get("intents", []) if i in ALL_INTENTS]
    except Exception:
        intents = []

    if not intents:
        intents = [INTENT_COMPANION]

    get_health_store().log_emotion(state["user_id"], emotion_label, user_input)
    print(f"[Triage] 意图：{intents} | 情绪：{emotion_label}")
    return {
        "intent":        intents[0],
        "all_intents":   intents,
        "emotion_label": emotion_label,
    }


def route_by_intent(state: ChatState) -> str:
    intent = state.get("intent", "companion")
    return "expert_agent" if intent == "medical" else "companion_agent"
