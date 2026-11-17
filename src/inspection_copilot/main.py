"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot import __version__
from inspection_copilot.config import get_settings
from inspection_copilot.db import get_engine, get_session

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=get_settings().log_level)
    logger.info("starting inspection-copilot %s", __version__)
    yield
    # Close pooled connections cleanly on shutdown (important for container restarts).
    await get_engine().dispose()


app = FastAPI(title="Insulator Inspection Copilot", version=__version__, lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database, so a slow DB does not
    make the orchestrator restart a healthy container."""
    return {"status": "ok", "version": __version__}


# Annotated dependency: reusable type alias, and no function call in a default argument.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@app.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    """Readiness: the app can serve traffic, i.e. the database answers."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # report any DB failure as 503 instead of a stack trace
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}
