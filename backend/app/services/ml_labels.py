"""Direction class encoding for XGBoost (requires 0..K-1, not -1/0/1)."""
from __future__ import annotations

import numpy as np

# Semantic labels: bearish, neutral, bullish
DIRECTION_BEARISH = -1
DIRECTION_NEUTRAL = 0
DIRECTION_BULLISH = 1

TARGET_TO_XGB: dict[int, int] = {
    DIRECTION_BEARISH: 0,
    DIRECTION_NEUTRAL: 1,
    DIRECTION_BULLISH: 2,
}
XGB_TO_TARGET: dict[int, int] = {v: k for k, v in TARGET_TO_XGB.items()}


def encode_direction_targets(y) -> np.ndarray:
    """Map -1/0/1 targets to 0/1/2 for sklearn XGBoost."""
    out = np.empty(len(y), dtype=np.int32)
    for i, t in enumerate(y):
        out[i] = TARGET_TO_XGB[int(t)]
    return out


def direction_from_xgb_class(class_id: int) -> int:
    """Map model class id back to -1/0/1 (supports legacy models with -1/0/1 classes)."""
    c = int(class_id)
    if c in XGB_TO_TARGET:
        return XGB_TO_TARGET[c]
  # Older artifacts may expose -1, 0, 1 directly
    if c in (DIRECTION_BEARISH, DIRECTION_NEUTRAL, DIRECTION_BULLISH):
        return c
    return DIRECTION_NEUTRAL
