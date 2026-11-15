import json
from types import SimpleNamespace
import pytest
from crewai import Agent, Crew, Task, Process, LLM
from crewai.tasks.task_output import TaskOutput
from devcrew_backend.services.models import Application
from devcrew_backend.services.guardrails import application_guardrail
from devcrew_backend.services.ui import activity
from devcrew_backend.services.backend import LiveBackend
from devcrew_backend.services.storage import Session
from devcrew_backend.services.facade import ROOT

from fixture_backend import FixtureBackend

APP = FixtureBackend().execute("developer", "")


# Verify that guardrail attaches parsed output.
def test_guardrail_attaches_parsed_output():
    output = TaskOutput(
        description="test", agent="developer", raw=APP.model_dump_json()
    )
    assert output.pydantic is None
    ok, result = application_guardrail(output)
    assert ok
    assert result.pydantic == APP
    assert result.output_format.value == "pydantic"


# Verify that real crewai task preserves developer guardrail output.
def test_real_crewai_task_preserves_developer_guardrail_output(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.invalid/v1")
    monkeypatch.setattr(Agent, "execute_task", lambda *a, **k: APP.model_dump_json())
    agent = Agent(
        role="Frontend Developer",
        goal="Build page",
        backstory="Test developer",
        llm=LLM(model="openai/gpt-4o-mini"),
    )
    task = Task(
        description="Build page",
        expected_output="Application",
        agent=agent,
        output_pydantic=Application,
        guardrail=application_guardrail,
    )
    result = Crew(agents=[agent], tasks=[task], process=Process.sequential).kickoff()
    assert result.pydantic == APP


# Verify that backend recovers existing json without another model call.
def test_backend_recovers_existing_json_without_another_model_call(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.invalid/v1")
    calls = []

    # Capture the assembled crew or return a canned result without a provider call.
    def kickoff(crew, **kwargs):
        calls.append(1)
        return SimpleNamespace(
            pydantic=None, raw=APP.model_dump_json(), json_dict=None, token_usage=None
        )

    monkeypatch.setattr(Crew, "kickoff", kickoff)
    result = LiveBackend(Session(tmp_path, "test", "test"), research=False).execute(
        "developer", "Build page"
    )
    assert result == APP
    assert len(calls) == 1


# Verify that activity handles nullable event fields.
@pytest.mark.parametrize(
    "kind",
    [
        "agent_step",
        "agent_completed",
        "tool_started",
        "tool_failed",
        "handoff",
        "model_response",
        "run_failed",
    ],
)
def test_activity_handles_nullable_event_fields(kind):
    event = {
        "kind": kind,
        "time": None,
        "tool": None,
        "actor": None,
        "agent": None,
        "usage": None,
        "exception_type": None,
        "sender": None,
        "recipient": None,
        "message": None,
        "operation": None,
    }
    assert isinstance(activity(event)["Activity"], str)


# Verify that all saved run events can be rendered.
def test_all_saved_run_events_can_be_rendered():
    for path in (ROOT / "outputs").glob("*/events.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            activity(event)
