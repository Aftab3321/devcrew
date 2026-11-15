"""One subprocess per UI run; never expose raw provider errors to the UI."""

import json
import sys
from pathlib import Path
from .storage import Session
from .limits import ConfigurationError
from .errors import StructuredOutputError


# Execute one saved brief and persist safe success or failure details.
def main():
    path = Path(sys.argv[1])
    session = Session.attach(path)
    config = json.loads((path / "job.json").read_text(encoding="utf-8"))
    session.event("run_started", message="Worker ready")
    try:
        from .facade import run_team

        result = run_team(config["requirements"], session=session)
        session.write("result.json", result)
        session.write(
            "terminal.json", {"status": "complete", "message": "Workflow completed"}
        )
    except (ConfigurationError, StructuredOutputError) as exc:
        session.event("run_failed", message=str(exc), exception_type=type(exc).__name__)
        session.write("terminal.json", {"status": "failed", "message": str(exc)})
    except BaseException as exc:
        # Exception type + stage/request events are safe to display. Provider messages may contain secrets.
        advice = {
            "ValueError": "Check configuration or structured output; inspect the last completed stage.",
            "AuthenticationError": "Check API credentials.",
            "RateLimitError": "Check provider quota or rate limits.",
            "TimeoutError": "Provider or tool did not respond in time.",
        }.get(
            type(exc).__name__,
            "Inspect the activity timeline and last HTTP status; completed artifacts are preserved.",
        )
        try:
            detail = json.loads(
                (path / "provider_error.json").read_text(encoding="utf-8")
            )
            advice = detail["message"]
        except (OSError, ValueError, KeyError):
            pass
        session.event("run_failed", exception_type=type(exc).__name__, message=advice)
        session.write(
            "terminal.json",
            {"status": "failed", "message": type(exc).__name__ + ": " + advice},
        )


if __name__ == "__main__":
    main()
