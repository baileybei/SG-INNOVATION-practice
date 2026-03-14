"""Abstract base class for VLM (Vision Language Model) interface.

Design goal: SEA-LION is just one implementation.
Swap models by swapping implementations, not graph logic.
"""

from abc import ABC, abstractmethod


class BaseVLM(ABC):
    """Abstract VLM interface. All VLM implementations must subclass this."""

    @abstractmethod
    def call(self, prompt: str, image_base64: str) -> str:
        """Send a prompt + image to the VLM and return the raw text response.

        Args:
            prompt: The text prompt / instruction.
            image_base64: Base64-encoded image string.

        Returns:
            Raw text response from the model.

        Raises:
            VLMError: If the API call fails.
        """

    def call_multi(self, prompt: str, images_base64: list[str]) -> str:
        """Send a prompt + multiple images to the VLM and return the raw text response.

        Default implementation: uses the first image and delegates to call().
        Subclasses that natively support multi-image input should override this.

        Args:
            prompt: The text prompt / instruction.
            images_base64: List of base64-encoded image strings (at least one).

        Returns:
            Raw text response from the model.

        Raises:
            VLMError: If the list is empty or the API call fails.
        """
        if not images_base64:
            raise VLMError("call_multi() requires at least one image.")
        return self.call(prompt, images_base64[0])

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""


class VLMError(Exception):
    """Raised when a VLM API call fails."""
