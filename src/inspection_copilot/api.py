"""REST API: inspections (upload, detect, review, report), chat with the agent, statistics."""

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot import agent, services
from inspection_copilot.db import get_session
from inspection_copilot.llm import MissingApiKeyError
from inspection_copilot.models import Image

router = APIRouter(prefix="/api")
SessionDep = Annotated[AsyncSession, Depends(get_session)]
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png"}


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20_000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


def _agent_payload(result: agent.AgentAnswer) -> dict:
    return {
        "answer": result.answer,
        "sources": [asdict(s) for s in result.sources],
        "trace": [asdict(t) for t in result.trace],
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(result.cost_usd, 4),
        "stopped_early": result.stopped_early,
    }


def _llm_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"LLM unavailable: {exc}")


@router.post("/inspections")
async def create_inspection(
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    insulator_type: Annotated[Literal["glass", "porcelain", "composite"], Form()] = "glass",
    mode: Annotated[Literal["auto", "fast", "accurate"], Form()] = "auto",
) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="upload a JPEG or PNG image")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="image larger than 15 MB")
    image_id = await services.inspect_image(
        session, data, file.filename or "upload.jpg", insulator_type, mode
    )
    return await services.image_detail(session, image_id)


@router.get("/inspections")
async def list_inspections(session: SessionDep) -> list[dict]:
    return await services.list_images(session)


@router.get("/inspections/{image_id}")
async def get_inspection(session: SessionDep, image_id: int) -> dict:
    try:
        return await services.image_detail(session, image_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/inspections/{image_id}/image")
async def get_inspection_image(session: SessionDep, image_id: int) -> FileResponse:
    image = await session.get(Image, image_id)
    if image is None or not image.storage_path:
        raise HTTPException(status_code=404, detail="image not found")
    if not await asyncio.to_thread(Path(image.storage_path).exists):
        raise HTTPException(status_code=404, detail="image file missing")
    return FileResponse(image.storage_path)


@router.post("/inspections/{image_id}/review")
async def review_inspection(session: SessionDep, image_id: int) -> dict:
    try:
        result = await services.review_image(session, image_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingApiKeyError as exc:
        raise _llm_unavailable(exc) from exc
    return {"review": result, "inspection": await services.image_detail(session, image_id)}


@router.post("/inspections/{image_id}/report")
async def report(session: SessionDep, image_id: int) -> dict:
    try:
        await services.image_detail(session, image_id)  # 404 before spending tokens
        result = await agent.write_report(session, image_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingApiKeyError as exc:
        raise _llm_unavailable(exc) from exc
    return _agent_payload(result)


@router.post("/chat")
async def chat(session: SessionDep, request: ChatRequest) -> dict:
    try:
        result = await agent.ask(
            session, request.question, [t.model_dump() for t in request.history]
        )
    except MissingApiKeyError as exc:
        raise _llm_unavailable(exc) from exc
    return _agent_payload(result)


@router.get("/stats")
async def stats(session: SessionDep) -> dict:
    return await services.fleet_statistics(session)
