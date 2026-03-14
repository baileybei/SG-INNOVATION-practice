"""Tests for output_formatter and rejection_handler nodes."""

import pytest

from src.vision_agent.nodes.output_formatter import _MAX_NULL_PENALTY, _adjust_confidence, output_formatter
from src.vision_agent.nodes.rejection_handler import rejection_handler


def _state(structured_output=None, error=None, scene_type="FOOD", confidence=0.9):
    return {
        "image_paths": ["/tmp/test.jpg"],
        "images_base64": ["b64"],
        "scene_type": scene_type,
        "confidence": confidence,
        "raw_response": "",
        "structured_output": structured_output or {},
        "error": error,
    }


class TestOutputFormatter:
    def test_passes_through_valid_output(self):
        state = _state(structured_output={
            "scene_type": "FOOD",
            "confidence": 0.9,
            "food_name": "Test",
            "gi_level": "low",
            "total_calories": 0.0,
        })
        result = output_formatter(state)
        assert result["structured_output"]["scene_type"] == "FOOD"

    def test_error_state_returns_error_envelope(self):
        state = _state(error="something went wrong")
        result = output_formatter(state)
        out = result["structured_output"]
        assert out["scene_type"] == "ERROR"
        assert "something went wrong" in out["error"]
        assert out["confidence"] == 0.0

    def test_missing_scene_type_returns_error(self):
        state = _state(structured_output={"confidence": 0.9})  # missing scene_type
        result = output_formatter(state)
        out = result["structured_output"]
        assert out["scene_type"] == "ERROR"
        assert "missing required fields" in out["error"]

    def test_missing_confidence_returns_error(self):
        state = _state(structured_output={"scene_type": "FOOD"})  # missing confidence
        result = output_formatter(state)
        out = result["structured_output"]
        assert out["scene_type"] == "ERROR"

    def test_empty_structured_output_returns_error(self):
        state = _state(structured_output={})
        result = output_formatter(state)
        assert result["structured_output"]["scene_type"] == "ERROR"


class TestConfidenceAdjustment:
    def test_medication_all_optional_null_reduces_confidence(self):
        output = {
            "scene_type": "MEDICATION",
            "confidence": 0.98,
            "drug_name": "Metformin",
            "dosage": "500mg",
            "frequency": None,
            "route": None,
            "warnings": None,
            "expiry_date": None,
            "ingredients": None,
        }
        adjusted = _adjust_confidence(output)
        assert adjusted["confidence"] < 0.98
        assert adjusted["confidence"] == round(0.98 - _MAX_NULL_PENALTY, 4)

    def test_medication_all_optional_filled_keeps_confidence(self):
        output = {
            "scene_type": "MEDICATION",
            "confidence": 0.98,
            "drug_name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
            "route": "oral",
            "warnings": ["take with food"],
            "expiry_date": "2026-01",
            "ingredients": None,  # None is expected for prescription drugs
        }
        # Only ingredients is None (1/5 fields)
        adjusted = _adjust_confidence(output)
        expected = round(0.98 - (1 / 5) * _MAX_NULL_PENALTY, 4)
        assert adjusted["confidence"] == expected

    def test_unknown_scene_confidence_unchanged(self):
        output = {"scene_type": "UNKNOWN", "confidence": 0.85, "reason": "not food"}
        adjusted = _adjust_confidence(output)
        assert adjusted["confidence"] == 0.85

    def test_confidence_never_below_zero(self):
        output = {
            "scene_type": "MEDICATION",
            "confidence": 0.05,
            "drug_name": "X",
            "dosage": "1mg",
            "frequency": None,
            "route": None,
            "warnings": None,
            "expiry_date": None,
            "ingredients": None,
        }
        adjusted = _adjust_confidence(output)
        assert adjusted["confidence"] >= 0.0

    def test_output_formatter_applies_adjustment(self):
        state = _state(structured_output={
            "scene_type": "MEDICATION",
            "confidence": 0.98,
            "drug_name": "Metformin",
            "dosage": "500mg",
            "frequency": None,
            "route": None,
            "warnings": None,
            "expiry_date": None,
            "ingredients": None,
        })
        result = output_formatter(state)
        assert result["structured_output"]["confidence"] < 0.98


class TestRejectionHandler:
    def test_returns_unknown_output(self):
        state = _state(scene_type="UNKNOWN", confidence=0.85)
        result = rejection_handler(state)
        out = result["structured_output"]
        assert out["scene_type"] == "UNKNOWN"
        assert "reason" in out
        assert len(out["reason"]) > 0

    def test_error_is_none(self):
        state = _state(scene_type="UNKNOWN")
        result = rejection_handler(state)
        assert result["error"] is None

    def test_confidence_preserved(self):
        state = _state(scene_type="UNKNOWN", confidence=0.73)
        result = rejection_handler(state)
        assert result["structured_output"]["confidence"] == 0.73

    def test_reason_mentions_upload_instruction(self):
        state = _state(scene_type="UNKNOWN")
        result = rejection_handler(state)
        reason = result["structured_output"]["reason"]
        assert "upload" in reason.lower() or "please" in reason.lower()
