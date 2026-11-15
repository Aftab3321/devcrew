"""Expose actionable provider error categories without logging request bodies or secrets."""

import re


# Convert provider error details into a user-safe diagnosis.
def provider_error(status, body):
    error = body.get("error", {}) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        error = {}
    param = str(error.get("param") or "")
    code = str(error.get("code") or error.get("type") or "")
    param = re.sub(r"[^a-zA-Z0-9_.\[\]-]", "", param)[:100]
    code = re.sub(r"[^a-zA-Z0-9_.-]", "", code)[:100]
    message = str(error.get("message") or "")
    category = {
        400: "Provider rejected the request",
        401: "Invalid API credentials",
        403: "Model access denied",
        404: "Model or endpoint not found",
        429: "Provider rate limit or quota",
    }.get(status, "Provider request failed")
    if message.startswith("Invalid schema for response_format"):
        safe = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message)[:1200]
        category = "Structured-output schema rejected: " + safe
    elif param:
        category += " (parameter: " + param + ")"
    return {
        "message": category,
        "http_status": status,
        "parameter": param,
        "provider_code": code,
    }


class StructuredOutputError(ValueError):
    """A safe summary of output validation failure, without echoing model content."""
