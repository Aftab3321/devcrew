"""Public entry points used by the demo interface."""

import os
from pathlib import Path
from dotenv import load_dotenv
from .guardrails import check_request
from .limits import ConfigurationError

from .paths import BACKEND_ROOT

ROOT = BACKEND_ROOT


# Load backend credentials, start the live Flow and return the session result.
def run_team(
    requirements,
    on_stage=lambda name, content: None,
    *,
    research=None,
    output_base=None,
    session=None,
):
    load_dotenv(ROOT / ".env")
    check_request(requirements)
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("Add OPENAI_API_KEY to .env")
    if research and not os.getenv("TAVILY_API_KEY"):
        raise ConfigurationError("Add TAVILY_API_KEY or disable external research")

    from .storage import Session
    from .backend import LiveBackend
    from ..flows.development_flow import DevelopmentFlow

    session = session or Session(
        Path(output_base) if output_base else ROOT / "outputs", requirements, "live"
    )
    backend = LiveBackend(session, research)
    flow = DevelopmentFlow(session, backend, on_stage=on_stage)
    try:
        flow.kickoff(inputs={"requirements": requirements})
        return {
            "project_dir": str(
                session.path
                / (
                    "project"
                    if flow.state.outcome == "release_candidate"
                    else f"project_v{flow.state.revision}"
                )
            ),
            "notes": flow.state.app.notes,
            "usage": backend.usage,
            "session_id": session.id,
            "output_dir": str(session.path),
            "outcome": flow.state.outcome,
            "revision": flow.state.revision,
        }
    except BaseException as exc:
        session.event("failed", exception_type=type(exc).__name__)
        session.write("state.json", flow.state.model_dump())
        on_stage(
            "failure",
            "Run failed. Session: "
            + session.id
            + ". Completed artifacts were preserved.",
        )
        raise
