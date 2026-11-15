"""Automatic execution regression tests. All provider requests are mocked."""

import json
import sys
import time
from types import SimpleNamespace
import httpx
import pytest
from devcrew_backend.services.limits import RequestMonitor
from devcrew_backend.services.policy import model_policy
from devcrew_backend.services.storage import Session
from devcrew_backend.services.runner import Job, launch
from devcrew_backend.services.ui import summarize, activity, stage_html
from devcrew_backend.services.models import Plan, Application
from devcrew_backend.services.facade import ROOT


# Verify that requests are observed without a quota.
def test_requests_are_observed_without_a_quota(tmp_path):
    session = Session(tmp_path, "test request", "test")
    monitor = RequestMonitor(session)
    monitor.begin("planner")
    for _ in range(30):
        monitor.before_request(
            "planner",
            httpx.Request(
                "POST",
                "https://provider.invalid",
                headers={"Authorization": "Bearer SECRET"},
            ),
        )
    log = (session.path / "events.jsonl").read_text()
    assert log.count('"kind": "model_request"') == 30
    assert "SECRET" not in log


# Verify that repeated tool action recovers to final answer.
def test_repeated_tool_action_recovers_to_final_answer(tmp_path):
    session = Session(tmp_path, "test request", "test")
    monitor = RequestMonitor(session)
    monitor.begin("planner")
    for _ in range(2):
        req = httpx.Request("POST", "https://provider.invalid")
        monitor.after_response(
            "planner",
            httpx.Response(
                200,
                request=req,
                json={
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "delegate",
                                            "arguments": json.dumps(
                                                {
                                                    "task": "Plan the page",
                                                    "context": "same evidence",
                                                }
                                            ),
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                },
            ),
        )
    request = httpx.Request(
        "POST",
        "https://provider.invalid",
        json={"messages": [], "tools": [{"type": "function"}], "tool_choice": "auto"},
    )
    monitor.before_request("planner", request)
    body = json.loads(request.content)
    assert body["tool_choice"] == "none"
    assert "available results" in body["messages"][-1]["content"]
    assert "loop_recovered" in (session.path / "events.jsonl").read_text()


# Verify that nonrepeated search questions are not mistaken for a loop.
def test_nonrepeated_search_questions_are_not_mistaken_for_a_loop(tmp_path):
    session = Session(tmp_path, "test request", "test")
    monitor = RequestMonitor(session)
    monitor.begin("designer")
    for query in ["contrast requirement", "keyboard focus requirement"]:
        monitor.after_response(
            "designer",
            httpx.Response(
                200,
                request=httpx.Request("POST", "https://provider.invalid"),
                json={
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "search",
                                            "arguments": json.dumps({"query": query}),
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                },
            ),
        )
    assert "designer" not in monitor.finalizing


# Verify that reasoning is model aware without a second planner.
def test_reasoning_is_model_aware_without_a_second_planner():
    assert model_policy("openai/gpt-4o-mini", "developer").mode == "in_task_self_check"
    assert model_policy("openai/o3-mini", "developer").mode == "native"
    assert model_policy("openai/gpt-5-mini", "security").mode == "native"
    assert model_policy("openai/unlisted-model", "security").native_reasoning is None


# Verify that simple planner completes with one real native structured request.
def test_simple_planner_completes_with_one_real_native_structured_request(
    monkeypatch, tmp_path
):
    from devcrew_backend.services.backend import LiveBackend

    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.invalid/v1")
    sent = []
    expected = Plan(
        summary="Login UI demo",
        acceptance_criteria=["Validate email"],
        specialists=[],
        implementation_steps=["Implement form"],
    )

    # Capture the outbound request and return a fake structured provider response.
    def respond(request):
        sent.append(json.loads(request.content))
        from test_schemas import assert_strict_objects

        assert_strict_objects(sent[-1]["response_format"]["json_schema"]["schema"])
        return httpx.Response(
            200,
            json={
                "id": "fake",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": expected.model_dump_json(),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 20,
                    "total_tokens": 40,
                },
            },
        )

    original = httpx.Client

    class TestClient(original):
        # Initialize the test adapter with the synchronization or transport it needs.
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(respond)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", TestClient)
    backend = LiveBackend(Session(tmp_path, "test request", "test"), research=False)
    result = backend.execute("planner", "Build a login page")
    assert result == expected
    assert len(sent) == 1
    assert not sent[0].get("tools")


# Verify that memory is reusable not a quota failure.
def test_memory_is_reusable_not_a_quota_failure(monkeypatch, tmp_path):
    from crewai import Crew
    from devcrew_backend.services.backend import LiveBackend

    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.invalid/v1")

    # Check that the test crew can complete using its supplied result.
    def read_twice(crew, **kwargs):
        assert not crew.agents[0].tools
        from fixture_backend import FixtureBackend

        return SimpleNamespace(
            pydantic=FixtureBackend().execute("developer", ""), token_usage=None
        )

    monkeypatch.setattr(Crew, "kickoff", read_twice)
    LiveBackend(Session(tmp_path, "test request", "test"), research=False).execute(
        "developer", "Build page"
    )


# Verify that stop terminates worker.
def test_stop_terminates_worker(tmp_path):
    session = Session(tmp_path, "test request", "test")
    job = Job(session.path, [sys.executable, "-c", "import time;time.sleep(30)"])
    job.stop()
    assert not job.running
    assert job.snapshot()["terminal"]["status"] == "stopped"


# Verify that live worker reports missing key without a run deadline.
def test_live_worker_reports_missing_key_without_a_run_deadline(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    job = launch("Build a simple page")
    assert not hasattr(job, "limits")
    deadline = time.monotonic() + 40
    try:
        while job.running and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not job.running
        assert job.snapshot()["terminal"] == {
            "status": "failed",
            "message": "Add OPENAI_API_KEY to .env",
        }
    finally:
        if job.running:
            job.stop("Test cleanup")


# Verify that parallel phase progress highlights both branches.
def test_parallel_phase_progress_highlights_both_branches():
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).isoformat()
    records = [
        {"time": stamp, "kind": "agent_started", "agent": r}
        for r in ["designer", "standards"]
    ]
    stages, _, _ = summarize(records)
    rendered = stage_html(stages)
    assert rendered.count('class="stage running"') == 2
    records += [
        {"time": stamp, "kind": "agent_completed", "agent": r}
        for r in ["designer", "standards"]
    ]
    records += [
        {"time": stamp, "kind": "agent_started", "agent": r}
        for r in ["reviewer", "security"]
    ]
    stages, _, _ = summarize(records)
    assert stage_html(stages).count('class="stage running"') == 2
