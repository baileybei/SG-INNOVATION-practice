"""Integration tests for the full LangGraph Vision Agent.

Uses shared fixtures from conftest.py.
"""

import os
import tempfile

import pytest
from PIL import Image

from src.vision_agent.graph import build_graph
from src.vision_agent.llm.mock import MockVLM


def _make_test_image() -> str:
    img = Image.new("RGB", (100, 100), color=(0, 128, 0))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f.name)
        return f.name


class TestGraphFoodPath:
    def test_food_image_returns_structured_output(self, food_graph, base_state):
        result = food_graph.invoke(base_state)
        assert result["error"] is None
        assert result["scene_type"] == "FOOD"
        output = result["structured_output"]
        assert output["scene_type"] == "FOOD"
        assert "food_name" in output
        assert output["total_calories"] > 0

    def test_food_output_has_confidence(self, food_graph, base_state):
        result = food_graph.invoke(base_state)
        assert 0.0 < result["structured_output"]["confidence"] <= 1.0


class TestGraphMedicationPath:
    def test_medication_image_returns_structured_output(self, medication_graph, base_state):
        result = medication_graph.invoke(base_state)
        assert result["error"] is None
        assert result["scene_type"] == "MEDICATION"
        output = result["structured_output"]
        assert "drug_name" in output
        assert "dosage" in output

    def test_medication_has_frequency(self, medication_graph, base_state):
        result = medication_graph.invoke(base_state)
        assert "frequency" in result["structured_output"]


class TestGraphReportPath:
    def test_report_image_returns_structured_output(self, report_graph, base_state):
        result = report_graph.invoke(base_state)
        assert result["error"] is None
        assert result["scene_type"] == "REPORT"
        output = result["structured_output"]
        assert "indicators" in output
        assert len(output["indicators"]) > 0

    def test_report_indicators_have_required_fields(self, report_graph, base_state):
        result = report_graph.invoke(base_state)
        for ind in result["structured_output"]["indicators"]:
            assert "name" in ind
            assert "value" in ind
            assert "is_abnormal" in ind


class TestGraphUnknownPath:
    def test_unknown_image_returns_rejection(self, unknown_graph, base_state):
        result = unknown_graph.invoke(base_state)
        assert result["scene_type"] == "UNKNOWN"
        output = result["structured_output"]
        assert output["scene_type"] == "UNKNOWN"
        assert "reason" in output

    def test_unknown_reason_is_non_empty(self, unknown_graph, base_state):
        result = unknown_graph.invoke(base_state)
        assert len(result["structured_output"]["reason"]) > 10


class TestGraphErrorHandling:
    def test_missing_image_path_propagates_error(self):
        graph = build_graph(vlm=MockVLM())
        state = {
            "image_paths": [],
            "images_base64": [],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        result = graph.invoke(state)
        assert result["structured_output"]["scene_type"] == "ERROR"
        assert result["structured_output"]["error"] is not None

    def test_nonexistent_file_propagates_error(self):
        graph = build_graph(vlm=MockVLM())
        state = {
            "image_paths": ["/tmp/no_such_file_xyz.jpg"],
            "images_base64": [],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        result = graph.invoke(state)
        assert result["structured_output"]["scene_type"] == "ERROR"

    def test_default_vlm_is_mock(self, mock_image_path):
        graph = build_graph()  # No VLM passed → defaults to MockVLM
        state = {
            "image_paths": [mock_image_path],
            "images_base64": [],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        result = graph.invoke(state)
        assert "scene_type" in result

    def test_png_image_works(self, unknown_graph, mock_png_path):
        state = {
            "image_paths": [mock_png_path],
            "images_base64": [],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        result = unknown_graph.invoke(state)
        assert result["error"] is None
