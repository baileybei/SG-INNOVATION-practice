"""Shared pytest fixtures for Vision Agent tests."""

import os
import tempfile
from typing import Generator

import pytest
from PIL import Image

from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.graph import build_graph


@pytest.fixture
def mock_image_path() -> Generator[str, None, None]:
    """Create a temporary JPEG test image, yield its path, then clean up."""
    img = Image.new("RGB", (150, 150), color=(128, 64, 32))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f.name)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_png_path() -> Generator[str, None, None]:
    """Create a temporary PNG test image, yield its path, then clean up."""
    img = Image.new("RGBA", (200, 200), color=(0, 128, 255, 255))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def base_state(mock_image_path: str) -> dict:
    """Return a minimal valid initial state for graph invocation."""
    return {
        "image_paths": [mock_image_path],
        "images_base64": [],
        "scene_type": "",
        "confidence": 0.0,
        "raw_response": "",
        "structured_output": {},
        "error": None,
    }


@pytest.fixture
def food_graph():
    """Pre-built graph with MockVLM forced to FOOD scene."""
    return build_graph(vlm=MockVLM(forced_scene="FOOD"))


@pytest.fixture
def medication_graph():
    """Pre-built graph with MockVLM forced to MEDICATION scene."""
    return build_graph(vlm=MockVLM(forced_scene="MEDICATION"))


@pytest.fixture
def report_graph():
    """Pre-built graph with MockVLM forced to REPORT scene."""
    return build_graph(vlm=MockVLM(forced_scene="REPORT"))


@pytest.fixture
def unknown_graph():
    """Pre-built graph with MockVLM forced to UNKNOWN scene."""
    return build_graph(vlm=MockVLM(forced_scene="UNKNOWN"))
