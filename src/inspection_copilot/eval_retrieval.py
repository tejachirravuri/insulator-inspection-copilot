"""Retrieval evaluation: how often does each search method put a correct chunk near the top?

    python -m inspection_copilot.eval_retrieval --check   # validate the question set (no DB)
    python -m inspection_copilot.eval_retrieval           # run against the ingested database

Ground truth: every question has a short verbatim `evidence` quote from its source document.
A retrieved chunk is relevant if it comes from the right document and contains the quote.
Comparison ignores case and all whitespace, because PDF extraction sometimes splits words
("f or cracks"). Labelling by quote instead of chunk id keeps the question set valid when
chunk size changes.

Metrics (computed over the top 10 results of each method):
  hit@k   share of questions with at least one relevant chunk in the top k
  MRR@10  mean of 1 / rank of the first relevant chunk (0 if none in the top 10)
"""

import argparse
import asyncio
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "eval" / "retrieval_questions.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
METHODS = ("keyword", "bm25", "vector", "hybrid", "hybrid_bm25")
TOP_K = 10


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    source_key: str
    page: int
    question: str
    evidence: str
    answer: str


def load_questions(path: Path = QUESTIONS) -> list[Question]:
    with path.open(encoding="utf-8") as f:
        return [Question(**json.loads(line)) for line in f if line.strip()]


def normalise(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def is_relevant(question: Question, source_key: str, chunk_text: str) -> bool:
    return source_key == question.source_key and normalise(question.evidence) in normalise(
        chunk_text
    )


def first_relevant_rank(question: Question, hits: list[tuple[str, str]]) -> int | None:
    """hits: (source_key, text) in ranked order. Returns a 1-based rank or None."""
    for rank, (key, text) in enumerate(hits, start=1):
        if is_relevant(question, key, text):
            return rank
    return None


def summarise(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks)
    return {
        "n": n,
        "hit@1": sum(r is not None and r <= 1 for r in ranks) / n,
        "hit@3": sum(r is not None and r <= 3 for r in ranks) / n,
        "hit@5": sum(r is not None and r <= 5 for r in ranks) / n,
        "mrr@10": sum(1 / r for r in ranks if r is not None) / n,
    }


def check_questions(path: Path = QUESTIONS) -> int:
    """Every evidence quote must occur in a chunk of the right document on the stated page."""
    from inspection_copilot.config import get_settings
    from inspection_copilot.ingest import build_chunks

    settings = get_settings()
    docs = build_chunks(settings.chunk_max_words, settings.chunk_overlap_words)
    problems = 0
    for q in load_questions(path):
        chunks = docs[q.source_key][1]
        matches = [c for c in chunks if normalise(q.evidence) in normalise(c.text)]
        if not matches:
            print(f"{q.id}: evidence not found in {q.source_key}")
            problems += 1
        elif not any(c.page_start <= q.page <= c.page_end for c in matches):
            pages = sorted({(c.page_start, c.page_end) for c in matches})
            print(f"{q.id}: evidence found on pages {pages}, question says {q.page}")
            problems += 1
    print(f"{problems} problem(s) in {len(load_questions(path))} questions")
    return problems


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        )
        return out.stdout.strip() or "uncommitted"
    except OSError:
        return "unknown"


async def run(path: Path = QUESTIONS) -> dict:
    from sqlalchemy import func, select

    from inspection_copilot.config import get_settings
    from inspection_copilot.db import get_engine, get_sessionmaker
    from inspection_copilot.embeddings import get_embedder
    from inspection_copilot.models import Chunk
    from inspection_copilot.retrieval import search

    settings = get_settings()
    questions = load_questions(path)
    embedder = get_embedder()
    ranks: dict[str, dict[str, int | None]] = defaultdict(dict)
    async with get_sessionmaker()() as session:
        n_chunks = await session.scalar(select(func.count(Chunk.id)))
        for q in questions:
            vector = await asyncio.to_thread(embedder.embed_query, q.question)
            for method in METHODS:
                hits = await search(session, q.question, vector, method, TOP_K)
                ranks[method][q.id] = first_relevant_rank(q, [(h.source_key, h.text) for h in hits])
    await get_engine().dispose()

    categories = sorted({q.category for q in questions})
    summary = {}
    for method in METHODS:
        summary[method] = {"all": summarise([ranks[method][q.id] for q in questions])}
        for cat in categories:
            subset = [ranks[method][q.id] for q in questions if q.category == cat]
            summary[method][cat] = summarise(subset)
    return {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "config": {
            "embedding_model": settings.embedding_model,
            "chunk_max_words": settings.chunk_max_words,
            "chunk_overlap_words": settings.chunk_overlap_words,
            "n_chunks": n_chunks,
            "top_k": TOP_K,
            "rrf_k": 60,
        },
        "summary": summary,
        "per_question": {m: ranks[m] for m in METHODS},
    }


def markdown_table(result: dict) -> str:
    lines = [
        "| Method | Questions | Hit@1 | Hit@3 | Hit@5 | MRR@10 |",
        "|---|---|---|---|---|---|",
    ]
    for method, groups in result["summary"].items():
        for group, m in groups.items():
            label = method if group == "all" else f"{method} ({group})"
            lines.append(
                f"| {label} | {m['n']} | {m['hit@1']:.2f} | {m['hit@3']:.2f} "
                f"| {m['hit@5']:.2f} | {m['mrr@10']:.2f} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate questions only")
    parser.add_argument("--questions", type=Path, default=QUESTIONS, help="question set (jsonl)")
    parser.add_argument("--out", default="retrieval.json", help="file name in eval/results/")
    args = parser.parse_args()
    if args.check:
        raise SystemExit(1 if check_questions(args.questions) else 0)
    result = asyncio.run(run(args.questions))
    result["question_set"] = args.questions.name
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / args.out
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(markdown_table(result))
    print(f"\nwritten to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
