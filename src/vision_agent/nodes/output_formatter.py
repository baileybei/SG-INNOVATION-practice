"""Node: output_formatter - final validation and formatting of structured output."""

import logging

from src.vision_agent.state import VisionAgentState

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"scene_type", "confidence"}

# Optional fields per scene type — used for completeness-based confidence adjustment.
# More null fields → lower adjusted confidence.
_OPTIONAL_FIELDS_BY_SCENE: dict[str, list[str]] = {
    "FOOD": ["meal_type", "notes"],
    "MEDICATION": ["frequency", "route", "warnings", "expiry_date", "ingredients"],
    "REPORT": ["report_date", "lab_name"],
}

# Max penalty applied when all optional fields are null (e.g. 0.25 = up to 25% reduction)
_MAX_NULL_PENALTY = 0.25


def _adjust_confidence(output: dict) -> dict:
    """Reduce confidence based on how many optional fields are null.

    Rationale: Gemini tends to return 0.98+ regardless of extraction quality.
    A result with many null fields is less complete, so we apply a proportional
    penalty to give downstream a more meaningful confidence signal.
    """
    scene = output.get("scene_type", "UNKNOWN")
    optional_fields = _OPTIONAL_FIELDS_BY_SCENE.get(scene)
    if not optional_fields:
        return output

    null_count = sum(1 for f in optional_fields if output.get(f) is None)
    null_ratio = null_count / len(optional_fields)
    penalty = null_ratio * _MAX_NULL_PENALTY

    original = output.get("confidence", 1.0)
    adjusted = round(max(0.0, original - penalty), 4)

    if adjusted != original:
        logger.debug(
            "Confidence adjusted %s→%s (%d/%d optional fields null)",
            original, adjusted, null_count, len(optional_fields),
        )

    return {**output, "confidence": adjusted}


def output_formatter(state: VisionAgentState) -> dict:
    """Validate structured_output has required fields, adjust confidence, add metadata."""
    if state.get("error"):
        return {
            "structured_output": {
                "scene_type": "ERROR",
                "error": state["error"],
                "confidence": 0.0,
            }
        }

    output = state.get("structured_output", {})
    missing = REQUIRED_FIELDS - set(output.keys())
    if missing:
        logger.error("structured_output missing required fields: %s", missing)
        return {
            "structured_output": {
                "scene_type": "ERROR",
                "error": f"Output missing required fields: {missing}",
                "confidence": 0.0,
            }
        }

    return {"structured_output": _adjust_confidence(output)}
