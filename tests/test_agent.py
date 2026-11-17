"""The agent loop with a scripted fake Claude client: no API key, no cost, deterministic."""

from types import SimpleNamespace

import pytest

from inspection_copilot import agent


def _usage(i: int = 10, o: int = 5) -> SimpleNamespace:
    return SimpleNamespace(input_tokens=i, output_tokens=o)


def _tool_use(id_: str, name: str, tool_input: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=tool_input)


def _text(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


class FakeMessages:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


@pytest.fixture
def fake_client(monkeypatch):
    def install(responses):
        messages = FakeMessages(responses)
        monkeypatch.setattr(agent, "get_async_client", lambda: SimpleNamespace(messages=messages))
        return messages

    return install


def _response(stop_reason: str, *blocks) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason, content=list(blocks), usage=_usage(), model="claude-opus-5-5"
    )


async def test_tool_results_go_back_in_one_message_and_trace_is_recorded(fake_client, monkeypatch):
    async def fake_list_images(session):
        return [{"id": 1, "detections": 3}]

    async def fake_stats(session):
        return {"images": 1, "detections": 3}

    monkeypatch.setattr(agent.services, "list_images", fake_list_images)
    monkeypatch.setattr(agent.services, "fleet_statistics", fake_stats)
    messages = fake_client(
        [
            _response(
                "tool_use",
                _tool_use("t1", "list_inspections", {}),
                _tool_use("t2", "fleet_statistics", {}),
            ),
            _response("end_turn", _text("One image with 3 insulators.")),
        ]
    )

    result = await agent.ask(session=None, question="How many?")

    assert result.answer == "One image with 3 insulators."
    assert [step.tool for step in result.trace] == ["list_inspections", "fleet_statistics"]
    # Both tool results are sent back together, in the user turn after the assistant turn.
    second_call_messages = messages.calls[1]["messages"]
    tool_results = second_call_messages[-1]["content"]
    assert [r["tool_use_id"] for r in tool_results] == ["t1", "t2"]
    assert result.input_tokens == 20 and result.output_tokens == 10


async def test_unknown_tool_is_reported_as_error_not_raised(fake_client):
    fake_client(
        [
            _response("tool_use", _tool_use("t1", "drop_database", {})),
            _response("end_turn", _text("Sorry.")),
        ]
    )
    result = await agent.ask(session=None, question="x")
    assert result.trace[0].is_error
    assert result.answer == "Sorry."


async def test_step_limit_stops_runaway_loops(fake_client, monkeypatch):
    monkeypatch.setattr(agent.get_settings(), "agent_max_steps", 2)

    async def fake_stats(session):
        return {"images": 0, "detections": 0}

    monkeypatch.setattr(agent.services, "fleet_statistics", fake_stats)
    fake_client(
        [_response("tool_use", _tool_use(f"t{i}", "fleet_statistics", {})) for i in range(2)]
    )
    result = await agent.ask(session=None, question="loop forever")
    assert result.stopped_early
    assert len(result.trace) == 2


async def test_refusal_is_handled(fake_client):
    fake_client([_response("refusal")])
    result = await agent.ask(session=None, question="x")
    assert "declined" in result.answer
