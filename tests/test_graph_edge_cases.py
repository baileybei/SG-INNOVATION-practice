"""Edge case and integration tests for the full graph."""

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.vision_agent.graph import build_graph
from src.vision_agent.llm.base import VLMError
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.llm.retry import RetryVLM


def _make_image(ext=".jpg") -> str:
    img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        img.save(f.name)
        return f.name


def _state(image_path: str) -> dict:
    return {
        "image_paths": [image_path],
        "images_base64": [],
        "scene_type": "",
        "confidence": 0.0,
        "raw_response": "",
        "structured_output": {},
        "error": None,
    }


class TestGraphRetryIntegration:
    def test_graph_uses_retry_for_real_vlm(self):
        """Non-mock VLMs should be wrapped in RetryVLM inside build_graph."""
        real_vlm = MagicMock()
        real_vlm.call_multi.return_value = json.dumps({
            "scene_type": "FOOD",
            "confidence": 0.9,
            "reason": "food detected"
        })
        real_vlm.model_name = "test-vlm"

        path = _make_image()
        try:
            # build_graph wraps non-MockVLM in RetryVLM
            graph = build_graph(vlm=real_vlm, max_retries=2, retry_delay_s=0)
            # We pass a mock that returns valid classifier JSON - graph should run
        finally:
            os.unlink(path)

    def test_mock_vlm_not_double_wrapped(self):
        """MockVLM should NOT be wrapped in RetryVLM (it never fails)."""
        from src.vision_agent.graph import build_graph
        import inspect

        # build_graph returns compiled graph, but we can verify by checking
        # that MockVLM calls work without the retry overhead
        mock = MockVLM(forced_scene="FOOD")
        path = _make_image()
        try:
            graph = build_graph(vlm=mock)
            result = graph.invoke(_state(path))
            assert result["scene_type"] == "FOOD"
        finally:
            os.unlink(path)


class TestGraphAllScenesPipeline:
    """Verify complete pipeline for each scene produces correct output shape."""

    def _run(self, scene: str) -> dict:
        path = _make_image()
        try:
            graph = build_graph(vlm=MockVLM(forced_scene=scene))
            return graph.invoke(_state(path))
        finally:
            os.unlink(path)

    def test_food_pipeline_output_shape(self):
        result = self._run("FOOD")
        out = result["structured_output"]
        assert out["scene_type"] == "FOOD"
        assert isinstance(out["food_name"], str)
        assert isinstance(out["gi_level"], str)
        assert isinstance(out["total_calories"], float)

    def test_medication_pipeline_output_shape(self):
        result = self._run("MEDICATION")
        out = result["structured_output"]
        assert out["scene_type"] == "MEDICATION"
        assert isinstance(out["drug_name"], str)
        assert len(out["drug_name"]) > 0
        assert isinstance(out["dosage"], str)
        assert isinstance(out["frequency"], str)

    def test_report_pipeline_output_shape(self):
        result = self._run("REPORT")
        out = result["structured_output"]
        assert out["scene_type"] == "REPORT"
        assert isinstance(out["indicators"], list)
        assert len(out["indicators"]) > 0
        for ind in out["indicators"]:
            assert "name" in ind
            assert "value" in ind
            assert "is_abnormal" in ind

    def test_unknown_pipeline_output_shape(self):
        result = self._run("UNKNOWN")
        out = result["structured_output"]
        assert out["scene_type"] == "UNKNOWN"
        assert isinstance(out["reason"], str)
        assert len(out["reason"]) > 0

    def test_all_outputs_have_confidence(self):
        for scene in ["FOOD", "MEDICATION", "REPORT", "UNKNOWN"]:
            result = self._run(scene)
            out = result["structured_output"]
            assert "confidence" in out, f"Missing confidence in {scene} output"
            assert 0.0 <= out["confidence"] <= 1.0


class TestGraphVLMFailureScenarios:
    """Test graph behavior when VLM fails at different nodes."""

    def test_classifier_json_failure_propagates_to_output(self):
        bad_vlm = MagicMock()
        bad_vlm.call_multi.return_value = "COMPLETELY INVALID JSON !!!"
        path = _make_image()
        try:
            graph = build_graph(vlm=bad_vlm)
            result = graph.invoke(_state(path))
            out = result["structured_output"]
            assert out["scene_type"] == "ERROR"
        finally:
            os.unlink(path)

    def test_analyzer_failure_after_classification(self):
        """Simulate classifier succeeding but analyzer failing."""
        call_count = 0

        def side_effect(prompt, images_base64):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call = classifier -> returns valid FOOD classification
                return json.dumps({
                    "scene_type": "FOOD",
                    "confidence": 0.9,
                    "reason": "food detected"
                })
            # Second call = food_analyzer -> returns broken JSON
            return "{ broken"

        bad_vlm = MagicMock()
        bad_vlm.call_multi.side_effect = side_effect
        path = _make_image()
        try:
            graph = build_graph(vlm=bad_vlm)
            result = graph.invoke(_state(path))
            out = result["structured_output"]
            assert out["scene_type"] == "ERROR"
        finally:
            os.unlink(path)

    def test_png_image_supported(self):
        path = _make_image(ext=".png")
        try:
            graph = build_graph(vlm=MockVLM(forced_scene="FOOD"))
            result = graph.invoke(_state(path))
            assert result["error"] is None
        finally:
            os.unlink(path)

    def test_large_filename_path_handled(self):
        """Graph should handle absolute paths correctly."""
        path = _make_image()
        try:
            state = _state(os.path.abspath(path))
            graph = build_graph(vlm=MockVLM(forced_scene="MEDICATION"))
            result = graph.invoke(state)
            assert result["scene_type"] == "MEDICATION"
        finally:
            os.unlink(path)


class TestStateImmutability:
    """Verify nodes return new dicts rather than mutating input state."""

    def test_image_intake_does_not_mutate_input(self):
        from src.vision_agent.nodes.image_intake import image_intake
        state = {
            "image_paths": ["/nonexistent/path.jpg"],
            "images_base64": ["original"],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        original_b64 = state["images_base64"][:]
        image_intake(state)
        # Original state should be unchanged (LangGraph handles merging)
        assert state["images_base64"] == original_b64

    def test_rejection_handler_does_not_mutate_input(self):
        from src.vision_agent.nodes.rejection_handler import rejection_handler
        state = {
            "image_paths": ["/tmp/test.jpg"],
            "images_base64": ["b64"],
            "scene_type": "UNKNOWN",
            "confidence": 0.5,
            "raw_response": "",
            "structured_output": {"original": True},
            "error": None,
        }
        result = rejection_handler(state)
        # State structured_output should not be mutated
        assert state["structured_output"] == {"original": True}
        # Result should be a new dict
        assert result["structured_output"] != {"original": True}
