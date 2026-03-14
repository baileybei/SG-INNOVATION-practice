"""Node: rejection_handler - handle unrecognized/unsupported images."""

from src.vision_agent.schemas.outputs import UnknownOutput
from src.vision_agent.state import VisionAgentState


def rejection_handler(state: VisionAgentState) -> dict:
    """Return a structured rejection response for unrecognized images."""
    output = UnknownOutput(
        scene_type="UNKNOWN",
        reason=(
            "The image does not contain identifiable food, medication, or medical report. "
            "Please upload a photo of a meal, medicine packaging, or lab/health report."
        ),
        confidence=state.get("confidence", 0.0),
    )
    return {
        "structured_output": output.model_dump(),
        "error": None,
    }
