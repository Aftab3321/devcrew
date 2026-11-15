"""HTTP-only client; backend packages and files are never imported."""

import os
from urllib.parse import quote
import httpx


class BackendClient:
    # Read the backend URL from the frontend environment.
    def __init__(self):
        self.url = os.getenv("DEVCREW_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

    # Send an HTTP request and surface unsuccessful responses.
    def request(self, method, path, **kwargs):
        response = httpx.request(method, self.url + path, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    # Check that the backend service is reachable.
    def health(self):
        return self.request("GET", "/health").json()

    # Submit a brief and return the new live session ID.
    def launch(self, requirements):
        return self.request(
            "POST", "/runs", json={"requirements": requirements}
        ).json()["id"]

    # Fetch current progress and saved reports for a session.
    def snapshot(self, identifier):
        return self.request("GET", "/runs/" + quote(identifier, safe="")).json()

    # List sessions available from the backend.
    def history(self):
        return self.request("GET", "/runs").json()

    # Ask the backend to stop this session worker.
    def stop(self, identifier):
        return self.request(
            "POST", "/runs/" + quote(identifier, safe="") + "/stop"
        ).json()

    # Fetch the requested project or session archive.
    def download(self, identifier, kind):
        return self.request(
            "GET", "/runs/" + quote(identifier, safe="") + "/download/" + kind
        ).content

    # Fetch a saved artifact such as a browser screenshot.
    def artifact(self, identifier, name):
        return self.request(
            "GET",
            "/runs/" + quote(identifier, safe="") + "/files/" + quote(name, safe="/"),
        ).content
