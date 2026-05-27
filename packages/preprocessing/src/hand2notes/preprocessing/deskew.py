"""Deskew and perspective correction via OpenCV Hough line detection.

Returns a corrected numpy array (BGR) alongside the angle that was applied.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class DeskewResult:
    image: np.ndarray
    angle_deg: float
    was_corrected: bool


def _detect_skew_angle(gray: np.ndarray) -> float:
    """Estimate page skew angle using Hough line transform."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    if lines is None:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Keep only near-horizontal lines (skew is typically < 15°)
        if abs(angle) < 15:
            angles.append(angle)

    if not angles:
        return 0.0
    return float(np.median(angles))


def deskew(image: np.ndarray, angle_threshold_deg: float = 0.5) -> DeskewResult:
    """Correct skew in a BGR image. Skips correction if angle < threshold."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    angle = _detect_skew_angle(gray)

    if abs(angle) < angle_threshold_deg:
        return DeskewResult(image=image, angle_deg=angle, was_corrected=False)

    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, scale=1.0)
    corrected = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return DeskewResult(image=corrected, angle_deg=angle, was_corrected=True)


def deskew_file(input_path: Path, output_path: Path) -> DeskewResult:
    """Load, deskew, and save an image file. Returns the deskew result."""
    image = cv2.imread(str(input_path))
    if image is None:
        raise ValueError(f"Could not read image: {input_path}")

    result = deskew(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), result.image)
    return result
