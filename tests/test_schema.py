"""Checks that the migrated schema supports both retrieval methods and the inspection data."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from inspection_copilot.models import (
    EMBEDDING_DIM,
    Chunk,
    Detection,
    DetectionRun,
    Document,
    Image,
)

pytestmark = pytest.mark.db


def _unit_vector(index: int) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0
    return vec


async def test_vector_search_returns_nearest_chunk(db_session) -> None:
    doc = Document(source_key=f"test-{uuid4()}", title="Test manual", license="test")
    doc.chunks = [
        Chunk(
            ordinal=0,
            page_start=1,
            page_end=1,
            text="glass insulator shattered shell",
            embedding=_unit_vector(0),
        ),
        Chunk(
            ordinal=1,
            page_start=1,
            page_end=2,
            text="porcelain flashover marks",
            embedding=_unit_vector(1),
        ),
    ]
    db_session.add(doc)
    await db_session.flush()

    query = _unit_vector(1)
    stmt = select(Chunk.ordinal).order_by(Chunk.embedding.cosine_distance(query)).limit(1)
    assert (await db_session.execute(stmt)).scalar_one() == 1


async def test_keyword_search_uses_generated_tsvector(db_session) -> None:
    doc = Document(source_key=f"test-{uuid4()}", title="Test manual", license="test")
    doc.chunks = [
        Chunk(
            ordinal=0,
            page_start=1,
            page_end=1,
            text="Inspect for flashover damage",
            embedding=_unit_vector(0),
        ),
        Chunk(
            ordinal=1,
            page_start=1,
            page_end=2,
            text="Clean the conductor clamps",
            embedding=_unit_vector(1),
        ),
    ]
    db_session.add(doc)
    await db_session.flush()

    # 'flashover' is matched through the English stemmer, without any Python-side indexing.
    tsquery = func.plainto_tsquery("english", "flashover")
    stmt = select(Chunk.ordinal).where(Chunk.document_id == doc.id, Chunk.tsv.op("@@")(tsquery))
    assert (await db_session.execute(stmt)).scalars().all() == [0]


async def test_detection_rows_link_to_run_and_image(db_session) -> None:
    image = Image(filename="a.jpg", sha256="0" * 64, insulator_type="glass", width=640, height=480)
    run = DetectionRun(model_name="glass_y8n_fast", mode="fast", inference_ms=12.5)
    run.detections = [
        Detection(class_name="defect", confidence=0.9, x1=1, y1=2, x2=30, y2=40),
    ]
    image.runs = [run]
    db_session.add(image)
    await db_session.flush()

    stmt = (
        select(Image.insulator_type, DetectionRun.mode, Detection.class_name)
        .join(DetectionRun, DetectionRun.image_id == Image.id)
        .join(Detection, Detection.run_id == DetectionRun.id)
        .where(Image.id == image.id)
    )
    assert (await db_session.execute(stmt)).one() == ("glass", "fast", "defect")
