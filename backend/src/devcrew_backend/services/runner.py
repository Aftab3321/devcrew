"""Process-isolated UI jobs: real stop, without run deadlines."""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from .paths import BACKEND_ROOT
from .storage import Session

ROOT = BACKEND_ROOT


# Read saved activity records in the order they were written.
def events(path):
    try:
        lines = (Path(path) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except ValueError:
            pass  # A concurrent append may still be incomplete.
    return result


class Job:
    # Start a session worker and capture its console output.
    def __init__(self, path, command):
        self.path = Path(path)
        self.started = time.monotonic()
        self.lock = threading.RLock()
        self.reason = None
        self.finished = None
        self.log = (self.path / "worker.log").open("w", encoding="utf-8")
        options = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if sys.platform == "win32"
            else {}
        )
        self.process = subprocess.Popen(
            command, cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT, **options
        )
        self.pid = self.process.pid
        threading.Thread(target=self._watch, daemon=True).start()

    # Terminate the worker and persist the reason for cancellation.
    def stop(self, reason="Stopped by user"):
        with self.lock:
            if self.process.poll() is not None:
                return
            self.reason = reason
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            Session.attach(self.path).event("run_stopped", message=reason)
            Session.attach(self.path).write(
                "terminal.json", {"status": "stopped", "message": reason}
            )

    # Wait for the process to exit and close its log handle.
    def _watch(self):
        self.process.wait()
        self.finished = time.monotonic()
        self.log.close()

    # Check whether the child process is still active.
    @property
    def running(self):
        return self.process.poll() is None

    # Combine process state with saved events, result and terminal status.
    def _snapshot(self):
        records = events(self.path)
        result = None
        terminal = None
        for filename in ["result.json", "terminal.json"]:
            try:
                value = json.loads((self.path / filename).read_text(encoding="utf-8"))
                if filename == "result.json":
                    result = value
                else:
                    terminal = value
            except (OSError, ValueError):
                pass
        if not self.running and terminal is None and result is None:
            terminal = {
                "status": "failed",
                "message": "Worker exited unexpectedly (code "
                + str(self.process.returncode)
                + "). Check saved diagnostics.",
            }
        return {
            "running": self.running,
            "elapsed": (self.finished or time.monotonic()) - self.started,
            "events": records,
            "result": result,
            "terminal": terminal,
        }

    # Serialize reads with cancellation to return a consistent snapshot.
    def snapshot(self):
        with self.lock:
            return self._snapshot()


# Validate the brief, save the live job and start its isolated worker.
def launch(requirements):
    from .guardrails import check_request

    check_request(requirements)
    session = Session(ROOT / "outputs", requirements, "live")
    session.write("job.json", {"requirements": requirements})
    return Job(
        session.path,
        [
            sys.executable,
            "-X",
            "utf8",
            "-u",
            "-m",
            "devcrew_backend.services.worker",
            str(session.path),
        ],
    )
