"""Node: report_digitizer - extract indicators from medical reports."""

import json
import logging

from pydantic import ValidationError

from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.prompts.report import REPORT_PROMPT
from src.vision_agent.schemas.outputs import ReportOutput
from src.vision_agent.state import VisionAgentState

logger = logging.getLogger(__name__)


def make_report_digitizer(vlm: BaseVLM):
    """Factory: returns a report_digitizer node bound to the given VLM."""

    def report_digitizer(state: VisionAgentState) -> dict:
        if state.get("error"):
            return {}

        try:
            raw = vlm.call_multi(REPORT_PROMPT, state["images_base64"])
            data = json.loads(raw)
            validated = ReportOutput(**data)

            return {
                "raw_response": raw,
                "structured_output": validated.model_dump(),
                "error": None,
            }

        except json.JSONDecodeError as e:
            return {"error": f"Report digitizer returned invalid JSON: {e}"}
        except ValidationError as e:
            return {"error": f"Report output validation failed: {e}"}
        except VLMError as e:
            return {"error": f"VLM call failed in report_digitizer: {e}"}

    return report_digitizer
