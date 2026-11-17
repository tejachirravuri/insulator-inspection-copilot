"""Inspection use cases shared by the HTTP API and the agent's tools.

Keeping this layer separate means the agent calls exactly the same, tested code paths as the
REST endpoints: a tool is a thin wrapper, not a second implementation.
"""

import asyncio
import hashlib
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from inspection_copilot.config import get_settings
from inspection_copilot.detection import Box, InsulatorType, Mode, detect
from inspection_copilot.models import Detection, DetectionReview, DetectionRun, Image

PRICE_PER_MTOK = {  # USD (input, output); used to show cost per request in the UI
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICE_PER_MTOK.get(model, (0.0, 0.0))
    return input_tokens * price_in / 1e6 + output_tokens * price_out / 1e6


def uploads_dir() -> Path:
    path = Path(get_settings().uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


class NotFoundError(LookupError):
    pass


async def inspect_image(
    session: AsyncSession,
    image_bytes: bytes,
    filename: str,
    insulator_type: InsulatorType,
    mode: Mode = "auto",
) -> int:
    """Store an image (deduplicated by SHA-256), run detection, store the run. Returns image id."""
    sha = hashlib.sha256(image_bytes).hexdigest()
    image = await session.scalar(select(Image).where(Image.sha256 == sha))
    outcome = await asyncio.to_thread(detect, image_bytes, insulator_type, mode)
    if image is None:
        suffix = Path(filename).suffix.lower() or ".jpg"
        path = uploads_dir() / f"{sha}{suffix}"
        await asyncio.to_thread(path.write_bytes, image_bytes)
        image = Image(
            filename=Path(filename).name[:500],
            sha256=sha,
            insulator_type=insulator_type,
            width=outcome.width,
            height=outcome.height,
            storage_path=str(path),
        )
        session.add(image)
        await session.flush()
    run = DetectionRun(
        image_id=image.id,
        model_name=outcome.model_name,
        mode=outcome.mode,
        requested_mode=outcome.requested_mode,
        escalated=outcome.escalated,
        fast_ms=outcome.fast_ms,
        inference_ms=round(outcome.inference_ms, 1),
    )
    run.detections = [
        Detection(
            class_name=b.class_name, confidence=b.confidence, x1=b.x1, y1=b.y1, x2=b.x2, y2=b.y2
        )
        for b in outcome.boxes
    ]
    session.add(run)
    await session.commit()
    return image.id


async def _latest_run(session: AsyncSession, image_id: int) -> DetectionRun | None:
    stmt = (
        select(DetectionRun)
        .where(DetectionRun.image_id == image_id)
        .order_by(DetectionRun.id.desc())
        .limit(1)
        .options(selectinload(DetectionRun.detections).selectinload(Detection.reviews))
    )
    return await session.scalar(stmt)


async def image_detail(session: AsyncSession, image_id: int) -> dict:
    """Image metadata, latest detection run, its detections and their latest review."""
    image = await session.get(Image, image_id)
    if image is None:
        raise NotFoundError(f"image {image_id} not found")
    run = await _latest_run(session, image_id)
    detections = []
    for d in sorted(run.detections if run else [], key=lambda d: -d.confidence):
        review = max(d.reviews, key=lambda r: r.id) if d.reviews else None
        detections.append(
            {
                "id": d.id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "box": [d.x1, d.y1, d.x2, d.y2],
                "review": None
                if review is None
                else {
                    "is_insulator": review.agrees_with_detector,
                    "condition": review.condition,
                    "severity": review.severity,
                    "needs_human_review": review.needs_human_review,
                    "rationale": review.rationale,
                },
            }
        )
    return {
        "id": image.id,
        "filename": image.filename,
        "insulator_type": image.insulator_type,
        "width": image.width,
        "height": image.height,
        "run": None
        if run is None
        else {
            "model": run.model_name,
            "mode": run.mode,
            "requested_mode": run.requested_mode,
            "escalated": run.escalated,
            "inference_ms": run.inference_ms,
            "fast_ms": run.fast_ms,
        },
        "detections": detections,
    }


async def review_image(session: AsyncSession, image_id: int) -> dict:
    """Run the vision second opinion on the latest run's detections and store it."""
    from inspection_copilot.vision import review_boxes

    image = await session.get(Image, image_id)
    if image is None:
        raise NotFoundError(f"image {image_id} not found")
    run = await _latest_run(session, image_id)
    if run is None or not run.detections:
        return {"reviewed": 0, "cost_usd": 0.0, "note": "no detections to review"}
    by_box = {(d.x1, d.y1, d.x2, d.y2): d for d in run.detections}
    boxes = [Box(d.class_name, d.confidence, d.x1, d.y1, d.x2, d.y2) for d in run.detections]
    data = await asyncio.to_thread(Path(image.storage_path).read_bytes)  # no blocking I/O
    result = await review_boxes(data, boxes)
    per_review_in = result.input_tokens // max(1, len(result.reviews))
    per_review_out = result.output_tokens // max(1, len(result.reviews))
    for review in result.reviews:
        if not 1 <= review.crop <= len(result.boxes):
            continue  # defensive: ignore a crop number the model invented
        box = result.boxes[review.crop - 1]
        detection = by_box[(box.x1, box.y1, box.x2, box.y2)]
        session.add(
            DetectionReview(
                detection_id=detection.id,
                model=result.model,
                agrees_with_detector=review.is_insulator,
                condition=review.condition,
                severity=review.severity,
                needs_human_review=review.needs_human_review,
                rationale=review.rationale[:2000],
                input_tokens=per_review_in,
                output_tokens=per_review_out,
            )
        )
    await session.commit()
    return {
        "reviewed": len(result.reviews),
        "model": result.model,
        "cost_usd": round(cost_usd(result.model, result.input_tokens, result.output_tokens), 4),
    }


async def list_images(session: AsyncSession, limit: int = 50) -> list[dict]:
    """Recent inspections with detection and review counts."""
    latest_run = (
        select(DetectionRun.image_id, func.max(DetectionRun.id).label("run_id"))
        .group_by(DetectionRun.image_id)
        .subquery()
    )
    flagged = (
        select(Detection.run_id, func.count(DetectionReview.id).label("n"))
        .join(DetectionReview, DetectionReview.detection_id == Detection.id)
        .where(DetectionReview.needs_human_review)
        .group_by(Detection.run_id)
        .subquery()
    )
    counts = (
        select(Detection.run_id, func.count(Detection.id).label("n"))
        .group_by(Detection.run_id)
        .subquery()
    )
    stmt = (
        select(
            Image.id,
            Image.filename,
            Image.insulator_type,
            DetectionRun.mode,
            DetectionRun.escalated,
            DetectionRun.inference_ms,
            func.coalesce(counts.c.n, 0),
            func.coalesce(flagged.c.n, 0),
        )
        .join(latest_run, latest_run.c.image_id == Image.id)
        .join(DetectionRun, DetectionRun.id == latest_run.c.run_id)
        .outerjoin(counts, counts.c.run_id == DetectionRun.id)
        .outerjoin(flagged, flagged.c.run_id == DetectionRun.id)
        .order_by(Image.id.desc())
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [
        {
            "id": r[0],
            "filename": r[1],
            "insulator_type": r[2],
            "mode": r[3],
            "escalated": r[4],
            "inference_ms": r[5],
            "detections": r[6],
            "flagged_for_human_review": r[7],
        }
        for r in rows
    ]


async def fleet_statistics(session: AsyncSession) -> dict:
    """Aggregate numbers across all inspections (computed in SQL, never by the LLM)."""
    images = await session.scalar(select(func.count(Image.id)))
    detections = await session.scalar(select(func.count(Detection.id)))
    runs = await session.execute(
        select(
            DetectionRun.requested_mode,
            DetectionRun.mode,
            func.count(DetectionRun.id),
            func.avg(DetectionRun.inference_ms),
            func.sum(case((DetectionRun.escalated, 1), else_=0)),
        ).group_by(DetectionRun.requested_mode, DetectionRun.mode)
    )
    conditions = await session.execute(
        select(DetectionReview.condition, DetectionReview.severity, func.count())
        .group_by(DetectionReview.condition, DetectionReview.severity)
        .order_by(func.count().desc())
    )
    flagged = await session.scalar(
        select(func.count(DetectionReview.id)).where(DetectionReview.needs_human_review)
    )
    return {
        "images": images,
        "detections": detections,
        "runs_by_model": [
            {
                "requested_mode": rm,
                "model_used": m,
                "runs": n,
                "avg_inference_ms": round(float(avg or 0), 1),
                "escalated": int(e or 0),
            }
            for rm, m, n, avg, e in runs
        ],
        "review_conditions": [
            {"condition": c, "severity": s, "count": n} for c, s, n in conditions
        ],
        "flagged_for_human_review": flagged,
    }
