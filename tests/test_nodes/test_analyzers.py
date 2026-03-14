"""Tests for food_analyzer, medication_reader, report_digitizer nodes."""

import json
from unittest.mock import MagicMock

import pytest

from src.vision_agent.llm.base import VLMError
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.nodes.food_analyzer import make_food_analyzer
from src.vision_agent.nodes.medication_reader import make_medication_reader
from src.vision_agent.nodes.report_digitizer import make_report_digitizer


def _state(error=None, images_base64=None):
    return {
        "image_paths": ["/tmp/test.jpg"],
        "images_base64": images_base64 if images_base64 is not None else ["b64data"],
        "scene_type": "FOOD",
        "confidence": 0.9,
        "raw_response": "",
        "structured_output": {},
        "error": error,
    }


# ─── food_analyzer ────────────────────────────────────────────────────────────

class TestFoodAnalyzer:
    def test_returns_structured_food_output(self):
        node = make_food_analyzer(MockVLM(forced_scene="FOOD"))
        result = node(_state())
        assert result["error"] is None
        output = result["structured_output"]
        assert output["scene_type"] == "FOOD"
        assert isinstance(output["food_name"], str)
        assert output["total_calories"] > 0

    def test_skips_on_existing_error(self):
        node = make_food_analyzer(MockVLM(forced_scene="FOOD"))
        result = node(_state(error="prior error"))
        assert result == {}

    def test_invalid_json_returns_error(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = "{ broken json ..."
        node = make_food_analyzer(bad_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "invalid JSON" in result["error"]

    def test_vlm_error_returns_error(self):
        failing = MagicMock()
        failing.call_multi.side_effect = VLMError("network timeout")
        node = make_food_analyzer(failing)
        result = node(_state())
        assert result["error"] is not None
        assert "food_analyzer" in result["error"]

    def test_validation_error_on_bad_schema(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = json.dumps({
            "scene_type": "FOOD",
            # missing required 'food_name', 'gi_level', 'total_calories'
            "confidence": 0.9,
        })
        node = make_food_analyzer(bad_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "validation" in result["error"].lower()

    def test_raw_response_stored(self):
        node = make_food_analyzer(MockVLM(forced_scene="FOOD"))
        result = node(_state())
        assert result["raw_response"] != ""


# ─── medication_reader ────────────────────────────────────────────────────────

class TestMedicationReader:
    def test_returns_structured_medication_output(self):
        node = make_medication_reader(MockVLM(forced_scene="MEDICATION"))
        result = node(_state())
        assert result["error"] is None
        output = result["structured_output"]
        assert output["scene_type"] == "MEDICATION"
        assert "drug_name" in output
        assert "dosage" in output

    def test_skips_on_existing_error(self):
        node = make_medication_reader(MockVLM(forced_scene="MEDICATION"))
        result = node(_state(error="prior error"))
        assert result == {}

    def test_invalid_json_returns_error(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = "NOT JSON"
        node = make_medication_reader(bad_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "invalid JSON" in result["error"]

    def test_vlm_error_returns_error(self):
        failing = MagicMock()
        failing.call_multi.side_effect = VLMError("API key invalid")
        node = make_medication_reader(failing)
        result = node(_state())
        assert result["error"] is not None
        assert "medication_reader" in result["error"]

    def test_validation_error_on_bad_schema(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = json.dumps({
            "scene_type": "MEDICATION",
            # missing drug_name, dosage, frequency
            "confidence": 0.8,
        })
        node = make_medication_reader(bad_vlm)
        result = node(_state())
        assert result["error"] is not None


# ─── report_digitizer ────────────────────────────────────────────────────────

class TestReportDigitizer:
    def test_returns_structured_report_output(self):
        node = make_report_digitizer(MockVLM(forced_scene="REPORT"))
        result = node(_state())
        assert result["error"] is None
        output = result["structured_output"]
        assert output["scene_type"] == "REPORT"
        assert isinstance(output["indicators"], list)
        assert len(output["indicators"]) > 0

    def test_skips_on_existing_error(self):
        node = make_report_digitizer(MockVLM(forced_scene="REPORT"))
        result = node(_state(error="prior error"))
        assert result == {}

    def test_invalid_json_returns_error(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = "invalid"
        node = make_report_digitizer(bad_vlm)
        result = node(_state())
        assert result["error"] is not None
        assert "invalid JSON" in result["error"]

    def test_vlm_error_returns_error(self):
        failing = MagicMock()
        failing.call_multi.side_effect = VLMError("server error 500")
        node = make_report_digitizer(failing)
        result = node(_state())
        assert result["error"] is not None
        assert "report_digitizer" in result["error"]

    def test_abnormal_indicators_flagged(self):
        node = make_report_digitizer(MockVLM(forced_scene="REPORT"))
        result = node(_state())
        indicators = result["structured_output"]["indicators"]
        hba1c = next((i for i in indicators if i["name"] == "HbA1c"), None)
        assert hba1c is not None
        assert hba1c["is_abnormal"] is True
