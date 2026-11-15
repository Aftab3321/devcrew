import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from client import BackendClient
from presentation import STYLE, NAMES, activity, summarize, stage_html

load_dotenv(Path(__file__).resolve().parent / ".env")
client = BackendClient()

st.set_page_config(page_title="DevCrew | Mission Control", page_icon="◈", layout="wide")
st.markdown(STYLE, unsafe_allow_html=True)
job = st.session_state.get("job")
busy = False
try:
    client.health()
    busy = bool(job and client.snapshot(job)["running"])
except Exception:
    st.error(
        "Backend unavailable. In another terminal: cd backend, then uv run crewai run."
    )
    st.stop()

st.markdown(
    '<div class="hero"><div class="eyebrow">AGENTIC SOFTWARE DEVELOPMENT</div><h1>Your team. Every step visible.</h1><p>Brief the team, follow its decisions, and inspect the result. Live agent activity, automatic orchestration, and a workspace for every run.</p></div>',
    unsafe_allow_html=True,
)
workspace, history = st.tabs(["Mission control", "Run history"])


# Display the saved project, review evidence and downloads for one session.
def artifacts(snap, prefix="live"):
    identifier = snap["id"]
    result = snap.get("result")
    files = snap.get("project_files", [])
    if result:
        if result.get("outcome") == "release_candidate":
            st.success(
                "Candidate passed the configured gates. Inspect evidence and limitations below."
            )
        else:
            st.warning(
                "Draft needs attention. Inspect unresolved findings and no-progress events."
            )
        st.caption(result.get("notes", ""))
    if files:
        st.download_button(
            "Download project ZIP",
            client.download(identifier, "project"),
            "devcrew-project.zip",
            "application/zip",
            key=prefix + "_project_" + identifier,
        )
        with st.expander("Project files", expanded=True):
            st.code("\n".join(files))
    st.download_button(
        "Download session & evidence",
        client.download(identifier, "session"),
        identifier + ".zip",
        "application/zip",
        key=prefix + "_session_" + identifier,
    )
    browser = snap.get("browser", {})
    if browser.get("screenshots"):
        st.markdown("**Rendered result · actual desktop and mobile screenshots**")
        cols = st.columns(2)
        for i, name in enumerate(browser["screenshots"]):
            cols[i % 2].image(
                client.artifact(identifier, name),
                caption=name.split("/")[-1],
                width="stretch",
            )
    if browser:
        with st.expander("Executed browser checks"):
            st.dataframe(browser.get("checks", []), hide_index=True, width="stretch")
            for limitation in browser.get("limitations", []):
                st.caption(limitation)
    reports = snap.get("artifacts", {})
    plan = reports.get("plan.json")
    if plan:
        with st.expander("Project plan & selected specialists", expanded=True):
            st.write(plan.get("summary", ""))
            for criterion in plan.get("acceptance_criteria", []):
                st.markdown("- " + criterion)
            st.write("Selected specialists: " + ", ".join(plan.get("specialists", [])))
    for name, data in sorted(reports.items()):
        if not name.startswith(
            (
                "designer",
                "standards",
                "reviewer_",
                "security_",
                "visual_",
                "quality_",
                "static_checks_",
            )
        ) or not isinstance(data, dict):
            continue
        with st.expander(name.removesuffix(".json").replace("_", " ").title()):
            if data.get("summary"):
                st.write(data["summary"])
            for field in [
                "visual_direction",
                "desktop_layout",
                "mobile_layout",
                "typography",
                "asset_direction",
                "brief_adherence",
                "rationale",
            ]:
                if data.get(field):
                    st.markdown(
                        "**" + field.replace("_", " ").title() + "**: " + data[field]
                    )
            if "design_score" in data:
                st.metric("Visual design score", str(data["design_score"]) + " / 10")
            for field in ["issues", "criteria", "color_tokens"]:
                if data.get(field):
                    st.dataframe(data[field], hide_index=True, width="stretch")
            if data.get("decision"):
                st.write("Decision: " + data["decision"].upper())
            for field in [
                "recommendations",
                "required_changes",
                "manual_checks",
                "limitations",
            ]:
                for item in data.get(field, []):
                    st.markdown("- " + item)
            for source in data.get("sources", []):
                if source.get("url", "").startswith(("http://", "https://")):
                    st.link_button(source.get("title", "Source"), source["url"])
    with st.expander("Debug files · structured JSON"):
        names = sorted(reports)
        if names:
            selected = st.selectbox(
                "Artifact", names, key=prefix + "_artifact_" + identifier
            )
            st.json(reports[selected])


