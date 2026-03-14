"""Node: scene_classifier - classify image into FOOD/MEDICATION/REPORT/UNKNOWN."""

import json
import logging

from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.prompts.classifier import CLASSIFIER_PROMPT
from src.vision_agent.state import VisionAgentState

logger = logging.getLogger(__name__)

VALID_SCENES = {"FOOD", "MEDICATION", "REPORT", "UNKNOWN"}


def make_scene_classifier(vlm: BaseVLM):
    """Factory: returns a scene_classifier node bound to the given VLM."""

    def scene_classifier(state: VisionAgentState) -> dict:
        if state.get("error"):
            return {}  # Propagate existing error, skip processing

        try:
            raw = vlm.call_multi(CLASSIFIER_PROMPT, state["images_base64"])
            data = json.loads(raw)

            scene_type = data.get("scene_type", "UNKNOWN").upper()
            if scene_type not in VALID_SCENES:
                logger.warning("VLM returned unknown scene_type '%s', defaulting to UNKNOWN", scene_type)
                scene_type = "UNKNOWN"

            return {
                "scene_type": scene_type,
                "confidence": float(data.get("confidence", 0.0)),
                "raw_response": raw,
                "error": None,
            }

        except json.JSONDecodeError as e:
            return {"error": f"Scene classifier returned invalid JSON: {e}", "scene_type": "UNKNOWN"}
        except VLMError as e:
            return {"error": f"VLM call failed in scene_classifier: {e}", "scene_type": "UNKNOWN"}

    return scene_classifier
