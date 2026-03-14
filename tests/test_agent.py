"""Tests for VisionAgent high-level API."""

import pytest

from src.vision_agent.agent import AnalysisResult, VisionAgent
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.schemas.outputs import (
    FoodOutput,
    MedicationOutput,
    ReportOutput,
    UnknownOutput,
)


class TestVisionAgentInit:
    def test_defaults_to_mock_vlm(self):
        agent = VisionAgent()
        assert agent.model_name == "mock-vlm-v1"

    def test_accepts_custom_vlm(self):
        vlm = MockVLM(forced_scene="FOOD")
        agent = VisionAgent(vlm=vlm)
        assert agent.model_name == "mock-vlm-v1"


class TestVisionAgentAnalyze:
    def test_food_scene_returns_food_result(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze(mock_image_path)
        assert isinstance(result, AnalysisResult)
        assert result.scene_type == "FOOD"
        assert result.is_food
        assert not result.is_medication
        assert not result.is_unknown
        assert not result.is_error

    def test_food_result_typed_output(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze(mock_image_path)
        assert isinstance(result.as_food, FoodOutput)
        assert result.as_medication is None
        assert result.as_report is None

    def test_medication_scene(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="MEDICATION"))
        result = agent.analyze(mock_image_path)
        assert result.is_medication
        assert isinstance(result.as_medication, MedicationOutput)
        assert result.as_medication.drug_name == "Metformin Hydrochloride"

    def test_report_scene(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="REPORT"))
        result = agent.analyze(mock_image_path)
        assert result.is_report
        assert isinstance(result.as_report, ReportOutput)
        assert len(result.as_report.indicators) > 0

    def test_unknown_scene(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="UNKNOWN"))
        result = agent.analyze(mock_image_path)
        assert result.is_unknown
        assert result.as_food is None
        assert result.as_medication is None

    def test_error_on_missing_file(self):
        agent = VisionAgent(vlm=MockVLM())
        result = agent.analyze("/nonexistent/path/image.jpg")
        assert result.is_error
        assert result.structured_output is None
        assert result.error is not None

    def test_confidence_populated(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze(mock_image_path)
        assert 0.0 < result.confidence <= 1.0

    def test_image_path_in_result(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze(mock_image_path)
        assert mock_image_path in result.image_path

    def test_analyze_accepts_string(self, mock_image_path):
        """Single string path should work (backward compat)."""
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze(mock_image_path)
        assert not result.is_multi_image
        assert result.image_path != ""

    def test_analyze_accepts_list(self, mock_image_path):
        """List of paths should work."""
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze([mock_image_path])
        assert not result.is_multi_image

    def test_analyze_multi_image(self, mock_image_path):
        """Multiple paths should mark is_multi_image=True."""
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        result = agent.analyze([mock_image_path, mock_image_path])
        assert result.is_multi_image
        assert len(result.image_paths) == 2
        # Backward compat: image_path returns first
        assert result.image_path == result.image_paths[0]


class TestAnalysisResultHelpers:
    def _make_food_result(self, mock_image_path) -> AnalysisResult:
        agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD"))
        return agent.analyze(mock_image_path)

    def test_food_total_calories(self, mock_image_path):
        result = self._make_food_result(mock_image_path)
        food = result.as_food
        assert food is not None
        assert food.total_calories > 0
        assert food.gi_level in ("high", "medium", "low")

    def test_report_abnormal_indicators(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="REPORT"))
        result = agent.analyze(mock_image_path)
        report = result.as_report
        assert report is not None
        abnormal = [i for i in report.indicators if i.is_abnormal]
        assert len(abnormal) > 0  # Mock data has abnormal HbA1c

    def test_medication_has_drug_name(self, mock_image_path):
        agent = VisionAgent(vlm=MockVLM(forced_scene="MEDICATION"))
        result = agent.analyze(mock_image_path)
        med = result.as_medication
        assert med is not None
        assert len(med.drug_name) > 0

    def test_image_path_property_backward_compat(self, mock_image_path):
        result = self._make_food_result(mock_image_path)
        # image_path should return first path from image_paths
        assert result.image_path == result.image_paths[0]
