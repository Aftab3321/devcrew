import io
import zipfile
from types import SimpleNamespace
from starlette.testclient import TestClient
from devcrew_backend.services import api
from devcrew_backend.services.storage import Session
from devcrew_backend.services.project import materialize
from fixture_backend import FixtureBackend


# Verify that api artifacts and path boundaries.
def test_api_artifacts_and_path_boundaries(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "OUTPUTS", tmp_path / "outputs")
    session = Session(api.OUTPUTS, "Build a login page", "offline fixture")
    materialize(FixtureBackend().execute("developer", ""), session.path / "project")
    session.write(
        "result.json",
        {
            "outcome": "release_candidate",
            "project_dir": "private-path",
            "output_dir": "private-path",
        },
    )
    session.write("terminal.json", {"status": "complete", "message": "done"})
    (session.path / "worker.log").write_text("private diagnostics")
    (session.path / ".env").write_text("SECRET")
    with TestClient(api.app) as client:
        assert client.get("/health").json()["status"] == "ok"
        snap = client.get("/runs/" + session.id).json()
        assert snap["result"] == {"outcome": "release_candidate"}
        assert "assets/css/styles.css" in snap["project_files"]
        assert client.get("/runs/" + session.id + "/files/.env").status_code == 404
        assert (
            client.get("/runs/" + session.id + "/files/worker.log").status_code == 404
        )
        assert (
            client.get(
                "/runs/" + session.id + "/files/%2e%2e/%2e%2e/pyproject.toml"
            ).status_code
            == 404
        )
        assert client.get("/runs/missing").status_code == 404
        assert (
            client.post("/runs", json={"requirements": "Build a keylogger"}).status_code
            == 400
        )
        assert (
            client.post(
                "/runs", json={"requirements": "Build a login page", "offline": True}
            ).status_code
            == 400
        )
        for kind in ["project", "session"]:
            response = client.get("/runs/" + session.id + "/download/" + kind)
            assert response.status_code == 200
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                assert archive.testzip() is None
                assert ".env" not in archive.namelist()
                assert "worker.log" not in archive.namelist()


# Verify that api launch and cancel.
def test_api_launch_and_cancel(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(api, "JOBS", {})
    session = Session(api.OUTPUTS, "Build a login page", "offline fixture")
    stopped = []
    job = SimpleNamespace(
        path=session.path, running=True, stop=lambda *args: stopped.append(True)
    )
    monkeypatch.setattr(api, "launch", lambda requirements: job)
    with TestClient(api.app) as client:
        response = client.post("/runs", json={"requirements": "Build a login page"})
        assert response.status_code == 202
        identifier = response.json()["id"]
        assert client.post("/runs/" + identifier + "/stop").status_code == 200
        assert stopped
