import re


class RequestBlocked(ValueError):
    pass


# Apply brief length and blocked-request checks before model execution.
def check_request(text):
    if not 5 <= len(text.strip()) <= 4000:
        raise RequestBlocked("Enter between 5 and 4,000 characters.")
    # Demonstration policy, not a comprehensive intent classifier.
    rules = [
        r"\b(?:steal|harvest|exfiltrate)\b.{0,60}\b(?:passwords?|credentials?|cookies?|tokens?)\b",
        r"\b(?:ransomware|keylogger|credential[- ]stealer)\b",
        r"\b(?:ignore|override)\b.{0,40}\b(?:system|guardrails?|safety)\b",
    ]
    if any(re.search(rule, text, re.I | re.S) for rule in rules):
        raise RequestBlocked("This request matches the demo's blocked-request policy.")


# Validate the structured project before accepting developer output.
def application_guardrail(output):
    try:
        from .models import Application

        app = output.pydantic or Application.model_validate_json(output.raw)
        from .project import validate_project

        validate_project(app)
        from crewai.tasks.output_format import OutputFormat

        output.pydantic = app
        output.raw = app.model_dump_json()
        output.output_format = OutputFormat.PYDANTIC
        return True, output
    except (ValueError, AttributeError):
        return False, "Return a valid Application with a complete HTML document."
