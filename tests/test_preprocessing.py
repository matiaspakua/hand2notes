"""Unit tests for image preprocessing (deskew) and the VLM resize step."""

import numpy as np
import pytest
from PIL import Image

cv2 = pytest.importorskip("cv2")

from hand2notes.preprocessing.deskew import deskew, deskew_file  # noqa: E402


def _blank_page(w=400, h=600) -> np.ndarray:
    return np.full((h, w, 3), 255, dtype=np.uint8)


def test_deskew_straight_page_not_corrected():
    img = _blank_page()
    # Draw a few horizontal black lines (text baselines) — perfectly straight.
    for y in range(100, 500, 60):
        img[y : y + 3, 50:350] = 0
    result = deskew(img)
    assert result.was_corrected is False
    assert abs(result.angle_deg) < 0.5
    assert result.image.shape == img.shape


def test_deskew_file_roundtrip(tmp_path):
    src = tmp_path / "in.jpg"
    Image.fromarray(_blank_page()).save(src, "JPEG")
    out = tmp_path / "out.jpg"
    result = deskew_file(src, out)
    assert out.exists()
    assert result.image is not None


def test_deskew_file_missing_raises(tmp_path):
    with pytest.raises(ValueError):
        deskew_file(tmp_path / "nope.jpg", tmp_path / "out.jpg")


def test_resize_caps_width(tmp_path):
    from hand2notes.pipeline.orchestrator import _MAX_PREPROCESS_WIDTH, _resize_for_processing

    src = tmp_path / "wide.jpg"
    Image.new("RGB", (3200, 2400), "white").save(src, "JPEG")
    dst = tmp_path / "small.jpg"
    _resize_for_processing(src, dst)
    with Image.open(dst) as out:
        assert out.size[0] == _MAX_PREPROCESS_WIDTH
        assert out.size[1] == int(2400 * _MAX_PREPROCESS_WIDTH / 3200)


def test_resize_leaves_small_image(tmp_path):
    from hand2notes.pipeline.orchestrator import _resize_for_processing

    src = tmp_path / "ok.jpg"
    Image.new("RGB", (1000, 700), "white").save(src, "JPEG")
    dst = tmp_path / "out.jpg"
    _resize_for_processing(src, dst)
    with Image.open(dst) as out:
        assert out.size == (1000, 700)
