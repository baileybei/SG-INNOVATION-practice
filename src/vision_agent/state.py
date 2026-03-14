"""VisionAgentState - the shared state flowing through the LangGraph."""

from typing import Optional
from typing_extensions import TypedDict


class VisionAgentState(TypedDict):
    image_paths: list[str]         # Input image file paths (one or more)
    images_base64: list[str]       # Base64-encoded images for VLM API
    scene_type: str                # FOOD / MEDICATION / REPORT / UNKNOWN
    confidence: float              # Scene classification confidence (0.0 - 1.0)
    raw_response: str              # Raw text response from vision VLM
    structured_output: dict        # Parsed, validated structured data
    skipped_images: list[dict]     # Images skipped during intake (partial failure)
    error: Optional[str]           # Error message if any node fails
