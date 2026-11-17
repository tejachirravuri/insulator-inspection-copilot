"""REST API: inspections (upload, detect, review, report), chat with the agent, statistics.

Protection for a public deployment:
  * optional access code (setting ACCESS_CODE): every /api call must send it, as the
    X-Access-Code header or, for <img> tags that cannot send headers, a `code` query parameter;
  * daily LLM budget (DAILY_LLM_BUDGET_USD): AI endpoints return 429 once it is used up.
"""

import secrets
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot import agent, services
from inspection_copilot.config import get_settings
from inspection_copilot.db import get_session
from inspection_copilot.llm import MissingApiKeyError


async def require_access(
    x_access_code: Annotated[str | None, Header()] = None,
    code: Annotated[str | None, Query()] = None,
) -> None:
    expected = get_settings().access_code
    if expected is None or not expected.get_secret_value():
        return  # open (local development)
    given = x_access_code or code or ""
    # compare_digest: constant-time comparison, so the code cannot be guessed by timing.
    if not secrets.compare_digest(given.encode(), expected.get_secret_value().encode()):
        raise HTTPException(status_code=401, detail="access code required")


router = APIRouter(prefix="/api", dependencies=[Depends(require_access)])
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


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, services.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, services.BudgetExceededError):
        return HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, MissingApiKeyError):
        return HTTPException(status_code=503, detail=f"LLM unavailable: {exc}")
    return HTTPException(status_code=500, detail="internal error")


HANDLED = (services.NotFoundError, services.BudgetExceededError, MissingApiKeyError)


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
    except HANDLED as exc:
        raise _http_error(exc) from exc


@router.get("/inspections/{image_id}/image")
async def get_inspection_image(session: SessionDep, image_id: int) -> Response:
    try:
        data, media_type = await services.image_bytes(session, image_id)
    except HANDLED as exc:
        raise _http_error(exc) from exc
    return Response(content=data, media_type=media_type)


@router.post("/inspections/{image_id}/review")
async def review_inspection(session: SessionDep, image_id: int) -> dict:
    try:
        result = await services.review_image(session, image_id)
    except HANDLED as exc:
        raise _http_error(exc) from exc
    return {"review": result, "inspection": await services.image_detail(session, image_id)}


@router.post("/inspections/{image_id}/report")
async def report(session: SessionDep, image_id: int) -> dict:
    try:
        await services.image_detail(session, image_id)  # 404 before spending tokens
        await services.ensure_budget(session)
        result = await agent.write_report(session, image_id)
    except HANDLED as exc:
        raise _http_error(exc) from exc
    await services.record_usage(
        session, "report", result.model, result.input_tokens, result.output_tokens
    )
    return _agent_payload(result)


@router.post("/chat")
async def chat(session: SessionDep, request: ChatRequest) -> dict:
    try:
        await services.ensure_budget(session)
        result = await agent.ask(
            session, request.question, [t.model_dump() for t in request.history]
        )
    except HANDLED as exc:
        raise _http_error(exc) from exc
    await services.record_usage(
        session, "chat", result.model, result.input_tokens, result.output_tokens
    )
    return _agent_payload(result)


@router.get("/stats")
async def stats(session: SessionDep) -> dict:
    data = await services.fleet_statistics(session)
    data["llm_spent_today_usd"] = round(await services.spent_today_usd(session), 4)
    data["llm_daily_budget_usd"] = get_settings().daily_llm_budget_usd
    return data
