"""Node: food_analyzer - extract food items and nutrition from image."""

import json
import logging

from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.prompts.food import FOOD_PROMPT
from src.vision_agent.schemas.outputs import FoodOutput
from src.vision_agent.state import VisionAgentState
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def make_food_analyzer(vlm: BaseVLM):
    """Factory: returns a food_analyzer node bound to the given VLM."""

    def food_analyzer(state: VisionAgentState) -> dict:
        if state.get("error"):
            return {}

        try:
            raw = vlm.call_multi(FOOD_PROMPT, state["images_base64"])
            data = json.loads(raw)
            validated = FoodOutput(**data)

            return {
                "raw_response": raw,
                "structured_output": validated.model_dump(),
                "error": None,
            }

        except json.JSONDecodeError as e:
            return {"error": f"Food analyzer returned invalid JSON: {e}"}
        except ValidationError as e:
            return {"error": f"Food output validation failed: {e}"}
        except VLMError as e:
            return {"error": f"VLM call failed in food_analyzer: {e}"}

    return food_analyzer
