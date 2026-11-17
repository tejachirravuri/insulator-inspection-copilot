"""The inspection agent: Claude + tools over detections and maintenance manuals.

A hand-written agentic loop (instead of the SDK's tool runner) because:
  * tools are async and share the request's database session,
  * every step is recorded in a trace that the UI shows (tool, input, result summary, time),
  * the number of rounds is capped (agent_max_steps) so cost per question is bounded.

Grounding rules (system prompt): numbers come from tools (SQL), never from the model; claims
from the manuals carry [S#] citations to the retrieved passages; if the manuals do not cover
something the agent says so instead of improvising.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from inspection_copilot import services
from inspection_copilot.config import get_settings
from inspection_copilot.llm import get_async_client
from inspection_copilot.retrieval import search

SYSTEM_PROMPT = """You are the Insulator Inspection Copilot, an assistant for powerline \
inspectors. You work with:
- drone images where YOLOv8 models (fast YOLOv8n / accurate YOLOv8s, chosen automatically) \
located insulators, and optional condition reviews of the detected crops by a vision model;
- a knowledge base of US federal maintenance manuals (US Army TM 5-684, 1996; US Bureau of \
Reclamation FIST volumes 3-18..3-28 and 4-1B, 2000-2005).

Rules:
- Get facts from tools. Never invent counts, confidences, image ids or manual content.
- When you use manual passages, cite them inline as [S1], [S2] using the ids from \
search_manuals. Only cite passages that support the sentence.
- If the manuals do not cover a question, say so plainly. Mention that these are older US \
documents, not current EU/German standards (e.g. DIN EN / IEC), when that matters.
- Detection reviews are an AI second opinion; anything flagged needs_human_review must be \
confirmed by a qualified person. Do not present AI condition calls as certain.
- Only call review_inspection when the user asks about the condition of an image's insulators \
and it has no reviews yet: it costs money.
- Be concise: short paragraphs or bullet points, answer first."""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_manuals",
        "description": "Hybrid (semantic + keyword) search over the maintenance manuals. "
        "Returns numbered passages [S#] with document, section and pages. Use for any question "
        "about procedures, inspection methods, maintenance intervals, defects and their causes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up, in plain words."},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "list_inspections",
        "description": "List recent inspected images with id, insulator type, detector mode, "
        "number of detections and how many are flagged for human review.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_inspection",
        "description": "Details of one inspected image: detector run (model, mode, whether "
        "auto mode escalated, latency) and every detection with confidence, box and review.",
        "input_schema": {
            "type": "object",
            "properties": {"image_id": {"type": "integer"}},
            "required": ["image_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "review_inspection",
        "description": "Run the vision-model condition review on an image's detections and "
        "store it. Costs money: only use when asked about condition and no reviews exist yet.",
        "input_schema": {
            "type": "object",
            "properties": {"image_id": {"type": "integer"}},
            "required": ["image_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "fleet_statistics",
        "description": "Aggregate statistics over all inspections: images, detections, runs and "
        "latency per detector mode, escalations, review conditions and severities, flags.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


@dataclass
class Source:
    id: str
    document: str
    section: str | None
    pages: str
    text: str


@dataclass
class TraceStep:
    tool: str
    input: dict
    summary: str
    ms: float
    is_error: bool = False


@dataclass
class AgentAnswer:
    answer: str
    sources: list[Source] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stopped_early: bool = False

    @property
    def cost_usd(self) -> float:
        return services.cost_usd(self.model, self.input_tokens, self.output_tokens)


class _Toolbox:
    """Executes tool calls for one question; collects the cited sources."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources: list[Source] = []

    async def search_manuals(self, query: str) -> tuple[str, str]:
        from inspection_copilot.embeddings import get_embedder

        vector = await asyncio.to_thread(get_embedder().embed_query, query)
        hits = await search(self.session, query, vector, "hybrid", top_k=5)
        lines = []
        for hit in hits:
            source = Source(
                id=f"S{len(self.sources) + 1}",
                document=hit.document_title,
                section=hit.section,
                pages=f"{hit.page_start}"
                + (f"-{hit.page_end}" if hit.page_end != hit.page_start else ""),
                text=hit.text,
            )
            self.sources.append(source)
            lines.append(
                f"[{source.id}] {source.document} | {source.section or ''} | p. {source.pages}\n"
                f"{source.text}"
            )
        summary = f"{len(hits)} passages: " + ", ".join(
            f"{s.id} p.{s.pages}" for s in self.sources[-len(hits) :]
        )
        return "\n\n".join(lines) or "No passages found.", summary

    async def list_inspections(self) -> tuple[str, str]:
        rows = await services.list_images(self.session)
        return json.dumps(rows), f"{len(rows)} inspections"

    async def get_inspection(self, image_id: int) -> tuple[str, str]:
        detail = await services.image_detail(self.session, image_id)
        return json.dumps(detail), f"image {image_id}: {len(detail['detections'])} detections"

    async def review_inspection(self, image_id: int) -> tuple[str, str]:
        result = await services.review_image(self.session, image_id)
        detail = await services.image_detail(self.session, image_id)
        return json.dumps({"review": result, "inspection": detail}), (
            f"reviewed {result['reviewed']} crops (${result['cost_usd']})"
        )

    async def fleet_statistics(self) -> tuple[str, str]:
        stats = await services.fleet_statistics(self.session)
        return json.dumps(stats), f"{stats['images']} images, {stats['detections']} detections"

    async def run(self, name: str, tool_input: dict) -> tuple[str, str, bool]:
        method = getattr(self, name, None)
        if name not in {t["name"] for t in TOOLS} or method is None:
            return f"Unknown tool {name}", "unknown tool", True
        try:
            content, summary = await method(**tool_input)
            return content, summary, False
        except services.NotFoundError as exc:
            return str(exc), str(exc), True
        except Exception as exc:  # report tool failures to the model instead of crashing
            await self.session.rollback()
            return f"Tool error: {exc.__class__.__name__}: {exc}", "tool error", True


