"""Presentation helpers: no API calls or Streamlit state mutations."""

import html
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

NAMES = {
    "planner": "Project planning",
    "designer": "UI / UX research",
    "standards": "Standards research",
    "developer": "Development",
    "browser": "Browser checks",
    "visual": "Visual review",
    "reviewer": "Code review",
    "security": "Security audit",
    "quality": "Quality assessment",
}


# Read a JSON file or return the fallback when it cannot be decoded.
def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# Aggregate phase status and reported provider usage from the event log.
def summarize(records):
    stages = {k: {"status": "queued", "elapsed": None} for k in NAMES}
    for e in records:
        role = e.get("agent")
        if role not in stages:
            continue
        if e["kind"] == "agent_started":
            stages[role] = {"status": "running", "started": e["time"], "elapsed": None}
        elif e["kind"] == "agent_completed":
            stages[role].update(status="done", elapsed=e.get("elapsed_seconds"))
        elif e["kind"] == "agent_skipped":
            stages[role].update(status="skipped")
        elif e["kind"] == "agent_failed":
            stages[role].update(status="failed")
    requests = sum(e["kind"] == "model_request" for e in records)
    tokens = sum(
        e.get("usage", {}).get(
            "total_tokens",
            e.get("usage", {}).get("input_tokens", 0)
            + e.get("usage", {}).get("output_tokens", 0),
        )
        for e in records
        if e["kind"] == "model_response"
    )
    return stages, requests, tokens


# Format a safe event as a row for the activity table.
def activity(e):
    # Optional event fields are explicitly null on final-answer steps.
    e = {key: value for key, value in e.items() if value is not None}
    kind = e["kind"]
    role = NAMES.get(e.get("agent"), e.get("agent", "Workflow"))
    descriptions = {
        "agent_started": "Started",
        "agent_completed": "Completed",
        "agent_skipped": "Not selected",
        "agent_failed": "Failed: " + e.get("exception_type", ""),
        "model_request": "Provider request " + str(e.get("request_number", "")),
        "model_response": "HTTP "
        + str(e.get("http_status", ""))
        + " · "
        + str(e.get("elapsed_seconds", ""))
        + "s · "
        + str(e.get("usage", {}).get("total_tokens", 0))
        + " tokens",
        "agent_step": e.get("actor", "Agent")
        + " · "
        + (e.get("tool") or "step completed"),
        "tool_started": "Calling " + e.get("tool", "tool"),
        "tool_completed": "Finished " + e.get("tool", "tool"),
        "tool_failed": "Tool failed: " + e.get("tool", ""),
        "tool": "Memory " + e.get("operation", "access"),
        "handoff": e.get("sender", "")
        + " → "
        + e.get("recipient", "")
        + ": "
        + e.get("message", ""),
        "code_snapshot": "Saved code revision " + str(e.get("revision", 0)),
        "input_guardrail": "Request validation passed",
    }
    stamp = e.get("time", "")
    try:
        stamp = (
            datetime.fromisoformat(stamp)
            .astimezone(timezone(timedelta(hours=5)))
            .strftime("%H:%M:%S")
        )
    except ValueError:
        pass
    return {
        "Time (PKT)": stamp,
        "Stage": role,
        "Activity": descriptions.get(kind, e.get("message", kind.replace("_", " "))),
    }


STYLE = """
<style>
.block-container{max-width:1440px;padding-top:2rem;padding-bottom:3rem}
[data-testid="stSidebar"]{border-right:1px solid #25304a}
h1,h2,h3{letter-spacing:-.035em}h3{font-size:1.15rem!important}
.hero{background:linear-gradient(115deg,#172a43,#131c30 60%,#17363c);border:1px solid #2b4059;border-radius:22px;padding:30px 34px;margin-bottom:24px;position:relative}
.eyebrow{color:#69e4c3;letter-spacing:3px;font-size:11px;font-weight:700}.hero h1{font-size:38px;margin:10px 0 6px}.hero p{color:#a8b9d0;margin:0;max-width:760px;line-height:1.65}
.stage-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:15px 0 24px}.stage{border:1px solid #2a354d;background:#131c30;border-radius:12px;padding:15px}.stage.running{border-color:#69e4c3;background:#143138}.stage.failed{border-color:#fa8585}.stage .label{font-size:13px;font-weight:600;margin:5px 0}.stage .state{font-size:12px;color:#a8b9d0}.stage .number{font-size:10px;color:#91a2bb;letter-spacing:1px}.stage.done .state{color:#69e4c3}.stage.skipped{opacity:.6}
[data-testid="stMetric"]{background:#131c30;border:1px solid #27344c;border-radius:12px;padding:14px 18px}[data-testid="stMetricLabel"]{color:#a8b9d0!important}
button[kind="primary"] p,button[kind="primary"]{color:#092923!important;font-weight:650!important}
[data-testid="stExpander"]{border-color:#29364f;border-radius:12px}.footnote{font-size:12px;color:#91a2bb;margin-top:12px}.pill{display:inline-block;background:#203c40;color:#8df0d4;border:1px solid #37615c;padding:5px 11px;border-radius:30px;font-size:11px;font-weight:700;margin-bottom:10px}
@media(max-width:900px){.stage-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{padding:22px}.hero h1{font-size:29px}}
</style>
"""


# Render stage cards and highlight every currently active branch.
def stage_html(stages, terminal=False):
    cards = []
    for i, (role, label) in enumerate(NAMES.items(), 1):
        item = stages[role]
        state = item["status"]
        if terminal and state == "running":
            state = "stopped"
        if terminal and state == "queued":
            state = "not reached"
        elapsed = item.get("elapsed")
        if state == "running" and item.get("started"):
            elapsed = (
                datetime.now(timezone.utc) - datetime.fromisoformat(item["started"])
            ).total_seconds()
        detail = state.capitalize() + (
            " · " + str(round(elapsed)) + "s" if elapsed is not None else ""
        )
        cards.append(
            '<div class="stage '
            + html.escape(state)
            + '"><div class="number">'
            + str(i).zfill(2)
            + '</div><div class="label">'
            + label
            + '</div><div class="state">'
            + html.escape(detail)
            + "</div></div>"
        )
    return '<div class="stage-grid">' + "".join(cards) + "</div>"
