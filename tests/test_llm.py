"""Tests for LLM interface layer."""

import json
import pytest

from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.llm.mock import MockVLM


class TestBaseVLM:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseVLM()  # type: ignore

    def test_call_multi_default_uses_first_image(self):
        """Default call_multi() should delegate to call() with images_base64[0]."""
        class StubVLM(BaseVLM):
            def call(self, prompt: str, image_base64: str) -> str:
                return f"received:{image_base64}"
            @property
            def model_name(self) -> str:
                return "stub"

        vlm = StubVLM()
        result = vlm.call_multi("prompt", ["img_a", "img_b"])
        assert result == "received:img_a"

    def test_call_multi_empty_list_raises(self):
        class StubVLM(BaseVLM):
            def call(self, prompt: str, image_base64: str) -> str:
                return ""
            @property
            def model_name(self) -> str:
                return "stub"

        vlm = StubVLM()
        with pytest.raises(VLMError, match="at least one image"):
            vlm.call_multi("prompt", [])


class TestMockVLM:
    def test_model_name(self):
        vlm = MockVLM()
        assert vlm.model_name == "mock-vlm-v1"

    def test_forced_food_scene(self):
        vlm = MockVLM(forced_scene="FOOD")
        response = vlm.call("describe image", "base64data")
        data = json.loads(response)
        assert data["scene_type"] == "FOOD"
        assert len(data["food_name"]) > 0

    def test_forced_medication_scene(self):
        vlm = MockVLM(forced_scene="MEDICATION")
        response = vlm.call("describe image", "base64data")
        data = json.loads(response)
        assert data["scene_type"] == "MEDICATION"
        assert "drug_name" in data

    def test_forced_report_scene(self):
        vlm = MockVLM(forced_scene="REPORT")
        response = vlm.call("describe image", "base64data")
        data = json.loads(response)
        assert data["scene_type"] == "REPORT"
        assert len(data["indicators"]) > 0

    def test_forced_unknown_scene(self):
        vlm = MockVLM(forced_scene="UNKNOWN")
        response = vlm.call("describe image", "base64data")
        data = json.loads(response)
        assert data["scene_type"] == "UNKNOWN"
        assert "reason" in data

    def test_infer_food_from_prompt(self):
        vlm = MockVLM()
        response = vlm.call("Analyze the food and nutrition in this meal photo", "b64")
        data = json.loads(response)
        assert data["scene_type"] == "FOOD"

    def test_infer_medication_from_prompt(self):
        vlm = MockVLM()
        response = vlm.call("Read the medication label and extract drug information", "b64")
        data = json.loads(response)
        assert data["scene_type"] == "MEDICATION"

    def test_infer_report_from_prompt(self):
        vlm = MockVLM()
        response = vlm.call("Extract lab report results from this blood test", "b64")
        data = json.loads(response)
        assert data["scene_type"] == "REPORT"

    def test_infer_unknown_fallback(self):
        vlm = MockVLM()
        response = vlm.call("What is this random image?", "b64")
        data = json.loads(response)
        assert data["scene_type"] == "UNKNOWN"

    def test_returns_valid_json(self):
        for scene in ["FOOD", "MEDICATION", "REPORT", "UNKNOWN"]:
            vlm = MockVLM(forced_scene=scene)
            response = vlm.call("test", "b64")
            data = json.loads(response)  # must not raise
            assert "scene_type" in data
            assert "confidence" in data

    def test_call_multi_works(self):
        vlm = MockVLM(forced_scene="FOOD")
        response = vlm.call_multi("test", ["b64a", "b64b"])
        data = json.loads(response)
        assert data["scene_type"] == "FOOD"

    def test_call_multi_empty_raises(self):
        vlm = MockVLM()
        with pytest.raises(VLMError, match="at least one image"):
            vlm.call_multi("test", [])
