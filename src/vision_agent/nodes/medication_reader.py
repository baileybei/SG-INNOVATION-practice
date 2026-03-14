"""Node: medication_reader - extract medication information from image."""

import json
import logging

from pydantic import ValidationError

from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.prompts.medication import MEDICATION_PROMPT
from src.vision_agent.schemas.outputs import MedicationOutput
from src.vision_agent.state import VisionAgentState

logger = logging.getLogger(__name__)


def make_medication_reader(vlm: BaseVLM):
    """Factory: returns a medication_reader node bound to the given VLM."""

    def medication_reader(state: VisionAgentState) -> dict:
        if state.get("error"):
            return {}

        try:
            raw = vlm.call_multi(MEDICATION_PROMPT, state["images_base64"])
            data = json.loads(raw)
            validated = MedicationOutput(**data)

            return {
                "raw_response": raw,
                "structured_output": validated.model_dump(),
                "error": None,
            }

        except json.JSONDecodeError as e:
            return {"error": f"Medication reader returned invalid JSON: {e}"}
        except ValidationError as e:
            return {"error": f"Medication output validation failed: {e}"}
        except VLMError as e:
            return {"error": f"VLM call failed in medication_reader: {e}"}

    return medication_reader
