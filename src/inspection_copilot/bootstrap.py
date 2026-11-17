"""First-start setup, so that `docker compose up --build` gives a working demo.

    python -m inspection_copilot.bootstrap

Runs at container start (docker/entrypoint.sh) and does work only when needed:
  * no documents in the database -> download the public-domain manuals (SHA-256 verified),
    chunk, embed and store them (a few minutes on CPU, once);
  * no inspections yet and YOLO weights present -> run detection on the openly licensed demo
    images in demo/images.
Failures are logged, never fatal: the API still starts (e.g. without internet access).
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import func, select

from inspection_copilot.config import get_settings
from inspection_copilot.db import get_engine, get_sessionmaker
from inspection_copilot.models import Document, Image

logger = logging.getLogger("bootstrap")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


async def _counts() -> tuple[int, int]:
    async with get_sessionmaker()() as session:
        documents = await session.scalar(select(func.count(Document.id)))
        images = await session.scalar(select(func.count(Image.id)))
    return documents or 0, images or 0


async def _load_documents() -> None:
    from inspection_copilot import ingest

    settings = get_settings()
    await asyncio.to_thread(ingest.fetch_documents)
    docs = await asyncio.to_thread(
        ingest.build_chunks, settings.chunk_max_words, settings.chunk_overlap_words
    )
    await ingest.write_to_db(docs)


def _demo_files() -> list[Path]:
    folder = Path(get_settings().demo_images_dir)
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES)


async def _seed_demo_images() -> None:
    from inspection_copilot import services
    from inspection_copilot.detection import MODEL_FILES, models_dir

    weights = models_dir() / MODEL_FILES[("glass", "fast")]
    if not await asyncio.to_thread(weights.exists):
        logger.info("YOLO weights not present: skipping demo detections")
        return
    files = await asyncio.to_thread(_demo_files)
    async with get_sessionmaker()() as session:
        for path in files:
            data = await asyncio.to_thread(path.read_bytes)
            image_id = await services.inspect_image(session, data, path.name, "glass", "auto")
            logger.info("seeded demo image %s as inspection %s", path.name, image_id)


async def main() -> None:
    documents, images = await _counts()
    if documents == 0:
        logger.info("no documents yet: loading the maintenance manuals (one-off, a few minutes)")
        try:
            await _load_documents()
        except Exception:
            logger.exception("loading documents failed; the API starts without them")
    if images == 0:
        try:
            await _seed_demo_images()
        except Exception:
            logger.exception("seeding demo images failed")
    await get_engine().dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
