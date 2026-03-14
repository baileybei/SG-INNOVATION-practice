"""Google Gemini VLM implementation.

Uses Gemini 2.5 Flash as a temporary VLM for development while waiting
for SEA-LION VL API access. Supports image + text multimodal input.

API docs: https://ai.google.dev/gemini-api/docs
"""

import os

import httpx

from src.vision_agent.llm.base import BaseVLM, VLMError

_DEFAULT_MODEL = "gemini-2.5-flash"
_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiVLM(BaseVLM):
    """Gemini API client for vision tasks."""

    def __init__(
        self,
        api_key: str = "",
        model: str = _DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self._api_key:
            raise VLMError("GEMINI_API_KEY must be set in environment or passed directly.")
        self._model = model
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def call(self, prompt: str, image_base64: str) -> str:
        """Send prompt + image to Gemini and return text response."""
        url = f"{_API_BASE}/models/{self._model}:generateContent?key={self._api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {"text": prompt},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
            },
        }

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return self._extract_text(data)
        except httpx.HTTPStatusError as e:
            raise VLMError(
                f"Gemini API error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise VLMError(f"Gemini network error: {e}") from e

    def call_multi(self, prompt: str, images_base64: list[str]) -> str:
        """Send prompt + multiple images to Gemini (native multi-image support)."""
        if not images_base64:
            raise VLMError("call_multi() requires at least one image.")
        if len(images_base64) == 1:
            return self.call(prompt, images_base64[0])

        url = f"{_API_BASE}/models/{self._model}:generateContent?key={self._api_key}"

        parts: list[dict] = []
        for img_b64 in images_base64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_b64,
                },
            })
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
            },
        }

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return self._extract_text(data)
        except httpx.HTTPStatusError as e:
            raise VLMError(
                f"Gemini API error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise VLMError(f"Gemini network error: {e}") from e

    def _extract_text(self, data: dict) -> str:
        """Extract text content from Gemini API response."""
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            # Concatenate all text parts
            text_parts = [p["text"] for p in parts if "text" in p]
            if not text_parts:
                raise VLMError("Gemini returned no text in response.")
            text = "\n".join(text_parts)
            return _strip_markdown_fences(text)
        except (KeyError, IndexError) as e:
            raise VLMError(f"Unexpected Gemini response structure: {e}") from e


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from Gemini output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = stripped.index("\n")
        stripped = stripped[first_newline + 1:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()
