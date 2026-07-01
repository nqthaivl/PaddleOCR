from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from app.models.settings import PreprocessSettings

Roi = Tuple[int, int, int, int]


def clamp_roi(roi: Roi, width: int, height: int) -> Roi:
    x, y, w, h = roi
    x = max(0, min(int(x), width - 1))
    y = max(0, min(int(y), height - 1))
    w = max(1, min(int(w), width - x))
    h = max(1, min(int(h), height - y))
    return x, y, w, h


def crop_roi(frame: np.ndarray, roi: Roi) -> np.ndarray:
    height, width = frame.shape[:2]
    x, y, w, h = clamp_roi(roi, width, height)
    return frame[y : y + h, x : x + w].copy()


def preprocess_for_ocr(frame: np.ndarray, roi: Roi, settings: PreprocessSettings) -> np.ndarray:
    image = crop_roi(frame, roi)
    if settings.upscale:
        image = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    if settings.denoise:
        image = cv2.fastNlMeansDenoisingColored(image, None, 7, 7, 7, 21)
    if settings.grayscale:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if settings.contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        if settings.sharpen:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            gray = cv2.filter2D(gray, -1, kernel)
        if settings.threshold:
            gray = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                5,
            )
        image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return image
