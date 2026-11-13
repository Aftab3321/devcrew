# Working on DevCrew locally

This CLI-generated project is adapted for the user’s local, two-terminal demonstration. Preserve the pinned CrewAI version unless a change requires an upgrade. Use uv for dependency management. The generated upstream guidance is retained under scaffold_reference/ for provenance.

- Backend: uv run crewai run starts the loopback API using the generated kickoff entry point. Each request invokes the real DevelopmentFlow in a worker.
- Frontend: uv run streamlit run app.py; it must use the HTTP client and must not import backend internals.
- Keep roles/backstories in crews/software_team/config/agents.yaml and task instructions in tasks.yaml. Bind Pydantic schemas and tools in Python.
- Preserve mandatory UI design/standards/security, parallel progress, manual stop, isolated sessions, and no-progress revision recovery. Do not add run deadlines or request quotas.
- Validate structural changes using offline runs and mocked provider tests. Do not initiate paid evaluations, cloud login, tracing uploads, deployment or model comparisons as part of a local migration. Preserve the existing tracing configuration.
- Run backend and frontend tests from their own folders; regenerate implementation diagrams with uv run crewai flow plot when topology changes.
- Keep API keys private. Downloads must remain confined to session artifacts.
