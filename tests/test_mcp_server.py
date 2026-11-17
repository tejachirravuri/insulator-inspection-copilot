"""MCP server: tool discovery and calls against a real database, with a fake embedder."""

from uuid import uuid4

import pytest

from inspection_copilot import mcp_server
from inspection_copilot.models import EMBEDDING_DIM, Chunk, Document


async def test_only_read_only_tools_are_exposed() -> None:
    names = {tool.name for tool in await mcp_server.mcp.list_tools()}
    assert names == {
        "search_manuals",
        "list_inspections",
        "get_inspection",
        "inspection_statistics",
    }
    # The paid vision review must not be reachable from external agents.
    assert not any("review" in name for name in names)


@pytest.mark.db
async def test_search_manuals_returns_cited_passages(db_session, monkeypatch) -> None:
    vec = [0.0] * EMBEDDING_DIM
    vec[0] = 1.0
    doc = Document(source_key=f"test-{uuid4()}", title="Test manual", license="test")
    doc.chunks = [
        Chunk(
            ordinal=0,
            page_start=4,
            page_end=4,
            section="Glaze burns",
            text="Insulators with extensive glaze burns should be replaced without delay.",
            embedding=vec,
        )
    ]
    db_session.add(doc)
    await db_session.flush()

    class SessionContext:  # hand the test's transaction-bound session to the tool
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(mcp_server, "session_factory", SessionContext)
    monkeypatch.setattr(mcp_server, "_embed", lambda query: vec)

    result = await mcp_server.mcp.call_tool("search_manuals", {"query": "glaze burns", "top_k": 3})
    assert not result.is_error
    passage = result.structured_content["result"][0]
    assert passage["document"] == "Test manual"
    assert passage["pages"] == "4"
    assert "replaced without delay" in passage["text"]
