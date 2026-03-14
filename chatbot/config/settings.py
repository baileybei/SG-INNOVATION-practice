"""
全局配置：模型名称、API地址、参数
"""
import os
from dotenv import load_dotenv

load_dotenv()


# 环境模式
ENV = os.getenv("ENV", "development")
IS_DEV = ENV == "development"


# SEA-LION 配置（对话推理主模型）
SEALION_API_KEY = os.getenv("SEALION_API_KEY", "")
SEALION_BASE_URL = os.getenv("SEALION_BASE_URL", "https://api.sea-lion.ai/v1")

SEALION_INSTRUCT_MODEL = "aisingapore/Qwen-SEA-LION-v4-32B-IT" # 患者交互用 Instruct 模型
SEALION_REASONING_MODEL = "aisingapore/Llama-SEA-LION-v3.5-70B-R" # 专家/预警 用 Reasoning 模型


# MERaLiON 配置（语音情绪识别）
MERALION_API_KEY = os.getenv("MERALION_API_KEY", "Xiaobei-l5hI1RJwg1qrNL6YxeV5LTREBwhBNHHo")
MERALION_BASE_URL = os.getenv("MERALION_BASE_URL", "http://meralion.org:8010")

MERALION_MODEL = "MERaLiON/MERaLiON-2-10B"  # chat completions 情绪识别


# 备用：OpenAI（SEA-LION API 未就绪时使用）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FALLBACK_MODEL = "gpt-4o-mini"


# 对话记忆配置
MAX_HISTORY_TURNS = 6    # 保留最近N轮对话（太长浪费token）
MAX_HISTORY_CHARS = 2000 # 历史字符上限


# 意图类别（两分类：医疗 vs 陪伴）
INTENT_MEDICAL   = "medical"     # 血糖、药物、饮食建议、症状等医疗话题
INTENT_COMPANION = "companion"   # 其余所有话题（情绪、闲聊、问候等）

ALL_INTENTS = [
    INTENT_MEDICAL,
    INTENT_COMPANION,
]


# 情绪类别（MERaLiON SER 输出）
EMOTION_LABELS = [
    "neutral",
    "happy",
    "sad",
    "fearful",
    "angry",
]

def get_active_api_key() -> str:
    """根据环境返回当前可用的 API Key"""
    if SEALION_API_KEY:
        return SEALION_API_KEY
    if OPENAI_API_KEY:
        return OPENAI_API_KEY
    raise ValueError("未配置任何 API Key，请检查 .env 文件")

def get_active_base_url() -> str | None:
    """根据环境返回当前可用的 base_url"""
    if SEALION_API_KEY:
        return SEALION_BASE_URL
    return None  # OpenAI 不需要 base_url
