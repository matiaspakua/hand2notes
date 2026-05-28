"""Denoising, shadow removal, and contrast normalization for notebook page images.

Uses OpenCV adaptiveThreshold and scikit-image background subtraction to produce
a clean, high-contrast image suitable for OCR.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class DenoiseResult:
    image: np.ndarray
    normalized: bool


def remove_shadow(gray: np.ndarray) -> np.ndarray:
    """Subtract uneven illumination (shadows) using morphological background estimation."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    background = cv2.dilate(gray, kernel)
    background = cv2.GaussianBlur(background, (21, 21), 0)
    # Shadow-free image: difference from background + shift to mid-gray
    shadow_free = cv2.addWeighted(gray, 1.0, background, -1.0, 128)
    return shadow_free


def normalize_contrast(gray: np.ndarray) -> np.ndarray:
    """Adaptive histogram equalization for uneven lighting."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def binarize(gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold binarization for handwritten text."""
    return cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )


def denoise(image: np.ndarray, binarize_output: bool = False) -> DenoiseResult:
    """Full denoising pipeline: shadow removal → contrast normalize → optional binarize.

    Args:
        image: BGR input image.
        binarize_output: If True, return a binary (black/white) image. Otherwise return
                         the shadow-free, contrast-normalized grayscale.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    shadow_free = remove_shadow(gray)
    normalized = normalize_contrast(shadow_free)

    output_gray = binarize(normalized) if binarize_output else normalized

    output_bgr = cv2.cvtColor(output_gray, cv2.COLOR_GRAY2BGR)
    return DenoiseResult(image=output_bgr, normalized=True)


def denoise_file(
    input_path: Path, output_path: Path, binarize_output: bool = False
) -> DenoiseResult:
    """Load, denoise, and save an image file."""
    image = cv2.imread(str(input_path))
    if image is None:
        raise ValueError(f"Could not read image: {input_path}")

    result = denoise(image, binarize_output=binarize_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), result.image)
    return result
