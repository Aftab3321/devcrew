# Streamlit frontend

Start the backend first. From this folder run `uv sync`, then `uv run streamlit run app.py`. Open http://localhost:8501.

This package communicates only through the backend HTTP API. Optional `.env`: `DEVCREW_BACKEND_URL=http://127.0.0.1:8000`. No LLM keys are needed here.

Tests: `uv run pytest tests -q`. See ../README.md for full instructions.
