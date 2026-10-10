"""Privacy stage: pixelate plates and people BEFORE anything is stored or shown."""
import cv2
import numpy as np

from .detect import Box


def pixelate(img: np.ndarray, boxes: list[Box], pad: float = 0.15, block: int = 12) -> np.ndarray:
    out = img.copy()
    h, w = img.shape[:2]
    for b in boxes:
        x1, y1, x2, y2 = b.xyxy
        px, py = int(b.w * pad), int(b.h * pad)
        x1, y1 = max(0, x1 - px), max(0, y1 - py)
        x2, y2 = min(w, x2 + px), min(h, y2 + py)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = out[y1:y2, x1:x2]
        small = cv2.resize(roi, (max(1, (x2 - x1) // block), max(1, (y2 - y1) // block)), interpolation=cv2.INTER_LINEAR)
        out[y1:y2, x1:x2] = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
    return out
