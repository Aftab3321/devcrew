# DevCrew frontend

The Streamlit frontend submits briefs to the local backend and displays progress, run history and generated artifacts. Start the backend separately before opening the UI.

## 1. Create an environment

Use Python 3.13. Pick one method and start from the repository root.

**Python venv (PowerShell)**

~~~powershell
cd frontend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install uv
uv sync --locked
~~~

On macOS or Linux, use python3.13 -m venv .venv and source .venv/bin/activate. Skip installing uv if it is already available. uv sync can also create the project environment for you.

**Conda (PowerShell)**

~~~powershell
conda create -n devcrew-frontend python=3.13 pip
conda activate devcrew-frontend
cd frontend
python -m pip install "streamlit>=1.41,<2" "httpx>=0.27,<1" "python-dotenv>=1,<2"
~~~

The uv route uses the committed lockfile. The Conda command installs dependencies from the ranges declared in pyproject.toml.

## 2. Configure and start

The default API URL is http://127.0.0.1:8000. For a different port, copy .env.example to .env on first setup and set DEVCREW_BACKEND_URL to the matching address. Keep the model API key in the backend's .env.

With the uv environment, run:

~~~powershell
uv run streamlit run app.py
~~~

With the Conda pip installation, run:

~~~powershell
python -m streamlit run app.py
~~~

Open http://localhost:8501. If connection fails, confirm the backend terminal is running and that the configured URL responds at /health.

## 3. Folder structure

| File | Purpose |
| --- | --- |
| app.py | Configures the page, checks API availability, displays the brief form, polls the active job, and renders history and artifacts. |
| client.py | BackendClient wraps requests for health, launch, snapshot, history, cancellation, ZIPs and individual artifacts. |
| presentation.py | Styles the page and converts raw events into human-readable phase cards, timings and activity rows. |
| .streamlit/config.toml | Sets the local theme and headless server options when present. |
| .env.example | Shows the optional backend URL setting. |
| pyproject.toml | Declares Streamlit, HTTPX, python-dotenv, and development test dependencies. |
| uv.lock / .python-version | Record dependency resolution and select the Python version. |
| tests/test_app.py | Exercises display of parallel stages, stopping a run and reporting connection failures with a mocked client. |

## 4. Read app.py from top to bottom

1. Page configuration and backend health. dotenv loads the local settings and BackendClient points at the local Starlette service.
2. Brief form. Clicking Launch sends only the requirements and stores the returned session ID in Streamlit session state.
3. Monitor fragment. The fragment polls the run, updates the cards and shows active phases together. The Stop button calls the backend, which terminates the worker.
4. Artifact renderer. It displays the project tree, screenshots, browser checks, structured reports, and download controls.
5. History tab. It lists saved sessions by asking the API, then renders the selected session's snapshot and evidence.

The browser talks to Streamlit. Streamlit's Python process talks to Starlette through HTTPX. The CrewAI backend owns agent execution, credentials and project files.

## 5. Test the frontend

~~~powershell
uv run pytest tests -q
~~~

For the classroom demo, point out which phases run in parallel, inspect one structured handoff and download the project. Compare the runtime timeline with the Flow source when explaining why stages start in that order. See [the backend guide](../backend/README.md) for the lab commands and full workflow.
