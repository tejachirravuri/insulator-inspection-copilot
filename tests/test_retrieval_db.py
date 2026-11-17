"""Retrieval against a real PostgreSQL + pgvector, with hand-made embeddings (no ML model)."""

from uuid import uuid4

import pytest

from inspection_copilot.models import EMBEDDING_DIM, Chunk, Document
from inspection_copilot.retrieval import search

pytestmark = pytest.mark.db


def _vec(index: int) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[index] = 1.0
    return v


@pytest.fixture
async def corpus(db_session):
    doc = Document(source_key=f"test-{uuid4()}", title="Manual", license="test")
    texts = [
        "Glaze burned insulators should be replaced when convenient.",  # 0
        "Clean contaminated insulators by washing with water.",  # 1
        "Wood poles are inspected for decay at ground line.",  # 2
    ]
    doc.chunks = [
        Chunk(ordinal=i, page_start=i + 1, page_end=i + 1, text=t, embedding=_vec(i))
        for i, t in enumerate(texts)
    ]
    db_session.add(doc)
    await db_session.flush()
    return {c.ordinal: c.id for c in doc.chunks}


async def test_keyword_search_matches_any_term(db_session, corpus) -> None:
    # A natural question: most words are absent from the corpus. OR semantics still finds
    # the chunk about washing, ranked first.
    hits = await search(db_session, "How do I wash dirty insulators?", None, "keyword", 3)
    assert hits[0].chunk_id == corpus[1]


async def test_vector_search_orders_by_cosine_distance(db_session, corpus) -> None:
    hits = await search(db_session, "irrelevant", _vec(2), "vector", 1)
    assert [h.chunk_id for h in hits] == [corpus[2]]
    assert hits[0].page_start == 3


async def test_hybrid_combines_both_lists(db_session, corpus) -> None:
    # Vector prefers chunk 0, keywords prefer chunk 1 ("washing"): both must be returned.
    hits = await search(db_session, "washing", _vec(0), "hybrid", 2)
    assert {h.chunk_id for h in hits} == {corpus[0], corpus[1]}
