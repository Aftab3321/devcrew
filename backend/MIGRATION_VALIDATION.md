# Migration validation

Validated locally on 10 November 2026 with Python 3.13.9 and CrewAI 1.15.39.

- Verified all 826 SHA-256 hashes in backups/pre_scaffold_20261110_134518.zip and its ZIP integrity.
- Installed backend and frontend independently with uv; both have separate lockfiles and environments.
- Started the backend using the actual installed crewai run command. /health returned HTTP 200. The temporary test service used port 8017 and was stopped after verification.
- Generated diagrams using crewai flow plot; exit status 0.
- Backend pytest: 54 passed. Provider responses were mocked; no paid LLM or Tavily requests were made.
- Frontend pytest: 2 passed, including parallel phase display, Stop control and readable backend-unavailable state.
- Offline HTTP run 20261110T111243_216dd00949e1: release_candidate, eight linked files, 21 actual desktop/mobile browser checks passed, two screenshots served through the API, runnable project ZIP validated.
- Offline launch through Streamlit AppTest: 20261110T111812_cce9061b330a. Completed with screenshots and download controls, without app exceptions.
- Real HTTP cancellation: 20261110T111834_4ad4d198f67f stopped the owned worker and saved stopped status.
- Download and traversal tests reject private configuration, worker logs and paths outside the session.

These results validate the migration and offline integration. They do not establish live model design quality or successful live standards retrieval. The native OpenAI request-monitor adapter and screenshot review behavior are preserved from the original project. CrewAI emits upstream callback-checkpoint and deprecation warnings during mocked crew tests; no checkpoint restoration is used here.