with workspace:
    left, right = st.columns([3, 1], gap="large")
    with left:
        st.subheader("01 / Brief your team")
        requirements = st.text_area(
            "What should we build?",
            value="Build a polished responsive login page with email and password validation, a show-password toggle, and accessible controls. Frontend demonstration only; no real authentication.",
            height=140,
            max_chars=4000,
            disabled=busy,
        )
    with right:
        st.markdown(
            '<span class="pill">ADAPTIVE EXECUTION</span>', unsafe_allow_html=True
        )
        st.write("A complete linked frontend project")
        st.caption(
            "A login page here demonstrates UI and validation. Real authentication requires a backend."
        )
        st.caption(
            "Design, standards and security are required. Desktop/mobile rendering and screenshot review check the actual result."
        )
    st.caption("Each run uses the OpenAI model configured in the backend.")
    if st.button(
        "Launch development team", type="primary", disabled=busy, width="stretch"
    ):
        try:
            st.session_state["job"] = client.launch(requirements)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Could not launch run. Inspect the backend terminal and API connection."
            )

    # Poll the current run and render its active stages and recent events.
    @st.fragment(run_every=1)
    def monitor():
        job = st.session_state.get("job")
        st.subheader("02 / Execution overview")
        if not job:
            stages, _, _ = summarize([])
            st.markdown(stage_html(stages), unsafe_allow_html=True)
            st.caption(
                "Ready to launch. Agent and provider activity will appear here while the team works."
            )
            return
        try:
            snap = client.snapshot(job)
        except Exception:
            st.warning("Backend connection interrupted. Check the backend terminal.")
            return
        records = snap["events"]
        if not snap["running"] and st.session_state.get("finished_job") != job:
            st.session_state["finished_job"] = job
            st.rerun()
        stages, requests, tokens = summarize(records)
        elapsed = snap["elapsed"]
        cols = st.columns(4)
        cols[0].metric("Elapsed", f"{int(elapsed)//60:02d}:{int(elapsed)%60:02d}")
        cols[1].metric("Provider requests", str(requests))
        cols[2].metric("Reported tokens", f"{tokens:,}")
        cols[3].metric(
            "Status",
            (
                "Running"
                if snap["running"]
                else (snap["terminal"] or {}).get("status", "Complete").title()
            ),
        )
        completed = sum(s["status"] in {"done", "skipped"} for s in stages.values())
        active_names = [NAMES[r] for r, s in stages.items() if s["status"] == "running"]
        st.progress(
            completed / len(stages),
            text=(
                ("Active: " + " + ".join(active_names))
                if active_names
                else f"{completed} of {len(stages)} phases completed or skipped"
            ),
        )
        if snap["running"]:
            active = [NAMES[r] for r, s in stages.items() if s["status"] == "running"]
            st.info(
                "Working: "
                + (
                    " + ".join(active)
                    if active
                    else "Starting the worker / loading CrewAI"
                )
            )
            if records:
                from datetime import datetime, timezone

                quiet = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(records[-1]["time"])
                ).total_seconds()
                if quiet > 20:
                    st.warning(
                        f"No new event for {int(quiet)}s. The worker may be waiting for a model or tool response; you can stop the run at any time."
                    )
            if st.button("Stop run now", type="secondary", key="stop_run"):
                client.stop(job)
                st.rerun()
        elif snap["terminal"]:
            terminal = snap["terminal"]
            if terminal["status"] == "complete":
                st.success(terminal["message"])
            else:
                st.error(terminal["message"])
        st.markdown(
            stage_html(stages, terminal=not snap["running"]), unsafe_allow_html=True
        )
        st.caption(
            "Session "
            + job
            + " · Request counts include provider attempts and structured-output retries. Tokens update only when a provider reports usage; no dollar estimate is invented."
        )
        st.subheader("Live activity")
        focus = st.selectbox(
            "Filter stage", ["All stages"] + list(NAMES.values()), key="activity_filter"
        )
        shown = [
            e
            for e in records
            if focus == "All stages" or NAMES.get(e.get("agent")) == focus
        ]
        st.dataframe(
            [activity(e) for e in reversed(shown[-80:])],
            hide_index=True,
            width="stretch",
        )
        with st.expander("Raw safe events · debugging"):
            st.code("\n".join(json.dumps(e) for e in records[-100:]), language="json")
            st.download_button(
                "Download event log",
                "\n".join(json.dumps(e) for e in records).encode(),
                "events.jsonl",
                key="live_events",
            )
        if not snap["running"]:
            st.subheader("03 / Deliverables & assessment")
            artifacts(snap)

    monitor()

with history:
    st.subheader("Every run has its own workspace")
    sessions = client.history()
    if sessions:
        selected = st.selectbox(
            "Saved session", [s["id"] for s in sessions], key="history_session"
        )
        snap = client.snapshot(selected)
        st.write(snap.get("request", {}).get("requirements", ""))
        stages, _, _ = summarize(snap["events"])
        st.markdown(
            stage_html(stages, terminal=not snap["running"]), unsafe_allow_html=True
        )
        st.dataframe(
            [activity(e) for e in reversed(snap["events"][-60:])],
            hide_index=True,
            width="stretch",
        )
        artifacts(snap, prefix="history")
    else:
        st.caption("Sessions appear here after launch.")
