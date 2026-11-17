"""MCP server: the copilot's tools for any MCP client (Claude Desktop, Claude Code, IDE agents).

    python -m inspection_copilot.mcp_server      # stdio transport

The Model Context Protocol lets an external agent discover and call these tools. They reuse
the same service layer as the REST API and the built-in agent, so behaviour is identical.

Only read-only tools are exposed. The paid vision review stays behind the REST API, where the
daily LLM budget applies, so an external agent can query everything but cannot spend money.
Logs go to stderr: on the stdio transport, stdout carries the protocol messages.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot import services
from inspection_copilot.db import get_sessionmaker
from inspection_copilot.retrieval import search

INSTRUCTIONS = """Tools for powerline insulator inspection data and maintenance manuals.
Inspections are drone images where YOLOv8 located insulators; some detections carry a vision-
model review (condition, severity, needs_human_review). The manuals are US federal documents
(TM 5-684, 1996; Bureau of Reclamation FIST, 2000-2005), not current EU standards. Cite manual
passages by document, section and page."""

mcp = MCPServer("insulator-inspection", instructions=INSTRUCTIONS)

# Overridable in tests: returns a new AsyncSession.
session_factory: Callable[[], AsyncSession] = lambda: get_sessionmaker()()  # noqa: E731


def _embed(query: str) -> list[float]:
    from inspection_copilot.embeddings import get_embedder

    return get_embedder().embed_query(query)


@mcp.tool()
async def search_manuals(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Hybrid (semantic + keyword) search over the maintenance manuals. Returns passages with
    document, section and page range, best first."""
    top_k = max(1, min(top_k, 10))
    vector = await asyncio.to_thread(_embed, query)
    async with session_factory() as session:
        hits = await search(session, query, vector, "hybrid", top_k)
    return [
        {
            "document": h.document_title,
            "section": h.section,
            "pages": f"{h.page_start}-{h.page_end}"
            if h.page_end != h.page_start
            else str(h.page_start),
            "text": h.text,
        }
        for h in hits
    ]


@mcp.tool()
async def list_inspections() -> list[dict[str, Any]]:
    """Recent inspected images: id, insulator type, detector mode, number of detections and how
    many are flagged for human review."""
    async with session_factory() as session:
        return await services.list_images(session)


@mcp.tool()
async def get_inspection(image_id: int) -> dict[str, Any]:
    """One inspection: detector run (model, mode, escalation, latency) and every detection with
    confidence, bounding box and vision review."""
    async with session_factory() as session:
        return await services.image_detail(session, image_id)


@mcp.tool()
async def inspection_statistics() -> dict[str, Any]:
    """Aggregates over all inspections: images, detections, runs per detector mode with average
    latency and escalations, review conditions and severities, human-review flags."""
    async with session_factory() as session:
        return await services.fleet_statistics(session)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
