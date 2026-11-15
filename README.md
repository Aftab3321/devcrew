# DevCrew — AI Software Development Team

DevCrew takes a frontend brief, plans the work, generates a linked web project, and reviews a rendered result. Streamlit displays progress and downloads. A local API starts one worker process for each run. The worker uses the OpenAI API and runs the CrewAI Flow.

## Run locally

Set `OPENAI_API_KEY` in `backend/.env`. Use `backend/.env.example` as a template. Set `MODEL` there to select the OpenAI model, and optionally set `TAVILY_API_KEY` for documentation search. Keep credentials out of Git. Chrome or Edge is needed for browser checks. Set `CHROME_PATH` if the browser is installed in a nonstandard location.

From the project root, start the backend in one terminal.

```powershell
cd backend
uv sync
uv run crewai run
```

In a second terminal, start Streamlit from the project root.

```powershell
cd frontend
uv sync
uv run streamlit run app.py
```

Open http://localhost:8501. The backend listens at http://127.0.0.1:8000 by default. If you change `DEVCREW_BACKEND_PORT` in the backend, point `DEVCREW_BACKEND_URL` in `frontend/.env` at the matching address. Every new run uses the configured model. The test suite uses simulated responses and does not require API credits.

## How a request moves through the application

1. Streamlit sends the brief to the backend, which validates it, creates an output directory, and starts a worker.
2. The Flow plans the work, runs design and standards research in parallel, then passes both results to the developer.
3. The browser renders the generated files. Code, security, and visual review use the current revision and available evidence. QA consolidates the results.
4. The Flow writes a release candidate or requests a targeted patch. It preserves the latest draft when a verified issue persists or the revision stops making progress. Streamlit polls the session and offers the saved files for download.

The developer can adapt the authored Forma login foundation. The example is a frontend demonstration. Production authentication would require a separate implementation.

## File guide

Paths under `backend/src/devcrew_backend/` are relative to that package in the first table.

| File | Responsibility |
| --- | --- |
| `main.py` | CrewAI CLI entry points. Starts the API, runs a supplied trigger brief, or plots the native Flow on demand. |
| `crews/software_team/software_team.py` | Binds individual roles to decorated CrewAI agents and tasks. Builds one stage crew at a time. |
| `crews/software_team/config/agents.yaml` | Role, goal, and backstory for each of the eight predefined agents. |
| `crews/software_team/config/tasks.yaml` | Task-specific prompts and expected deliverables. The Python factory sets the runtime schema, including the developer patch schema. |
| `flows/development_flow.py` | Pydantic Flow state, parallel scheduling, handoffs, evidence checks, and release or revision routing. |
| `services/api.py` | Starlette routes for launching, polling, stopping, history, and artifact downloads. |
| `services/runner.py` | Starts and observes worker processes, handles cancellation, and reads event logs. |
| `services/worker.py` | Executes one saved brief in a child process and records its outcome. |
| `services/facade.py` | Loads backend configuration, initializes the live adapter, and invokes the Flow. |
| `services/backend.py` | Invokes the configured OpenAI model, prepares the available Tavily tool, handles screenshot review, and processes typed results. |
| `services/registry.py` | Associates YAML roles with their Pydantic models and available tool names. |
| `services/models.py` | Defines plans, design and research reports, generated files, patches, review findings, and related output schemas. |
| `services/policy.py` | Chooses guidance based on whether the configured model has native reasoning support. |
| `services/limits.py` | Records model request status and usage and helps recover from repeated tool actions. |
| `services/errors.py` | Turns provider failures into useful messages without exposing private request details. |
| `services/guardrails.py` | Checks input briefs and validates developer output through the CrewAI task guardrail. |
| `services/project.py` | Validates generated paths and linked assets, checks generated files, merges patches, and writes or archives projects. |
| `services/browser.py` | Serves the result locally for browser checks and captures desktop and mobile screenshots. |
| `services/starter.py` | Applies the Forma login foundation and constrains edits to its protected layout. |
| `services/storage.py` | Writes session artifacts and activity logs, and persists the session blackboard. |
| `services/paths.py` | Provides the shared backend root path. |
| `services/ui.py` | Existing event formatting helpers exercised by backend regression tests. The frontend uses its own presentation module. |
| `__init__.py` files | Mark Python packages. The empty tools package comes from the scaffold. |

| File or folder | Responsibility |
| --- | --- |
| `frontend/app.py` | Streamlit brief form, progress cards, timeline, run history, and deliverables. |
| `frontend/client.py` | HTTP calls to the backend. |
| `frontend/presentation.py` | Streamlit display styles and pure helpers for progress and activity formatting. |
| `frontend/.streamlit/` | Streamlit appearance settings. |
| `backend/examples/studio_login/` | The actual HTML, CSS, JavaScript, SVG assets and documentation used by the live login foundation. |
| `backend/knowledge/` | Maintained source notes the standards researcher can use when live search is unavailable. |
| `backend/outputs/` | Generated session folders with events, reports, revisions, screenshots and downloads. |
| `backend/tests/fixture_backend.py` | Predictable stand-in for agent output in tests. |
| `backend/tests/test_api.py` | Exercises API requests, cancellation, download boundaries, and the live-only request format. |
| `backend/tests/test_limits.py` | Tests provider telemetry, reasoning policy, worker controls, and phase progress. |
| `backend/tests/test_output_recovery.py` | Verifies structured output recovery and safe formatting of saved events. |
| `backend/tests/test_project.py` | Verifies file structure, linkage, patches, and the login foundation. |
| `backend/tests/test_schemas.py` | Checks output schemas and safe provider errors. |
| `backend/tests/test_team.py` | Exercises Flow ordering, parallelism, session isolation, and review gates. |
| `frontend/tests/test_app.py` | Exercises Streamlit progress, cancellation and connection errors. |
| `pyproject.toml`, `uv.lock`, `.python-version` in both apps | Declare dependencies, lock resolved versions, and select Python. |
| `.env.example` files | List configuration keys and example values. |

## Coding style and a simpler option

This is a layered Python application. Streamlit handles presentation, Starlette handles HTTP, and the Flow handles orchestration. CrewAI decorators register roles and stage dependencies. Small classes hold stateful resources such as the worker, session, and model adapter. Functions handle file operations and transformations. Pydantic defines the data exchanged by stages. Black formats the Python code, with a purpose comment above each function.

A smaller classroom demo could call the Flow directly from Streamlit. That would eliminate the HTTP client, API, and separate worker entry points. A synchronous call would also make the current live polling and Stop button harder to preserve. If the two-terminal setup and cancellation are important, keeping the process boundary while consolidating internal helpers is a smaller simplification.

Run `uv run pytest -q` from each app folder. If you need the native Flow graph for slides, run `uv run crewai flow plot` from `backend/`.

