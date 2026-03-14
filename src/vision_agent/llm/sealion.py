"""SEA-LION text model implementation.

Uses AI Singapore's SEA-LION API (OpenAI-compatible /v1/chat/completions).
Currently only text models are available. For vision tasks, use GeminiVLM
as a temporary solution until SEA-LION VL models become available via API.

Text model: aisingapore/Gemma-SEA-LION-v4-27B-IT
"""

import os

import httpx

from src.vision_agent.llm.base import BaseVLM, VLMError

_API_BASE = "https://api.sea-lion.ai/v1/chat/completions"
_DEFAULT_MODEL = "aisingapore/Gemma-SEA-LION-v4-27B-IT"


class SeaLionVLM(BaseVLM):
    """SEA-LION API client (text-only, OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str = "",
        model: str = _DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("SEALION_API_KEY", "")
        if not self._api_key:
            raise VLMError("SEALION_API_KEY must be set in environment or passed directly.")
        self._model = model
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def call(self, prompt: str, image_base64: str) -> str:
        """Call SEA-LION text API.

        Note: image_base64 is accepted for interface compatibility but
        currently ignored since only text models are available.
        For vision tasks, pair with GeminiVLM or FoodAI for image understanding.
        """
        try:
            response = httpx.post(
                _API_BASE,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "max_completion_tokens": 2048,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise VLMError(
                f"SEA-LION API error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise VLMError(f"SEA-LION network error: {e}") from e
