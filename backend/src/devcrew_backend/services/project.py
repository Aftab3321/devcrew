"""Portable multi-file projects, safe paths, linkage validation and targeted patches."""

import hashlib
import json
import re
import zipfile
import io
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, unquote
from html.parser import HTMLParser
from .models import Application, ProjectPatch, Issue

REQUIRED = {"index.html", "assets/css/styles.css", "assets/js/app.js", "README.md"}


# Normalize a generated path and reject files outside the allowed project structure.
def safe_path(name):
    p = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or ":" in name
        or p.is_absolute()
        or any(x in {"..", "."} for x in name.split("/"))
        or p.suffix.lower() not in {".html", ".css", ".js", ".svg", ".md", ".json"}
    ):
        raise ValueError("Unsafe or unsupported project path: " + name)
    return name


class References(HTMLParser):
    # Prepare the parser to collect linked assets and inline code indicators.
    def __init__(self):
        super().__init__()
        self.refs = []
        self.inline = False

    # Inspect an HTML tag for resource references and inline code.
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style" or (tag == "script" and not a.get("src")):
            self.inline = True
        for key in ["href", "src"]:
            if a.get(key):
                self.refs.append((tag, key, a[key]))


# Check the generated files for broken links and unsafe browser behavior.
def project_issues(app):
    files = {f.path: f.content for f in app.files}
    issues = []

    # Collect a finding with a stable rule ID, its evidence and a suggested fix.
    def add(rule, file, evidence, fix, severity="high"):
        issues.append(
            Issue(
                rule_id=rule, file=file, severity=severity, evidence=evidence, fix=fix
            )
        )

    for name in REQUIRED - files.keys():
        add(
            "structure.missing." + name, name, "Missing required file", "Create " + name
        )
    for f in app.files:
        safe_path(f.path)
        if f.path.endswith(".html"):
            parser = References()
            parser.feed(f.content)
            if parser.inline:
                add(
                    "structure.inline_code",
                    f.path,
                    "Inline style or script found",
                    "Move CSS/JS into linked external local files",
                )
            if f.path == "index.html":
                for ref in ["assets/css/styles.css", "assets/js/app.js"]:
                    if ref not in [r[2] for r in parser.refs]:
                        add(
                            "structure.unlinked." + ref,
                            f.path,
                            "Missing link to " + ref,
                            "Link " + ref + " from index.html",
                        )
            for tag, key, url in parser.refs:
                parsed = urlsplit(url)
                if parsed.scheme or parsed.netloc:
                    if (
                        tag == "img"
                        and parsed.scheme == "https"
                        and parsed.hostname == "images.unsplash.com"
                    ):
                        continue
                    if parsed.scheme in {"mailto", "tel"}:
                        continue
                    add(
                        "resources.external",
                        f.path,
                        url,
                        "Use local project assets; remote photos may use images.unsplash.com",
                    )
                elif parsed.path:
                    from posixpath import normpath, join, dirname

                    target = normpath(join(dirname(f.path), unquote(parsed.path)))
                    if target not in files:
                        add(
                            "resources.broken." + target,
                            f.path,
                            url,
                            "Include and correctly link " + target,
                        )
        if f.path.endswith((".js", ".html", ".svg")):
            for pattern, rule, fix in [
                (r"\beval\s*\(", "security.eval", "Remove dynamic code execution"),
                (
                    r"\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(",
                    "security.network",
                    "Remove backend/network calls from the frontend demo",
                ),
                (
                    r"(?:localStorage|sessionStorage)\.setItem.{0,100}(?:password|credential)",
                    "security.password_storage",
                    "Never persist passwords",
                ),
            ]:
                hit = re.search(pattern, f.content, re.I | re.S)
                if hit:
                    add(rule, f.path, hit.group(), fix)
        if f.path.endswith(".svg") and re.search(
            r"<script|foreignObject|onload=", f.content, re.I
        ):
            add(
                "security.active_svg",
                f.path,
                "Active SVG content",
                "Use a static original SVG without scripts or embedded documents",
            )
    if len(files) != len(app.files):
        raise ValueError("Duplicate project file paths")
    return issues


# Enforce the expected file structure before writing the deliverable.
def validate_project(app):
    for f in app.files:
        safe_path(f.path)
    missing = REQUIRED - {f.path for f in app.files}
    if missing:
        raise ValueError("Project missing files: " + ", ".join(sorted(missing)))
    if "<html" not in app.html.lower() or "</html>" not in app.html.lower():
        raise ValueError("index.html must be a complete HTML document")


# Write validated generated files inside a designated project directory.
def materialize(app, folder):
    validate_project(app)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    for f in app.files:
        target = folder / safe_path(f.path)
        if not target.resolve().is_relative_to(folder):
            raise ValueError("Project path escapes output directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.content, encoding="utf-8")


# Replace only the files supplied in a developer patch.
def merge_patch(app, patch):
    files = {f.path: f for f in app.files}
    for f in patch.changed_files:
        files[safe_path(f.path)] = f
    result = Application(
        files=list(files.values()),
        notes=patch.notes,
        feedback_responses=patch.addressed_issue_ids,
    )
    validate_project(result)
    return result


# Hash the sorted file contents to detect unchanged revisions.
def digest(app):
    return hashlib.sha256(
        json.dumps(sorted((f.path, f.content) for f in app.files)).encode()
    ).hexdigest()


# Package a project directory for download.
def project_zip(folder):
    folder = Path(folder)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(folder).as_posix())
    return buffer.getvalue()
