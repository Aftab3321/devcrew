# DevCrew — AI Software Development Team

The active application is split into a CrewAI backend and a Streamlit frontend. The backend was created with the real CrewAI CLI, then adapted from its classic Flow scaffold. See backend/SCAFFOLD_PROVENANCE.md and backend/scaffold_reference/ for the original generated code.

## Start in two terminals

Terminal 1 — backend, from this project folder:

~~~powershell
cd backend
uv sync
uv run crewai run
~~~

Keep that terminal running. The command uses the generated kickoff entry point to start this application's local API at http://127.0.0.1:8000. Requests received by the API launch the real CrewAI DevelopmentFlow in an isolated worker process. This service startup is an application customization; CrewAI does not generate an HTTP server automatically.

Terminal 2 — frontend, from this project folder:

~~~powershell
cd frontend
uv sync
uv run streamlit run app.py
~~~

Open http://localhost:8501. Choose Offline rehearsal for a fixed sample without model/search charges. Live CrewAI uses backend/.env. Existing configuration has been copied there; future key/model changes belong there. The frontend needs no model or Tavily credentials.

Each folder has its own pyproject.toml, uv.lock, .python-version and virtual environment. Python 3.13 is pinned to match the tested environment. If uv is not on PATH, use C:\Users\Aftab\.local\bin\uv.exe.

## Source map

| Location | Responsibility |
| --- | --- |
| backend/src/devcrew_backend/main.py | CrewAI kickoff, plot and trigger entry points |
| backend/src/devcrew_backend/flows/development_flow.py | Typed Flow, parallel stages, review and revision routing |
| backend/src/devcrew_backend/crews/software_team/software_team.py | Classic @CrewBase, @agent, @task and @crew definitions |
| backend/src/devcrew_backend/crews/software_team/config/agents.yaml | Authoritative role, goal and backstory definitions |
| backend/src/devcrew_backend/crews/software_team/config/tasks.yaml | Authoritative task instructions |
| backend/src/devcrew_backend/services/backend.py | Model adapter, request telemetry, Tavily MCP tool and visual image review |
| backend/src/devcrew_backend/services/api.py | Local HTTP routes, history and artifact downloads |
| backend/src/devcrew_backend/services/runner.py | Worker lifecycle and manual cancellation |
| backend/src/devcrew_backend/services/models.py | Pydantic plans, designs, projects, patches and reports |
| frontend/app.py | Streamlit mission control |
| frontend/client.py | HTTP-only backend client |
| frontend/presentation.py | Styles and parallel phase display helpers |
| backend/outputs/ | New isolated session folders |

The manager plans using predefined capabilities. UI design and standards run in parallel, development waits for both, then code review, security and screenshot review run in parallel before QA. Login projects transparently adapt the authored Forma design foundation. Native reasoning is kept for supported reasoning models; other models receive in-task checking guidance. There are no user-configured request budgets or overall run deadlines. HTTP operations still have normal network timeouts.

The original application, its configuration, previous backups and run history are preserved under legacy/. Use the two-terminal commands above for the migrated application. Previous sessions in legacy/outputs/ have not been mixed into the new backend history.

## Configuration

Copy backend/.env.example to backend/.env only if creating a fresh configuration. Do not overwrite existing credentials. MODEL and OPENAI_API_KEY configure the live model. TAVILY_API_KEY enables external search; failed retrieval is recorded and maintained standards notes are labeled honestly. The monitored live provider remains native OpenAI, as in the original app. Chrome or Edge is required for actual browser screenshots/checks; CHROME_PATH can specify the executable.

Optional backend port: DEVCREW_BACKEND_PORT=8000 in backend/.env. Match frontend/.env with DEVCREW_BACKEND_URL=http://127.0.0.1:8000 when changing it. The API binds to loopback and is a local demonstration service, without production authentication.

## Graphs and verification

From backend:

~~~powershell
uv run crewai flow plot
uv run pytest tests -q
~~~

From frontend:

~~~powershell
uv run pytest tests -q
~~~

The graph command generates backend/diagrams/crewai_flow.html using CrewAI's actual Flow plotting API, plus execution.mmd, execution.svg and execution.md with the full application topology. diagram_sources.json records hashes of the implementation and YAML. Static topology describes possible paths; a session's events.jsonl records what actually ran. The UI Architecture tab can regenerate and download them.

The backup is backups/pre_scaffold_20261110_134518.zip with an internal SHA-256 manifest. It includes the previous local configuration and should stay private.

Validation for this migration uses offline workers, actual browser rendering, HTTP downloads, Streamlit AppTest and mocked provider requests. It does not claim fresh paid-model quality evaluation or CrewAI AMP evaluation.
