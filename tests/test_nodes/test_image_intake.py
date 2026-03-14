"""Tests for image_intake node."""

import base64
import os
import tempfile

import pytest
from PIL import Image

from src.vision_agent.nodes.image_intake import MAX_IMAGES, image_intake


def _make_test_image(suffix: str = ".jpg") -> str:
    """Create a temporary test image file, return its path."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        img.save(f.name)
        return f.name


def _state(image_paths: list[str] | None = None) -> dict:
    return {
        "image_paths": image_paths or [],
        "images_base64": [],
        "scene_type": "",
        "confidence": 0.0,
        "raw_response": "",
        "structured_output": {},
        "error": None,
    }


class TestImageIntake:
    def test_valid_jpeg_returns_base64(self):
        path = _make_test_image(".jpg")
        try:
            result = image_intake(_state([path]))
            assert result["error"] is None
            assert len(result["images_base64"]) == 1
            decoded = base64.b64decode(result["images_base64"][0])
            assert len(decoded) > 0
        finally:
            os.unlink(path)

    def test_valid_png_returns_base64(self):
        path = _make_test_image(".png")
        try:
            result = image_intake(_state([path]))
            assert result["error"] is None
            assert len(result["images_base64"]) == 1
        finally:
            os.unlink(path)

    def test_missing_path_returns_error(self):
        result = image_intake(_state([]))
        assert result["error"] is not None
        assert "No image path" in result["error"]

    def test_nonexistent_file_returns_error(self):
        result = image_intake(_state(["/tmp/definitely_does_not_exist_12345.jpg"]))
        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_unsupported_extension_returns_error(self):
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            f.write(b"GIF89a")
            path = f.name
        try:
            result = image_intake(_state([path]))
            assert result["error"] is not None
            assert "Unsupported" in result["error"]
        finally:
            os.unlink(path)

    def test_file_too_large_returns_error(self):
        """Simulate a file that exceeds the 10MB limit via mock."""
        from unittest.mock import patch
        path = _make_test_image(".jpg")
        try:
            with patch(
                "src.vision_agent.nodes.image_intake.os.path.getsize",
                return_value=11 * 1024 * 1024,  # 11MB
            ):
                result = image_intake(_state([path]))
                assert result["error"] is not None
                assert "too large" in result["error"]
        finally:
            os.unlink(path)

    def test_webp_extension_supported(self):
        """WebP images should be accepted."""
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
            img.save(f.name, format="WEBP")
            path = f.name
        try:
            result = image_intake(_state([path]))
            assert result["error"] is None
            assert len(result["images_base64"]) == 1
        finally:
            os.unlink(path)

    def test_jpeg_extension_supported(self):
        """Both .jpg and .jpeg extensions should be accepted."""
        path = _make_test_image(".jpeg")
        try:
            result = image_intake(_state([path]))
            assert result["error"] is None
        finally:
            os.unlink(path)


class TestImageIntakeMulti:
    def test_multiple_valid_images(self):
        paths = [_make_test_image(".jpg") for _ in range(3)]
        try:
            result = image_intake(_state(paths))
            assert result["error"] is None
            assert len(result["images_base64"]) == 3
        finally:
            for p in paths:
                os.unlink(p)

    def test_max_images_exceeded(self):
        paths = [_make_test_image(".jpg") for _ in range(MAX_IMAGES + 1)]
        try:
            result = image_intake(_state(paths))
            assert result["error"] is not None
            assert "Too many images" in result["error"]
        finally:
            for p in paths:
                os.unlink(p)

    def test_one_bad_image_skipped_partial_success(self):
        """One invalid image is skipped; valid images still processed."""
        good = _make_test_image(".jpg")
        try:
            result = image_intake(_state([good, "/nonexistent.jpg"]))
            assert result["error"] is None
            assert len(result["images_base64"]) == 1
            assert "skipped_images" in result
            assert len(result["skipped_images"]) == 1
            assert result["skipped_images"][0]["index"] == 1
            assert "not found" in result["skipped_images"][0]["reason"]
        finally:
            os.unlink(good)

    def test_all_bad_images_returns_error(self):
        """All images failing validation should return an error."""
        result = image_intake(_state(["/nonexistent1.jpg", "/nonexistent2.jpg"]))
        assert result["error"] is not None
        assert "All images failed" in result["error"]

    def test_no_skipped_images_key_when_all_valid(self):
        """skipped_images key should not appear when all images are valid."""
        path = _make_test_image(".jpg")
        try:
            result = image_intake(_state([path]))
            assert "skipped_images" not in result
        finally:
            os.unlink(path)

    def test_skipped_images_records_index_and_reason(self):
        """skipped_images entries must include index, path, and reason."""
        good1 = _make_test_image(".jpg")
        good2 = _make_test_image(".jpg")
        try:
            result = image_intake(_state([good1, "/bad.gif", good2]))
            assert result["error"] is None
            assert len(result["images_base64"]) == 2
            skipped = result["skipped_images"]
            assert len(skipped) == 1
            assert skipped[0]["index"] == 1
            assert skipped[0]["path"] == "/bad.gif"
            assert "reason" in skipped[0]
        finally:
            os.unlink(good1)
            os.unlink(good2)
