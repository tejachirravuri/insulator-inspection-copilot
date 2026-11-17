"""Hybrid retrieval over document chunks: vector search + keyword search, fused with RRF.

Why both?
  * Vector (semantic) search finds paraphrases: "porcelain discs breaking" matches text about
    "cracked insulator units", even with no shared words.
  * Keyword (full-text) search finds exact technical terms, standard numbers and acronyms
    ("FIST 4-1B", "glaze burn", "Doble test") that small embedding models often blur.
  * Reciprocal Rank Fusion (RRF) merges the two ranked lists using only ranks, not scores.
    Cosine distances and ts_rank values live on different scales, so adding raw scores would
    need tuning; RRF does not. score(chunk) = sum over lists of 1 / (k + rank), k = 60.

Keyword ranking comes in two variants:
  * keyword: PostgreSQL ts_rank_cd. It has no inverse document frequency (IDF), so common
    words ("test" is in 370 of 931 chunks) outrank rare, decisive ones ("stick": 29).
  * bm25: Okapi BM25 computed in SQL from the same tsvector column: IDF, term-frequency
    saturation (k1) and length normalisation (b), standard parameters k1 = 1.2, b = 0.75,
    not tuned. Statistics are computed per query, which is fast at this corpus size (~1k
    chunks); for large corpora they would be precomputed in materialized views.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Text, cast, func, select, text
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot.models import Chunk, Document

Method = Literal["vector", "keyword", "bm25", "hybrid", "hybrid_bm25"]
# Default for the agent and the MCP server. Chosen by a rule fixed before measuring: switch
# to hybrid_bm25 only if it beats hybrid on both the development and the held-out question
# set (MRR@10: 0.62 vs 0.51 and 0.61 vs 0.57; eval/results/).
DEFAULT_METHOD: Method = "hybrid_bm25"
BM25_K1 = 1.2  # standard values (Robertson & Zaragoza), deliberately not tuned on our questions
BM25_B = 0.75
RRF_K = 60  # constant from the original RRF paper (Cormack et al., 2009)
CANDIDATES = 30  # how many results each method contributes before fusion


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    score: float
    source_key: str
    document_title: str
    section: str | None
    page_start: int
    page_end: int
    text: str


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[int]], k: int = RRF_K
) -> list[tuple[int, float]]:
    """Fuse ranked lists of ids. Returns (id, score) sorted best first.

    Ties are broken by id so results are deterministic.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


async def vector_ids(session: AsyncSession, query_embedding: list[float], limit: int) -> list[int]:
    """Nearest chunks by cosine distance (uses the HNSW index)."""
    stmt = select(Chunk.id).order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(limit)
    return list((await session.execute(stmt)).scalars())


def _or_tsquery(query: str):
    # plainto_tsquery parses and stems the question safely (no injection, no syntax errors)
    # but ANDs all terms, so a long question would rarely match anything. Replacing '&' with
    # '|' turns it into an OR query; ts_rank_cd then rewards chunks matching more terms.
    or_text = func.replace(cast(func.plainto_tsquery("english", query), Text), "&", "|")
    return cast(or_text, TSQUERY)


