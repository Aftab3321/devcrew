"""Loopback API shared by the CLI service and the Streamlit client."""

import io
import json
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, FileResponse
from starlette.routing import Route
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .paths import BACKEND_ROOT
from .runner import launch, events
from .guardrails import check_request
from .project import project_zip

OUTPUTS = BACKEND_ROOT / "outputs"
JOBS = {}
ALLOWED = {".json", ".jsonl", ".html", ".txt", ".css", ".js", ".svg", ".md", ".png"}


# Load a saved JSON artifact or return the caller's fallback.
def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# Resolve a validated session ID inside the backend output root.
def session_path(identifier):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError("Invalid session ID")
    path = (OUTPUTS / identifier).resolve()
    if not path.is_relative_to(OUTPUTS.resolve()) or not path.is_dir():
        raise FileNotFoundError("Session not found")
    return path


# Allow only exported artifact types that resolve within the session.
def safe_file(path, name):
    candidate = (path / name).resolve()
    if (
        not candidate.is_relative_to(path.resolve())
        or not candidate.is_file()
        or candidate.suffix not in ALLOWED
        or any(
            part.startswith(".") or part == "browser-profile"
            for part in Path(name).parts
        )
    ):
        raise FileNotFoundError("Artifact not found")
    return candidate


# Choose the final project folder or the most recent draft.
def project_folder(path):
    if (path / "project").is_dir():
        return path / "project"
    versions = [
        p for p in path.glob("project_v*") if p.is_dir() and p.name[9:].isdigit()
    ]
    return max(versions, key=lambda p: int(p.name[9:]), default=None)


# Assemble status, events and relative artifact paths for the frontend.
def snapshot(identifier):
    path = session_path(identifier)
    job = JOBS.get(identifier)
    data = (
        job.snapshot()
        if job
        else {
            "running": False,
            "elapsed": 0,
            "events": events(path),
            "result": read_json(path / "result.json"),
            "terminal": read_json(path / "terminal.json"),
        }
    )
    if not data["running"] and not data["terminal"] and not data["result"]:
        data["terminal"] = {
            "status": "interrupted",
            "message": "No active worker or final status. Saved artifacts are available.",
        }
    data["id"] = identifier
    # Never make the frontend depend on this machine's paths.
    if data["result"]:
        data["result"] = {
            k: v
            for k, v in data["result"].items()
            if k not in {"project_dir", "output_dir"}
        }
    data["request"] = read_json(path / "request.json", {})
    data["artifacts"] = {
        p.name: read_json(p)
        for p in path.glob("*.json")
        if p.name not in {"job.json", "provider_error.json"}
    }
    for result in data["artifacts"].values():
        if isinstance(result, dict):
            result.pop("project_dir", None)
            result.pop("output_dir", None)
    project = project_folder(path)
    data["project_files"] = (
        [
            p.relative_to(project).as_posix()
            for p in sorted(project.rglob("*"))
            if p.is_file() and p.resolve().is_relative_to(project.resolve())
        ]
        if project
        else []
    )
    screenshots = []
    reports = sorted(
        path.glob("browser_v*.json"), key=lambda p: int(p.stem.split("_v")[-1])
    )
    if reports:
        report = read_json(reports[-1], {})
        for image in report.get("screenshots", []):
            image = Path(image)
            try:
                relative = image.resolve().relative_to(path.resolve()).as_posix()
                safe_file(path, relative)
                screenshots.append(relative)
            except (ValueError, FileNotFoundError):
                pass
        data["browser"] = {**report, "screenshots": screenshots}
    return data


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    requirements: str = Field(min_length=1, max_length=4000)


# Report that the API process can respond to requests.
async def health(request):
    return JSONResponse(
        {"status": "ok", "service": "devcrew-backend", "version": "0.2.0"}
    )


# List existing sessions or validate a brief and launch a live worker.
async def runs(request):
    if request.method == "GET":
        items = []
        if OUTPUTS.exists():
            for path in sorted(OUTPUTS.iterdir(), reverse=True):
                if path.is_dir() and re.fullmatch(r"[A-Za-z0-9_-]+", path.name):
                    items.append(
                        {
                            "id": path.name,
                            "request": read_json(path / "request.json", {}),
                            "terminal": read_json(path / "terminal.json"),
                        }
                    )
        return JSONResponse(items)
    try:
        payload = RunRequest.model_validate(await request.json())
        check_request(payload.requirements)
        job = await run_in_threadpool(launch, payload.requirements)
        JOBS[job.path.name] = job
        return JSONResponse({"id": job.path.name}, status_code=202)
    except (ValueError, ValidationError):
        return JSONResponse(
            {
                "error": "Invalid or blocked brief. Use a benign frontend request of 1–4000 characters."
            },
            status_code=400,
        )


# Return the requested session snapshot or a 404 response.
async def status(request):
    try:
        return JSONResponse(
            await run_in_threadpool(snapshot, request.path_params["id"])
        )
    except (ValueError, FileNotFoundError):
        return JSONResponse({"error": "Session not found"}, status_code=404)


# Stop a worker owned by this API process.
async def stop(request):
    job = JOBS.get(request.path_params["id"])
    if not job:
        return JSONResponse(
            {"error": "No active worker owned by this service"}, status_code=404
        )
    await run_in_threadpool(job.stop)
    return JSONResponse({"status": "stopped"})


# Build the requested ZIP from validated session files.
async def download(request):
    try:
        path = session_path(request.path_params["id"])
        kind = request.path_params["kind"]
        if kind == "project":
            project = project_folder(path)
            if project is None:
                raise FileNotFoundError()
            # Validate all entries before bundling, including symlinks.
            for file in project.rglob("*"):
                if file.is_file():
                    safe_file(project, file.relative_to(project).as_posix())
            content = await run_in_threadpool(project_zip, project)
        elif kind == "session":
            # Archive allowed evidence without including private worker logs.
            def bundle():
                out = io.BytesIO()
                with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
                    for file in path.rglob("*"):
                        if not file.is_file():
                            continue
                        try:
                            safe_file(path, file.relative_to(path).as_posix())
                        except FileNotFoundError:
                            continue
                        archive.write(file, file.relative_to(path).as_posix())
                return out.getvalue()

            content = await run_in_threadpool(bundle)
        else:
            raise FileNotFoundError()
        return Response(
            content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="devcrew-{kind}.zip"'
            },
        )
    except (ValueError, FileNotFoundError):
        return JSONResponse({"error": "Download not found"}, status_code=404)


# Serve a validated session file as an attachment.
async def file(request):
    try:
        path = safe_file(
            session_path(request.path_params["id"]), request.path_params["name"]
        )
        return FileResponse(
            path,
            headers={
                "Content-Disposition": "attachment",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except (ValueError, FileNotFoundError):
        return JSONResponse({"error": "Artifact not found"}, status_code=404)


# Stop active workers when the API service shuts down.
@asynccontextmanager
async def lifespan(app):
    yield
    for job in list(JOBS.values()):
        if job.running:
            await run_in_threadpool(job.stop, "Backend service shut down")


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health),
        Route("/runs", runs, methods=["GET", "POST"]),
        Route("/runs/{id}", status),
        Route("/runs/{id}/stop", stop, methods=["POST"]),
        Route("/runs/{id}/download/{kind}", download),
        Route("/runs/{id}/files/{name:path}", file),
    ],
)
