"""Retry wrapper for VLM calls with exponential backoff.

Wraps any BaseVLM implementation to add automatic retry on transient errors.
Does NOT retry on:
  - JSON parse errors (those indicate a model logic issue, not transient)
  - VLMError raised by the implementation itself (already counted as failure)
"""

import logging
import time
from typing import Optional

from src.vision_agent.llm.base import BaseVLM, VLMError

logger = logging.getLogger(__name__)


class RetryVLM(BaseVLM):
    """Decorator-style wrapper that retries VLM calls on failure."""

    def __init__(
        self,
        vlm: BaseVLM,
        max_retries: int = 3,
        delay_s: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> None:
        """
        Args:
            vlm: The underlying VLM implementation to wrap.
            max_retries: Maximum number of attempts (1 = no retry).
            delay_s: Initial delay between retries in seconds.
            backoff_factor: Multiplier for delay after each failure.
        """
        self._vlm = vlm
        self._max_retries = max_retries
        self._delay_s = delay_s
        self._backoff_factor = backoff_factor

    @property
    def model_name(self) -> str:
        return self._vlm.model_name

    def call(self, prompt: str, image_base64: str) -> str:
        last_error: Optional[Exception] = None
        delay = self._delay_s

        for attempt in range(1, self._max_retries + 1):
            try:
                return self._vlm.call(prompt, image_base64)
            except VLMError as e:
                last_error = e
                if attempt < self._max_retries:
                    logger.warning(
                        "VLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt,
                        self._max_retries,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= self._backoff_factor
                else:
                    logger.error(
                        "VLM call failed after %d attempts: %s",
                        self._max_retries,
                        e,
                    )

        raise VLMError(
            f"VLM call failed after {self._max_retries} attempts: {last_error}"
        )

    def call_multi(self, prompt: str, images_base64: list[str]) -> str:
        last_error: Optional[Exception] = None
        delay = self._delay_s

        for attempt in range(1, self._max_retries + 1):
            try:
                return self._vlm.call_multi(prompt, images_base64)
            except VLMError as e:
                last_error = e
                if attempt < self._max_retries:
                    logger.warning(
                        "VLM call_multi failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt,
                        self._max_retries,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= self._backoff_factor
                else:
                    logger.error(
                        "VLM call_multi failed after %d attempts: %s",
                        self._max_retries,
                        e,
                    )

        raise VLMError(
            f"VLM call failed after {self._max_retries} attempts: {last_error}"
        )
