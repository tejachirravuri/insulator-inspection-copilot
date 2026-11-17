"""Access code and daily LLM budget: the two guards for a public deployment."""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from inspection_copilot.config import get_settings
from inspection_copilot.db import get_session
from inspection_copilot.main import app
from inspection_copilot.models import LlmUsage

pytestmark = pytest.mark.db


@pytest.fixture
async def client(db_session):
    async def override():
        yield db_session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_access_code_is_required_when_configured(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "access_code", SecretStr("s3cret"))
    assert (await client.get("/api/stats")).status_code == 401
    assert (await client.get("/api/stats", headers={"X-Access-Code": "wrong"})).status_code == 401
    assert (await client.get("/api/stats", headers={"X-Access-Code": "s3cret"})).status_code == 200
    assert (await client.get("/api/stats?code=s3cret")).status_code == 200  # for <img> tags


async def test_health_stays_open_with_access_code(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "access_code", SecretStr("s3cret"))
    assert (await client.get("/health")).status_code == 200


async def test_chat_is_refused_when_daily_budget_is_spent(client, db_session, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "access_code", None)
    monkeypatch.setattr(get_settings(), "daily_llm_budget_usd", 1.0)
    db_session.add(
        LlmUsage(purpose="chat", model="m", input_tokens=1, output_tokens=1, cost_usd=1.5)
    )
    await db_session.flush()
    response = await client.post("/api/chat", json={"question": "hello"})
    assert response.status_code == 429
    assert "budget" in response.json()["detail"]


async def test_upload_without_yolo_weights_returns_503(client, monkeypatch) -> None:
    from inspection_copilot import services
    from inspection_copilot.detection import WeightsMissingError

    monkeypatch.setattr(get_settings(), "access_code", None)

    async def no_weights(*args, **kwargs):
        raise WeightsMissingError("YOLO weights not available in this deployment: x.pt")

    monkeypatch.setattr(services, "inspect_image", no_weights)
    response = await client.post(
        "/api/inspections",
        files={"file": ("a.jpg", b"\xff\xd8\xff", "image/jpeg")},
        data={"insulator_type": "glass"},
    )
    assert response.status_code == 503
    assert "weights" in response.json()["detail"]
