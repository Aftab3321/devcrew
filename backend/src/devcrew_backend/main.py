"""CLI entry points from the generated CrewAI Flow project."""

import json
import os
import sys
from dotenv import load_dotenv
from .services.paths import BACKEND_ROOT

load_dotenv(BACKEND_ROOT / ".env")


# Start the loopback API when CrewAI runs the scaffold entry point.
def kickoff():
    """Keep the local backend available; launched by crewai run."""
    import uvicorn

    port = int(os.getenv("DEVCREW_BACKEND_PORT", "8000"))
    uvicorn.run("devcrew_backend.services.api:app", host="127.0.0.1", port=port)


# Generate the native Flow graph without starting an agent run.
def plot():
    from .flows.development_flow import DevelopmentFlow

    DevelopmentFlow(None, None).plot()


# Read the trigger brief and execute the live development Flow.
def run_with_trigger():
    from .services.facade import run_team

    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    result = run_team(payload["requirements"])
    print(json.dumps(result))


if __name__ == "__main__":
    kickoff()
