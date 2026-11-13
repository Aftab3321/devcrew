"""Public entry points used by the demo interface."""
import os
from pathlib import Path
from dotenv import load_dotenv
from .guardrails import validate_html, check_request
from .models import Application
from .limits import ConfigurationError

from .paths import BACKEND_ROOT
ROOT = BACKEND_ROOT

def run_team(requirements, on_stage=lambda name, content: None, *, offline=False,
             research=None, output_base=None, session=None):
    load_dotenv(ROOT / ".env")
    from .storage import Session
    from .backend import LiveBackend, FixtureBackend
    from ..flows.development_flow import DevelopmentFlow
    check_request(requirements)
    if not offline and not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("Add OPENAI_API_KEY to .env")
    if not offline and research and not os.getenv("TAVILY_API_KEY"):
        raise ConfigurationError("Add TAVILY_API_KEY or disable external research")
    session = session or Session(Path(output_base) if output_base else ROOT / "outputs", requirements,
                      "offline fixture" if offline else "live")
    backend = FixtureBackend() if offline else LiveBackend(session, research)
    flow = DevelopmentFlow(session, backend, on_stage=on_stage)
    try:
        flow.kickoff(inputs={"requirements": requirements})
        return {"project_dir":str(session.path / ("project" if flow.state.outcome=="release_candidate" else f"project_v{flow.state.revision}")), "notes":flow.state.app.notes,
                "usage":backend.usage, "session_id":session.id, "output_dir":str(session.path),
                "outcome":flow.state.outcome, "revision":flow.state.revision}
    except BaseException as exc:
        session.event("failed", exception_type=type(exc).__name__)
        session.write("state.json", flow.state.model_dump())
        on_stage("failure", "Run failed. Session: " + session.id + ". Completed artifacts were preserved.")
        raise

def rehearsal(on_stage=lambda name, content: None):
    return run_team("Build the fixed rehearsal task tracker", on_stage, offline=True)
