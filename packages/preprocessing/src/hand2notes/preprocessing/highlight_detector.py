"""Highlight color detection using OpenCV HSV color space analysis.

Detects highlighted regions (yellow, green, blue, pink highlighters) and
returns bounding regions with associated color names.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# HSV ranges for common highlighter colors (H in [0,179], S/V in [0,255])
_HIGHLIGHT_RANGES = {
    "yellow": ((20, 100, 150), (40, 255, 255)),
    "green": ((40, 80, 120), (80, 255, 255)),
    "blue": ((90, 80, 120), (130, 255, 255)),
    "pink": ((140, 60, 150), (170, 255, 255)),
    "orange": ((5, 120, 150), (20, 255, 255)),
}


def detect_highlights(image_path: Path) -> list[dict]:
    """Detect highlighted regions in an image.

    Returns a list of dicts with keys: color, bbox (x,y,w,h), hex_color.
    Returns empty list if OpenCV is not available.
    """
    if not _CV2_AVAILABLE:
        return []

    try:
        return _detect_with_opencv(image_path)
    except Exception as exc:
        log.warning("Highlight detection failed: %s", exc)
        return []


def _detect_with_opencv(image_path: Path) -> list[dict]:
    import cv2
    import numpy as np

    img = cv2.imread(str(image_path))
    if img is None:
        return []

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    results = []

    for color_name, (lower, upper) in _HIGHLIGHT_RANGES.items():
        lower_arr = np.array(lower, dtype=np.uint8)
        upper_arr = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_arr, upper_arr)

        # Morphological close to fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:  # skip tiny specks
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            results.append({
                "color": color_name,
                "hex_color": _color_to_hex(color_name),
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            })

    return results


def _color_to_hex(color_name: str) -> str:
    _HEX_MAP = {
        "yellow": "#FFFF00",
        "green": "#00FF7F",
        "blue": "#00BFFF",
        "pink": "#FF69B4",
        "orange": "#FFA500",
    }
    return _HEX_MAP.get(color_name, "#FFFF00")
