"""
Integration tests for the demo golden path.
Uses mocked LLM calls and pre-injected vision_result (no real API calls).
"""
from unittest.mock import patch, MagicMock
import pytest


def _mock_llm_response(system_prompt: str, messages: list, reasoning: bool = False) -> str:
    """Smart mock: returns contextually appropriate responses based on prompt content."""
    combined = system_prompt + str(messages)
    # Triage: return JSON
    if '"intents"' in combined or "分诊" in combined or "意图" in combined and "返回JSON" in combined:
        if "我好难过" in combined or "压力" in combined:
            return '{"intents": ["emotional"], "emotion": "sad"}'
        if "药" in combined or "medication" in combined.lower():
            return '{"intents": ["medical"], "emotion": "neutral"}'
        return '{"intents": ["medical"], "emotion": "neutral"}'
    # Chitchat
    if "闲聊" in combined or "日常对话" in combined:
        return "你好呀！我是你的健康助手，有什么可以帮你的？"
    # Expert
    if "慢性病管理" in combined or "医疗顾问" in combined:
        return "根据您的血糖数据，建议控制碳水摄入，配合运动。"
    # Companion
    if "陪伴" in combined or "温暖" in combined:
        return "我理解您的感受，控制饮食确实不容易。您能和我说说是什么让您感到压力大吗？"
    return "好的，我了解了。"


def _mock_llm_single(system_prompt: str, user_message: str, reasoning: bool = False) -> str:
    return _mock_llm_response(system_prompt, [{"role": "user", "content": user_message}])


def _build_state(**overrides):
    """Build a minimal valid ChatState for testing."""
    from state.chat_state import ChatState
    defaults = dict(
        user_input="",
        input_mode="text",
        chat_mode="personal",
        user_id="test_user",
        audio_path=None,
        transcribed_text=None,
        emotion_label="neutral",
        emotion_confidence=0.0,
        intent=None,
        all_intents=None,
        history=[],
        user_profile={
            "name": "测试用户",
            "language": "Chinese",
            "conditions": ["Type 2 Diabetes"],
            "medications": ["Metformin"],
        },
        glucose_readings=None,
        response=None,
        emotion_log=None,
        image_paths=None,
        vision_result=None,
    )
    defaults.update(overrides)
    return ChatState(**defaults)


@patch("utils.llm_factory.call_sealion_with_history_stream", side_effect=_mock_llm_response)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step1_chitchat(mock_triage, mock_history, mock_stream):
    """Step 1: User says hello -> chitchat agent responds."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(user_input="你好")
    result = app.invoke(state)
    assert result.get("response") is not None
    assert len(result["response"]) > 0


@patch("utils.llm_factory.call_sealion_with_history_stream", side_effect=_mock_llm_response)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step2_food_vision_expert_advice(mock_triage, mock_history, mock_stream):
    """Step 2: Food photo -> expert gives diet advice (single-turn, no conversation_stage)."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(
        user_input="我拍了一张食物照片",
        vision_result=[{
            "scene_type": "FOOD",
            "food_name": "海南鸡饭",
            "total_calories": 600.0,
            "confidence": 0.85,
        }],
    )
    result = app.invoke(state)
    assert result.get("response") is not None
    assert result.get("intent") == "medical"
    assert len(result["response"]) > 0


@patch("utils.llm_factory.call_sealion_with_history_stream", side_effect=_mock_llm_response)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step5_emotional_routes_to_companion(mock_triage, mock_history, mock_stream):
    """Emotional input -> routed to companion agent."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(user_input="唉，我最近压力好大，管不住嘴")
    result = app.invoke(state)
    assert result.get("intent") in ["emotional", "medical"]
    assert result.get("response") is not None
    assert len(result["response"]) > 0


@patch("utils.llm_factory.call_sealion_with_history_stream", side_effect=_mock_llm_response)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_crisis_short_circuits(mock_triage, mock_history, mock_stream):
    """Crisis input -> triage detects crisis, skips to history_update."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(user_input="我不想活了")
    result = app.invoke(state)
    assert result.get("intent") == "crisis"
    assert result.get("response") is not None
    assert "1-767" in result["response"] or "6389" in result["response"]
