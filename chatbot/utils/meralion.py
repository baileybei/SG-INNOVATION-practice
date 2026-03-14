"""
utils/meralion.py
MERaLiON API 集成
- 语音输入：base64编码音频 → 转录 + 情绪识别（官方模板）
- 文字输入：纯文本 → 语义情绪识别
logprob 解析：扫 top_logprobs 取第一个合法情绪标签
"""
import base64
import math
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MERALION_BASE_URL = os.getenv("MERALION_BASE_URL", "http://meralion.org:8010")
MERALION_API_KEY  = os.getenv("MERALION_API_KEY", "Xiaobei-l5hI1RJwg1qrNL6YxeV5LTREBwhBNHHo")
MERALION_MODEL    = os.getenv("MERALION_MODEL", "MERaLiON/MERaLiON-2-10B")

CONFIDENCE_THRESHOLD = 0.4
VALID_EMOTIONS = {"angry", "sad", "fearful", "happy", "neutral"}

# 官方语音 prompt 模板
_AUDIO_PROMPT = "Instruction: {query} \nFollow the text instruction based on the following audio: <SpeechHere>"
_EMOTION_QUERY = "Analyze the speaker's emotion from both tone and content. Reply with a single word only, one of: angry sad fearful happy neutral"


def _parse_emotion_from_logprobs(data: dict) -> tuple[str, float]:
    """
    从 top_logprobs 扫描，取第一个在 VALID_EMOTIONS 里的候选及其概率。
    模型有时输出截断词（'an'、'frust'），直接取 content 字段不可靠。
    """
    try:
        top = data["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
        for candidate in top:
            token = candidate["token"].strip().lower()
            prob  = math.exp(candidate["logprob"])
            if token in VALID_EMOTIONS:
                return token, prob
    except (KeyError, IndexError, TypeError):
        pass
    # fallback：取 content 字段
    raw = data["choices"][0]["message"]["content"].strip().lower()
    return ("neutral", 0.0) if raw not in VALID_EMOTIONS else (raw, 0.5)


# ── 语音相关 ──────────────────────────────────────────────────────

def _call_audio_api(audio_b64: str, content_type: str, query: str,
                    max_tokens: int, logprobs: bool = False) -> dict:
    resp = requests.post(
        f"{MERALION_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {MERALION_API_KEY}"},
        json={
            "model": MERALION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _AUDIO_PROMPT.format(query=query)},
                    {"type": "audio_url", "audio_url": {"url": f"data:{content_type};base64,{audio_b64}"}},
                ],
            }],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "logprobs": logprobs,
            "top_logprobs": 5 if logprobs else 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _transcribe(audio_b64: str, content_type: str) -> str:
    data = _call_audio_api(audio_b64, content_type,
                           query="Please transcribe this speech.",
                           max_tokens=256, logprobs=False)
    text = data["choices"][0]["message"]["content"].strip()
    print(f"[MERaLiON] 转录完成：{text[:60]}{'...' if len(text) > 60 else ''}")
    return text


def _analyze_audio_emotion(audio_b64: str, content_type: str) -> tuple[str, float]:
    data = _call_audio_api(audio_b64, content_type,
                           query=_EMOTION_QUERY, max_tokens=5, logprobs=True)
    emotion_label, confidence = _parse_emotion_from_logprobs(data)
    if confidence < CONFIDENCE_THRESHOLD:
        emotion_label = "neutral"
    print(f"[MERaLiON] 语音情绪：{emotion_label}（置信度{confidence:.3f}）")
    return emotion_label, confidence


def process_voice_input(audio_path: str) -> dict:
    """音频文件路径 → 转录文字 + 情绪标签"""
    try:
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        content_type = "audio/wav" if audio_path.lower().endswith(".wav") else "audio/mpeg"
        transcribed_text          = _transcribe(audio_b64, content_type)
        emotion_label, confidence = _analyze_audio_emotion(audio_b64, content_type)
        return {
            "transcribed_text":   transcribed_text,
            "emotion_label":      emotion_label,
            "emotion_confidence": confidence,
        }
    except Exception as e:
        print(f"[MERaLiON] 语音调用失败：{e}")
        return {"transcribed_text": "", "emotion_label": "neutral", "emotion_confidence": 0.0}


# ── 文字情绪识别 ──────────────────────────────────────────────────

def _analyze_text_emotion(text: str) -> tuple[str, float]:
    resp = requests.post(
        f"{MERALION_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {MERALION_API_KEY}"},
        json={
            "model": MERALION_MODEL,
            "messages": [{
                "role": "user",
                "content": (
                    "Analyze the emotion in the following text. "
                    "Reply with a single word only, one of: angry sad fearful happy neutral\n"
                    f"Text: {text}"
                ),
            }],
            "temperature": 0.0,
            "max_tokens": 5,
            "logprobs": True,
            "top_logprobs": 5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    emotion_label, confidence = _parse_emotion_from_logprobs(data)
    if confidence < CONFIDENCE_THRESHOLD:
        emotion_label = "neutral"
    print(f"[MERaLiON] 文字情绪：{emotion_label}（置信度{confidence:.3f}）")
    return emotion_label, confidence


def process_text_input(text: str) -> dict:
    """文字内容 → 情绪标签（语义识别）"""
    try:
        emotion_label, confidence = _analyze_text_emotion(text)
        return {"emotion_label": emotion_label, "emotion_confidence": confidence}
    except Exception as e:
        print(f"[MERaLiON] 文字情绪调用失败：{e}")
        return {"emotion_label": "neutral", "emotion_confidence": 0.0}


# ── Mock模式 ──────────────────────────────────────────────────────
def process_voice_input_mock(audio_path: str) -> dict:
    print(f"[MERaLiON Mock] 处理：{audio_path}")
    return {"transcribed_text": "我今天血糖有点高，很担心", "emotion_label": "fearful", "emotion_confidence": 0.82}


def process_text_input_mock(text: str) -> dict:
    print(f"[MERaLiON Mock] 文字情绪：{text[:30]}")
    return {"emotion_label": "neutral", "emotion_confidence": 0.85}
