"""Underline, box, and circle shape detection using OpenCV contour analysis.

Detects hand-drawn underlines, rectangles (boxes), and circles/ellipses around
text, and returns shape metadata for association with nearby blocks.
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


def detect_shapes(image_path: Path) -> list[dict]:
    """Detect underlines, boxes, and circles in an image.

    Returns list of dicts with keys: shape_type, bbox (x,y,width,height).
    shape_type is one of: 'underline', 'box', 'circle'.
    Returns empty list if OpenCV is not available.
    """
    if not _CV2_AVAILABLE:
        return []

    try:
        return _detect_with_opencv(image_path)
    except Exception as exc:
        log.warning("Shape detection failed: %s", exc)
        return []


def _detect_with_opencv(image_path: Path) -> list[dict]:
    import cv2
    import numpy as np

    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []

    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results = []
    img_h, img_w = img.shape[:2]

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 200:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / max(h, 1)

        # Underline: very wide and very flat
        if aspect > 8 and h < img_h * 0.02:
            results.append({"shape_type": "underline", "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}})
            continue

        # Try circle/ellipse fitting
        if len(cnt) >= 5:
            ellipse = cv2.fitEllipse(cnt)
            (_, _), (ma, mi), _ = ellipse
            if mi > 0 and (ma / mi) < 1.5 and area > 1000:
                results.append({"shape_type": "circle", "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}})
                continue

        # Box: roughly rectangular with reasonable area
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            rect_area = w * h
            if rect_area > 0 and (area / rect_area) > 0.6 and solidity > 0.8 and 0.3 < aspect < 10:
                results.append({"shape_type": "box", "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}})

    return results
