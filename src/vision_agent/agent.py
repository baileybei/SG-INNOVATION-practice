"""VisionAgent - high-level public API for the Vision Agent module.

This is the main entry point for other modules or services that want
to use the Vision Agent without worrying about LangGraph internals.

Usage:
    from src.vision_agent.agent import VisionAgent

    agent = VisionAgent()                          # uses MockVLM by default
    result = agent.analyze("/path/to/meal.jpg")
    print(result.scene_type)                       # "FOOD"
    print(result.structured_output)               # validated Pydantic model

    # Multi-image support:
    result = agent.analyze(["/path/front.jpg", "/path/back.jpg"])
    print(result.is_multi_image)                  # True
    print(result.image_path)                      # first path (backward compat)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from src.vision_agent.graph import build_graph
from src.vision_agent.llm.base import BaseVLM
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.schemas.outputs import (
    FoodOutput,
    MedicationOutput,
    ReportOutput,
    SceneType,
    UnknownOutput,
)

logger = logging.getLogger(__name__)

# Union type for all possible structured outputs
AnalysisOutput = Union[FoodOutput, MedicationOutput, ReportOutput, UnknownOutput]

_SCHEMA_MAP = {
    SceneType.FOOD: FoodOutput,
    SceneType.MEDICATION: MedicationOutput,
    SceneType.REPORT: ReportOutput,
    SceneType.UNKNOWN: UnknownOutput,
}


@dataclass
class AnalysisResult:
    """Result returned from VisionAgent.analyze().

    Attributes:
        scene_type: Detected scene (FOOD/MEDICATION/REPORT/UNKNOWN).
        confidence: Model confidence (0.0-1.0).
        structured_output: Validated Pydantic model, or None on error.
        raw_response: Raw VLM text response (useful for debugging).
        error: Error message if analysis failed, None on success.
        image_paths: The input image path(s) that were analyzed.
    """

    scene_type: str
    confidence: float
    structured_output: Optional[AnalysisOutput]
    raw_response: str
    error: Optional[str]
    image_paths: list[str]

    @property
    def image_path(self) -> str:
        """Return the first image path (backward compatibility)."""
        return self.image_paths[0] if self.image_paths else ""

    @property
    def is_multi_image(self) -> bool:
        return len(self.image_paths) > 1

    @property
    def is_food(self) -> bool:
        return self.scene_type == SceneType.FOOD

    @property
    def is_medication(self) -> bool:
        return self.scene_type == SceneType.MEDICATION

    @property
    def is_report(self) -> bool:
        return self.scene_type == SceneType.REPORT

    @property
    def is_unknown(self) -> bool:
        return self.scene_type == SceneType.UNKNOWN

    @property
    def is_error(self) -> bool:
        return self.error is not None or self.scene_type == "ERROR"

    @property
    def as_food(self) -> Optional[FoodOutput]:
        """Return typed FoodOutput if scene is FOOD, else None."""
        return self.structured_output if isinstance(self.structured_output, FoodOutput) else None

    @property
    def as_medication(self) -> Optional[MedicationOutput]:
        """Return typed MedicationOutput if scene is MEDICATION, else None."""
        return self.structured_output if isinstance(self.structured_output, MedicationOutput) else None

    @property
    def as_report(self) -> Optional[ReportOutput]:
        """Return typed ReportOutput if scene is REPORT, else None."""
        return self.structured_output if isinstance(self.structured_output, ReportOutput) else None


class VisionAgent:
    """High-level API for analyzing medical images.

    Wraps the LangGraph Vision Agent and returns typed AnalysisResult objects.
    Supports dual-model architecture: vision VLM (Gemini) + text LLM (SeaLION).
    """

    def __init__(
        self,
        vlm: Optional[BaseVLM] = None,
        max_retries: int = 3,
        retry_delay_s: float = 1.0,
    ) -> None:
        """
        Args:
            vlm: Vision VLM for image understanding (e.g. Gemini). Defaults to MockVLM.
            max_retries: Retry attempts for VLM failures.
            retry_delay_s: Initial delay between retries.
        """
        if vlm is None:
            vlm = MockVLM()
            logger.info("VisionAgent initialized with MockVLM (development mode)")
        else:
            logger.info("VisionAgent initialized with vision=%s", vlm.model_name)

        self._vlm = vlm
        self._graph = build_graph(
            vlm=vlm,
            max_retries=max_retries,
            retry_delay_s=retry_delay_s,
        )

    def analyze(self, image_path: Union[str, list[str]]) -> AnalysisResult:
        """Analyze image(s) and return a structured AnalysisResult.

        Args:
            image_path: Path or list of paths to image file(s).

        Returns:
            AnalysisResult with scene_type, structured_output, and metadata.
        """
        if isinstance(image_path, str):
            paths = [image_path]
        else:
            paths = list(image_path)

        resolved_paths = [str(Path(p).resolve()) for p in paths]
        logger.debug("Analyzing image(s): %s", resolved_paths)

        initial_state = {
            "image_paths": resolved_paths,
            "images_base64": [],
            "scene_type": "",
            "confidence": 0.0,
            "raw_response": "",
            "structured_output": {},
            "error": None,
        }

        state = self._graph.invoke(initial_state)
        return self._parse_result(state, paths)

    def _parse_result(self, state: dict, image_paths: list[str]) -> AnalysisResult:
        """Convert raw graph state into a typed AnalysisResult."""
        raw_output = state.get("structured_output", {})
        scene_type = state.get("scene_type") or raw_output.get("scene_type", "UNKNOWN")
        error = state.get("error")

        # If output_formatter wrapped an error
        if raw_output.get("scene_type") == "ERROR":
            return AnalysisResult(
                scene_type="ERROR",
                confidence=0.0,
                structured_output=None,
                raw_response=state.get("raw_response", ""),
                error=raw_output.get("error", "Unknown error"),
                image_paths=image_paths,
            )

        # Try to instantiate the typed Pydantic model
        typed_output: Optional[AnalysisOutput] = None
        try:
            scene_enum = SceneType(scene_type)
            schema_cls = _SCHEMA_MAP.get(scene_enum)
            if schema_cls and raw_output:
                typed_output = schema_cls(**raw_output)
        except Exception as e:
            logger.warning("Could not deserialize structured_output to Pydantic model: %s", e)

        return AnalysisResult(
            scene_type=scene_type,
            confidence=state.get("confidence", raw_output.get("confidence", 0.0)),
            structured_output=typed_output,
            raw_response=state.get("raw_response", ""),
            error=error,
            image_paths=image_paths,
        )

    @property
    def model_name(self) -> str:
        return self._vlm.model_name
