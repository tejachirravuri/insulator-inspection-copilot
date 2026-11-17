import pytest
from httpx import ASGITransport, AsyncClient

from inspection_copilot import __version__
from inspection_copilot.db import get_session
from inspection_copilot.main import app


async def test_health_does_not_need_database() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


@pytest.mark.db
async def test_ready_when_database_answers(db_session) -> None:
    async def override():
        yield db_session

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