async def keyword_ids(session: AsyncSession, query: str, limit: int) -> list[int]:
    """Chunks ranked by PostgreSQL full-text relevance (uses the GIN index)."""
    tsquery = _or_tsquery(query)
    rank = func.ts_rank_cd(Chunk.tsv, tsquery)
    stmt = (
        select(Chunk.id)
        .where(Chunk.tsv.op("@@")(tsquery))
        .order_by(rank.desc(), Chunk.id)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


_BM25_SQL = text(
    """
    WITH query_terms AS (
        SELECT DISTINCT lexeme FROM unnest(to_tsvector('english', :query))
    ),
    doc_len AS (
        SELECT c.id,
               (SELECT coalesce(sum(array_length(t.positions, 1)), 0) FROM unnest(c.tsv) t)
                   AS dl
        FROM chunks c
    ),
    corpus AS (
        SELECT count(*)::float8 AS n, avg(dl)::float8 AS avgdl FROM doc_len
    ),
    term_freq AS (
        SELECT c.id AS chunk_id, t.lexeme, array_length(t.positions, 1)::float8 AS tf
        FROM chunks c, unnest(c.tsv) t
        WHERE t.lexeme IN (SELECT lexeme FROM query_terms)
    ),
    term_df AS (
        SELECT lexeme, count(*)::float8 AS df FROM term_freq GROUP BY lexeme
    )
    SELECT tf.chunk_id
    FROM term_freq tf
    JOIN term_df df ON df.lexeme = tf.lexeme
    JOIN doc_len dl ON dl.id = tf.chunk_id
    CROSS JOIN corpus
    GROUP BY tf.chunk_id
    ORDER BY sum(
        ln(1 + (corpus.n - df.df + 0.5) / (df.df + 0.5))
        * tf.tf * (:k1 + 1)
        / (tf.tf + :k1 * (1 - :b + :b * dl.dl / greatest(corpus.avgdl, 1)))
    ) DESC, tf.chunk_id
    LIMIT :limit
    """
)


async def bm25_ids(session: AsyncSession, query: str, limit: int) -> list[int]:
    """Chunks ranked by Okapi BM25 over the PostgreSQL tsvector column."""
    rows = await session.execute(
        _BM25_SQL, {"query": query, "limit": limit, "k1": BM25_K1, "b": BM25_B}
    )
    return [row[0] for row in rows]


async def _load_hits(session: AsyncSession, scored: list[tuple[int, float]]) -> list[SearchHit]:
    if not scored:
        return []
    ids = [chunk_id for chunk_id, _ in scored]
    stmt = (
        select(Chunk, Document.source_key, Document.title)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_(ids))
    )
    rows = {chunk.id: (chunk, key, title) for chunk, key, title in await session.execute(stmt)}
    hits = []
    for chunk_id, score in scored:
        chunk, key, title = rows[chunk_id]
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                score=score,
                source_key=key,
                document_title=title,
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
            )
        )
    return hits


async def search(
    session: AsyncSession,
    query: str,
    query_embedding: list[float] | None,
    method: Method = "hybrid",
    top_k: int = 5,
) -> list[SearchHit]:
    """Run one retrieval method and return the top_k chunks with their metadata."""
    if method == "keyword":
        ids = await keyword_ids(session, query, top_k)
        scored = [(i, 1.0 / (RRF_K + r)) for r, i in enumerate(ids, start=1)]
    elif method == "vector":
        if query_embedding is None:
            raise ValueError("vector search needs a query embedding")
        ids = await vector_ids(session, query_embedding, top_k)
        scored = [(i, 1.0 / (RRF_K + r)) for r, i in enumerate(ids, start=1)]
    elif method == "bm25":
        ids = await bm25_ids(session, query, top_k)
        scored = [(i, 1.0 / (RRF_K + r)) for r, i in enumerate(ids, start=1)]
    elif method == "hybrid_bm25":
        if query_embedding is None:
            raise ValueError("hybrid search needs a query embedding")
        rankings = [
            await vector_ids(session, query_embedding, CANDIDATES),
            await bm25_ids(session, query, CANDIDATES),
        ]
        scored = reciprocal_rank_fusion(rankings)[:top_k]
    elif method == "hybrid":
        if query_embedding is None:
            raise ValueError("hybrid search needs a query embedding")
        # Sequential on purpose: one AsyncSession cannot run two queries concurrently.
        rankings = [
            await vector_ids(session, query_embedding, CANDIDATES),
            await keyword_ids(session, query, CANDIDATES),
        ]
        scored = reciprocal_rank_fusion(rankings)[:top_k]
    else:
        raise ValueError(f"unknown method {method!r}")
    return await _load_hits(session, scored)
