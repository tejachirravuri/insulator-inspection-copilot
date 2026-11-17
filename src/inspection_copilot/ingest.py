"""Ingest the knowledge-base PDFs into PostgreSQL.

    python -m inspection_copilot.ingest            # PDF -> chunks -> embeddings -> database
    python -m inspection_copilot.ingest --dry-run  # only print chunk statistics

Re-running is safe (idempotent): each document is identified by its manifest key and is
replaced, so the database always matches the current chunking settings.
"""

import argparse
import asyncio
import statistics
import time
import tomllib
from pathlib import Path

from sqlalchemy import delete

from inspection_copilot.chunking import ChunkData, chunk_pages
from inspection_copilot.config import get_settings
from inspection_copilot.db import get_engine, get_sessionmaker
from inspection_copilot.models import Chunk, Document

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "sources.toml"
RAW_DIR = ROOT / "data" / "raw"


def read_pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader  # lazy: only needed for ingestion, not in the API

    return [page.extract_text() or "" for page in PdfReader(path).pages]


def load_manifest() -> list[dict]:
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))["document"]


def build_chunks(max_words: int, overlap_words: int) -> dict[str, tuple[dict, list[ChunkData]]]:
    result = {}
    for doc in load_manifest():
        pages = read_pdf_pages(RAW_DIR / f"{doc['key']}.pdf")
        # Blank (not remove) front matter so page numbers still match the PDF for citations.
        skip = doc.get("first_content_page", 1) - 1
        pages = [""] * skip + pages[skip:]
        result[doc["key"]] = (doc, chunk_pages(pages, max_words, overlap_words))
    return result


async def write_to_db(docs: dict[str, tuple[dict, list[ChunkData]]]) -> None:
    from inspection_copilot.embeddings import get_embedder

    embedder = get_embedder()
    async with get_sessionmaker()() as session:
        for key, (meta, chunks) in docs.items():
            started = time.perf_counter()
            vectors = await asyncio.to_thread(embedder.embed_passages, [c.text for c in chunks])
            await session.execute(delete(Document).where(Document.source_key == key))
            document = Document(
                source_key=key, title=meta["title"], source_url=meta["url"], license=meta["license"]
            )
            document.chunks = [
                Chunk(
                    ordinal=c.ordinal,
                    section=c.section,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    text=c.text,
                    embedding=v,
                )
                for c, v in zip(chunks, vectors, strict=True)
            ]
            session.add(document)
            await session.commit()  # one transaction per document
            print(f"{key}: {len(chunks)} chunks in {time.perf_counter() - started:.1f}s")
    await get_engine().dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    settings = get_settings()
    parser.add_argument("--max-words", type=int, default=settings.chunk_max_words)
    parser.add_argument("--overlap-words", type=int, default=settings.chunk_overlap_words)
    parser.add_argument("--dry-run", action="store_true", help="print statistics only")
    args = parser.parse_args()

    docs = build_chunks(args.max_words, args.overlap_words)
    for key, (_, chunks) in docs.items():
        sizes = [len(c.text.split()) for c in chunks]
        with_section = sum(c.section is not None for c in chunks)
        print(
            f"{key}: {len(chunks)} chunks, words median {statistics.median(sizes):.0f} "
            f"max {max(sizes)}, {with_section}/{len(chunks)} with a section heading"
        )
    if not args.dry_run:
        asyncio.run(write_to_db(docs))


if __name__ == "__main__":
    main()
