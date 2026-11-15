# CrewAI backend

From this folder: `uv sync`, then `uv run crewai run`. The local API stays running at http://127.0.0.1:8000. Set OPENAI_API_KEY in backend/.env before launching a run. Start the frontend in another terminal.

Generate the native CrewAI graph on demand: `uv run crewai flow plot`. Tests: `uv run pytest tests -q`.

See ../README.md for architecture, configuration, and the file guide.
