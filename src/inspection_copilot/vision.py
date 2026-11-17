"""Second opinion on YOLO detections from a vision LLM (Claude).

Two-stage design (a common industry pattern):
  1. YOLO localises insulators: fast, cheap, runs on CPU, but only knows "insulator here".
  2. Claude looks at the cropped insulators and judges their condition (glaze burn, broken
     shed, contamination, ...), which the detector was never trained to do.

All crops of one image go into ONE request, which is cheaper and faster than one call per
box. The answer is constrained by a JSON schema (structured outputs), so it always parses.
Disagreements (the LLM thinks a box is not an insulator) and uncertain or severe findings are
flagged `needs_human_review`: the model assists the inspector, it does not replace them.
"""

import base64
import io
import json
from dataclasses import dataclass

from inspection_copilot.config import get_settings
from inspection_copilot.detection import Box
from inspection_copilot.llm import get_async_client

CONDITIONS = [
    "good",
    "contaminated",
    "glaze_burn_or_flashover_marks",
    "broken_or_chipped",
    "missing_or_damaged_disc",
    "corroded_hardware",
    "not_an_insulator",
    "unclear",
]
SEVERITIES = ["none", "low", "medium", "high"]

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "crop": {"type": "integer"},
                    "is_insulator": {"type": "boolean"},
                    "condition": {"type": "string", "enum": CONDITIONS},
                    "severity": {"type": "string", "enum": SEVERITIES},
                    "needs_human_review": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "crop",
                    "is_insulator",
                    "condition",
                    "severity",
                    "needs_human_review",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["reviews"],
    "additionalProperties": False,
}

PROMPT = """You are assisting a powerline inspector. Each image above is a crop around one \
object that a YOLO detector labelled as "{label}". Crops are numbered in order, starting at 1.

For every crop decide:
- is_insulator: does the crop actually show an insulator?
- condition: the most important visible condition (use "unclear" if resolution or angle does \
not allow a judgement; do not guess).
- severity: none (good), low (cosmetic), medium (plan maintenance), high (replace soon).
- needs_human_review: true if you disagree with the detector, are unsure, or severity is \
medium or high.
- rationale: one short sentence about what you actually see.

Aerial crops are often small and blurry. Prefer "unclear" over a confident wrong answer."""

MAX_CROPS = 8  # cost cap per image
CROP_MARGIN = 0.15  # context around the box, as a fraction of box size
CROP_MAX_SIDE = 512  # pixels; bigger crops cost more tokens without helping much


@dataclass(frozen=True)
class Review:
    crop: int
    is_insulator: bool
    condition: str
    severity: str
    needs_human_review: bool
    rationale: str


@dataclass(frozen=True)
class ReviewResult:
    boxes: list[Box]  # the reviewed boxes, in crop order (crop 1 = boxes[0])
    reviews: list[Review]
    model: str
    input_tokens: int
    output_tokens: int


def crop_jpeg(image, box: Box) -> bytes:
    """Crop a box with some margin, shrink to CROP_MAX_SIDE, encode as JPEG."""
    w, h = box.x2 - box.x1, box.y2 - box.y1
    left = max(0, box.x1 - w * CROP_MARGIN)
    top = max(0, box.y1 - h * CROP_MARGIN)
    right = min(image.width, box.x2 + w * CROP_MARGIN)
    bottom = min(image.height, box.y2 + h * CROP_MARGIN)
    crop = image.crop((int(left), int(top), int(right), int(bottom)))
    crop.thumbnail((CROP_MAX_SIDE, CROP_MAX_SIDE))
    buffer = io.BytesIO()
    crop.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


async def review_boxes(image_bytes: bytes, boxes: list[Box]) -> ReviewResult:
    """Ask Claude for a condition assessment of up to MAX_CROPS detected boxes."""
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    selected = sorted(boxes, key=lambda b: -b.confidence)[:MAX_CROPS]
    content: list[dict] = []
    for box in selected:
        data = base64.standard_b64encode(crop_jpeg(image, box)).decode("ascii")
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
            }
        )
    label = selected[0].class_name if selected else "insulator"
    content.append({"type": "text", "text": PROMPT.format(label=label)})

    settings = get_settings()
    response = await get_async_client().messages.create(
        model=settings.llm_model,
        max_tokens=4000,
        output_config={
            "effort": "low",  # visual judgement, not multi-step reasoning
            "format": {"type": "json_schema", "schema": REVIEW_SCHEMA},
        },
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined to review these crops")
    text = next(b.text for b in response.content if b.type == "text")
    reviews = [Review(**r) for r in json.loads(text)["reviews"]]
    return ReviewResult(
        boxes=selected,
        reviews=reviews,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
