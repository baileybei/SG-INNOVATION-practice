"""Tests for scene_classifier node."""

import json
from unittest.mock import MagicMock

import pytest

from src.vision_agent.llm.base import VLMError
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.nodes.scene_classifier import make_scene_classifier


def _state(scene_type="", error=None, images_base64=None):
    return {
        "image_paths": ["/tmp/test.jpg"],
        "images_base64": images_base64 if images_base64 is not None else ["b64data"],
        "scene_type": scene_type,
        "confidence": 0.0,
        "raw_response": "",
        "structured_output": {},
        "error": error,
    }


class TestSceneClassifier:
    def test_food_classification(self):
        node = make_scene_classifier(MockVLM(forced_scene="FOOD"))
        result = node(_state())
        assert result["scene_type"] == "FOOD"
        assert result["confidence"] > 0
        assert result["error"] is None

    def test_medication_classification(self):
        node = make_scene_classifier(MockVLM(forced_scene="MEDICATION"))
        result = node(_state())
        assert result["scene_type"] == "MEDICATION"

    def test_report_classification(self):
        node = make_scene_classifier(MockVLM(forced_scene="REPORT"))
        result = node(_state())
        assert result["scene_type"] == "REPORT"

    def test_unknown_classification(self):
        node = make_scene_classifier(MockVLM(forced_scene="UNKNOWN"))
        result = node(_state())
        assert result["scene_type"] == "UNKNOWN"

    def test_skips_when_error_in_state(self):
        node = make_scene_classifier(MockVLM(forced_scene="FOOD"))
        result = node(_state(error="upstream error"))
        # Should return empty dict (no-op) when error already present
        assert result == {}

    def test_invalid_json_returns_error(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = "this is not json at all"
        node = make_scene_classifier(bad_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "invalid JSON" in result["error"]
        assert result["scene_type"] == "UNKNOWN"

    def test_vlm_error_returns_error(self):
        failing_vlm = MagicMock()
        failing_vlm.call_multi.side_effect = VLMError("API timeout")
        node = make_scene_classifier(failing_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "scene_classifier" in result["error"]
        assert result["scene_type"] == "UNKNOWN"

    def test_unknown_scene_type_normalized(self):
        weird_vlm = MagicMock()
        weird_vlm.call_multi.return_value = json.dumps({
            "scene_type": "SELFIE",
            "confidence": 0.5,
            "reason": "It's a selfie"
        })
        node = make_scene_classifier(weird_vlm)
        result = node(_state())
        assert result["scene_type"] == "UNKNOWN"

    def test_raw_response_stored(self):
        node = make_scene_classifier(MockVLM(forced_scene="FOOD"))
        result = node(_state())
        assert result["raw_response"] != ""
        data = json.loads(result["raw_response"])
        assert "scene_type" in data