async def ask(
    session: AsyncSession, question: str, history: list[dict] | None = None
) -> AgentAnswer:
    """Answer one question. `history`: earlier [{"role", "content": str}] turns (text only)."""
    settings = get_settings()
    client = get_async_client()
    toolbox = _Toolbox(session)
    messages: list[dict] = [*(history or []), {"role": "user", "content": question}]
    answer = AgentAnswer(answer="", model=settings.llm_model)

    for _ in range(settings.agent_max_steps):
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            output_config={"effort": settings.agent_effort},
            messages=messages,
        )
        answer.model = response.model
        answer.input_tokens += response.usage.input_tokens
        answer.output_tokens += response.usage.output_tokens

        if response.stop_reason == "refusal":
            answer.answer = "The model declined to answer this request."
            break
        if response.stop_reason != "tool_use":
            answer.answer = "".join(b.text for b in response.content if b.type == "text").strip()
            break

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            started = time.perf_counter()
            content, summary, is_error = await toolbox.run(block.name, block.input)
            answer.trace.append(
                TraceStep(
                    tool=block.name,
                    input=block.input,
                    summary=summary,
                    ms=round((time.perf_counter() - started) * 1000, 1),
                    is_error=is_error,
                )
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    **({"is_error": True} if is_error else {}),
                }
            )
        # All results of one turn go back in ONE user message (keeps parallel tool use working).
        messages.append({"role": "user", "content": results})
    else:
        answer.stopped_early = True
        answer.answer = "Stopped: the step limit was reached before a final answer."

    answer.sources = toolbox.sources
    return answer


REPORT_PROMPT = """Write an inspection report for image {image_id} in Markdown.
Use get_inspection first. If it has detections without reviews, run review_inspection.
Then look up relevant guidance with search_manuals for every condition found (for example \
inspection, cleaning or replacement of the affected insulator type).
Structure:
# Inspection report: image {image_id}
## Summary (2-3 sentences)
## Detections (table: #, confidence, condition, severity, human review needed)
## Recommended actions (each with [S#] citations)
## Limitations (image quality, AI second opinion, age of the manuals)
Do not invent findings; if everything is unclear, say that a closer inspection is needed."""


async def write_report(session: AsyncSession, image_id: int) -> AgentAnswer:
    return await ask(session, REPORT_PROMPT.format(image_id=image_id))
