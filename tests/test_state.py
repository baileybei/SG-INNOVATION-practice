"""Tests for VisionAgentState."""

from src.vision_agent.state import VisionAgentState


class TestVisionAgentState:
    def test_state_is_typeddict(self):
        state: VisionAgentState = {
            "image_paths": ["/tmp/test.jpg"],
            "images_base64": [],
            "scene_type": "FOOD",
            "confidence": 0.9,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        assert state["scene_type"] == "FOOD"
        assert state["error"] is None

    def test_state_allows_partial_construction(self):
        # LangGraph nodes return partial state updates
        partial: dict = {"scene_type": "MEDICATION", "confidence": 0.85}
        assert partial["scene_type"] == "MEDICATION"

    def test_state_supports_multiple_image_paths(self):
        state: VisionAgentState = {
            "image_paths": ["/tmp/front.jpg", "/tmp/back.jpg"],
            "images_base64": ["b64a", "b64b"],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }
        assert len(state["image_paths"]) == 2
        assert len(state["images_base64"]) == 2
