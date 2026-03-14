"""Test input_node image handling with mock Vision Agent."""
import sys
import os
from unittest.mock import patch, MagicMock
from state.chat_state import ChatState


def _make_state(**overrides):
    """Helper to create a minimal ChatState."""
    defaults = dict(
        user_input="",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
        image_paths=None,
        vision_result=None,
    )
    defaults.update(overrides)
    return ChatState(**defaults)


def test_input_node_text_only_unchanged():
    """Text-only input should pass through without calling Vision Agent."""
    from agents.triage import input_node

    state = _make_state(user_input="hello", image_paths=None)
    result = input_node(state)
    assert result.get("vision_result") is None or result.get("vision_result") == []
    assert "transcribed_text" in result


def test_input_node_image_calls_vision_agent():
    """Image input should call Vision Agent and store result."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "FOOD"
    mock_result.confidence = 0.85
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "FOOD",
        "items": [{"name": "Chicken Rice"}],
        "confidence": 0.85,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(user_input="", image_paths=["/tmp/food.jpg"])
        result = input_node(state)

    assert result["vision_result"] is not None
    assert len(result["vision_result"]) == 1
    assert result["vision_result"][0]["scene_type"] == "FOOD"


def test_input_node_image_no_text_generates_synthetic():
    """Image with no text should generate synthetic user_input."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "FOOD"
    mock_result.confidence = 0.85
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "FOOD",
        "confidence": 0.85,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(user_input="", image_paths=["/tmp/food.jpg"])
        result = input_node(state)

    assert result["user_input"] != ""
    assert "食物" in result["user_input"] or "food" in result["user_input"].lower()


def test_input_node_image_with_text_keeps_original():
    """Image with text should keep original user_input."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "MEDICATION"
    mock_result.confidence = 0.9
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "MEDICATION",
        "confidence": 0.9,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(
            user_input="this is my medicine",
            image_paths=["/tmp/med.jpg"],
        )
        result = input_node(state)

    assert "user_input" in result
    assert result["user_input"] == "this is my medicine"
    assert result["vision_result"] is not None
