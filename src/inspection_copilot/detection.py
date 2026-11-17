"""Insulator detection with the YOLOv8 models from the master's thesis.

Six models: {glass, porcelain, composite} x {fast = YOLOv8n, accurate = YOLOv8s}.

Modes:
  fast      YOLOv8n only (low latency)
  accurate  YOLOv8s only (higher accuracy)
  auto      the thesis idea in miniature (dynamic model switching): run the fast model first
            and escalate to the accurate model only when the fast result is uncertain, i.e.
            nothing was found with high confidence or some box sits in the uncertain band.
            Easy images stay cheap; hard images get the bigger model.
"""

import io
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

from inspection_copilot.config import get_settings

InsulatorType = Literal["glass", "porcelain", "composite"]
Mode = Literal["fast", "accurate", "auto"]

MODEL_FILES: dict[tuple[str, str], str] = {
    ("glass", "fast"): "glass_y8n_fast.pt",
    ("glass", "accurate"): "glass_y8s_accurate.pt",
    ("porcelain", "fast"): "porcelain_y8n_fast.pt",
    ("porcelain", "accurate"): "porcelain_y8s_accurate.pt",
    ("composite", "fast"): "comp_resplit_y8n_fast.pt",
    ("composite", "accurate"): "comp_resplit_y8s_accurate.pt",
}

CONF_THRESHOLD = 0.25  # boxes below this are discarded (Ultralytics default)
CONFIDENT = 0.5  # a box at or above this counts as a confident detection
UNCERTAIN_BAND = (0.25, 0.45)  # boxes in this range make the fast result "uncertain"


@dataclass(frozen=True)
class Box:
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class DetectionOutcome:
    model_name: str
    mode: str  # the mode that produced the final boxes: fast | accurate
    requested_mode: str
    boxes: list[Box]
    inference_ms: float
    width: int
    height: int
    escalated: bool = False
    fast_ms: float | None = None  # in auto mode: latency of the first (fast) pass
    notes: list[str] = field(default_factory=list)


def models_dir() -> Path:
    return Path(get_settings().models_dir)


@lru_cache(maxsize=6)
def _load(insulator_type: str, mode: str):
    from ultralytics import YOLO  # lazy: heavy import

    path = models_dir() / MODEL_FILES[(insulator_type, mode)]
    if not path.exists():
        raise FileNotFoundError(f"model weights not found: {path}")
    model = YOLO(str(path))
    # Warm-up: the first predict call initialises the network and is several seconds slower.
    # Doing it here keeps that one-off cost out of the recorded inference latencies.
    import numpy as np

    model.predict(np.zeros((640, 640, 3), dtype=np.uint8), device="cpu", verbose=False)
    return model


def _run(image, insulator_type: str, mode: str) -> tuple[list[Box], float, str]:
    model = _load(insulator_type, mode)
    started = time.perf_counter()
    result = model.predict(image, conf=CONF_THRESHOLD, device="cpu", verbose=False)[0]
    elapsed_ms = (time.perf_counter() - started) * 1000
    boxes = [
        Box(
            class_name=result.names[int(cls)],
            confidence=round(float(conf), 4),
            x1=round(float(x1), 1),
            y1=round(float(y1), 1),
            x2=round(float(x2), 1),
            y2=round(float(y2), 1),
        )
        for (x1, y1, x2, y2), conf, cls in zip(
            result.boxes.xyxy.tolist(),
            result.boxes.conf.tolist(),
            result.boxes.cls.tolist(),
            strict=True,
        )
    ]
    return boxes, elapsed_ms, MODEL_FILES[(insulator_type, mode)].removesuffix(".pt")


def is_uncertain(boxes: list[Box]) -> bool:
    """Escalation rule for auto mode."""
    if not any(b.confidence >= CONFIDENT for b in boxes):
        return True
    low, high = UNCERTAIN_BAND
    return any(low <= b.confidence < high for b in boxes)


def detect(
    image_bytes: bytes, insulator_type: InsulatorType, mode: Mode = "auto"
) -> DetectionOutcome:
    """Run detection on an image (CPU). Blocking: call via asyncio.to_thread from the API."""
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    if mode in ("fast", "accurate"):
        boxes, ms, name = _run(image, insulator_type, mode)
        return DetectionOutcome(name, mode, mode, boxes, ms, width, height)

    boxes, fast_ms, name = _run(image, insulator_type, "fast")
    if not is_uncertain(boxes):
        return DetectionOutcome(
            name, "fast", "auto", boxes, fast_ms, width, height, fast_ms=fast_ms
        )
    acc_boxes, acc_ms, acc_name = _run(image, insulator_type, "accurate")
    return DetectionOutcome(
        acc_name,
        "accurate",
        "auto",
        acc_boxes,
        fast_ms + acc_ms,
        width,
        height,
        escalated=True,
        fast_ms=fast_ms,
        notes=[f"fast pass uncertain ({len(boxes)} boxes), escalated to accurate model"],
    )
