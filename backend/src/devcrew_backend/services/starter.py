"""A transparent tested design foundation, not claimed to be fresh model output."""

import re
from pathlib import Path
from .paths import BACKEND_ROOT
from .models import Application, ProjectFile, ProjectPatch
from .project import merge_patch, project_issues

BASE = BACKEND_ROOT / "examples/studio_login"


# Detect a brief that should use the login foundation.
def is_login(brief):
    return bool(re.search(r"login|log in|sign[- ]?in|password", brief, re.I))


# Assemble the Forma starter files and apply safe design tokens.
def login_starter(design):
    files = []
    for p in BASE.rglob("*"):
        if not p.is_file():
            continue
        name = p.relative_to(BASE).as_posix()
        content = p.read_text(encoding="utf-8")
        if name == "assets/css/styles.css":
            name = "assets/css/layout.css"
            content = content.replace("#284d3b", "var(--accent,#284d3b)").replace(
                "#fffefa", "var(--surface,#fffefa)"
            )
        if name == "index.html":
            content = content.replace(
                '<link rel="stylesheet" href="assets/css/styles.css">',
                '<link rel="stylesheet" href="assets/css/layout.css"><link rel="stylesheet" href="assets/css/styles.css">',
            )
        files.append(ProjectFile(path=name, content=content))
    theme = "/* Agent-customizable theme; reviewed layout remains in layout.css. */\n"
    # Palette values are real design output; reject CSS injection/URLs.
    for token in design.color_tokens:
        if re.fullmatch(r"#[0-9a-fA-F]{3,8}", token.value):
            key = re.sub(r"[^a-z0-9-]", "-", token.name.lower())
            theme += ":root { --" + key + ": " + token.value + "; }\n"
            if any(x in key for x in ["forest", "primary", "accent"]):
                theme += ":root { --accent: " + token.value + "; }\n"
            if any(x in key for x in ["cream", "surface"]):
                theme += ":root { --surface: " + token.value + "; }\n"
    files.append(ProjectFile(path="assets/css/styles.css", content=theme))
    return Application(
        files=files,
        notes="Built from the tested Forma login design foundation, with agent-authored planning, design specification, adaptations and review. Original local SVG assets included.",
    )


# Merge compatible changes while preserving protected layout and asset contracts.
def integrate_login_patch(app, patch):
    """Preserve proven layout/asset contracts; accept compatible targeted adaptations."""
    kept = []
    rejected = []
    files = {f.path: f.content for f in app.files}
    html = files["index.html"]
    for f in patch.changed_files:
        if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in f.content):
            rejected.append(
                f.path
                + ": invalid control characters; retained the clean existing file"
            )
            continue
        if f.path == "assets/css/layout.css":
            rejected.append(f.path + ": reviewed layout is retained")
            continue
        if f.path == "assets/css/styles.css":
            # Theme changes can refine colors/type/spacing through custom properties.
            properties = re.findall(r"--[a-zA-Z0-9-]+\s*:\s*[^;{}]+;", f.content)
            safe = [
                p
                for p in properties
                if not re.search(r"url|expression|javascript|@", p, re.I)
            ]
            if safe:
                kept.append(
                    ProjectFile(path=f.path, content=":root {" + "\n".join(safe) + "}")
                )
            else:
                rejected.append(
                    f.path + ": unscoped rewrite would discard the design system"
                )
            continue
        if f.path == "index.html":
            required = [
                'class="shell"',
                'class="story"',
                'class="signin"',
                "assets/css/layout.css",
                'data-testid="password-toggle"',
            ]
            if not all(x in f.content for x in required):
                rejected.append(
                    f.path + ": missing established layout/interaction hooks"
                )
                continue
            html = f.content
        kept.append(f)
    html = next((f.content for f in kept if f.path == "index.html"), html)
    ids = set(re.findall(r'id=["\']([^"\']+)', html))
    safe_files = []
    for f in kept:
        if f.path.endswith(".js"):
            references = re.findall(
                r"(?:querySelector\(['\"]#|getElementById\(['\"])([A-Za-z0-9_-]+)",
                f.content,
            )
            if any(x not in ids for x in references):
                rejected.append(f.path + ": references missing HTML controls")
                continue
        safe_files.append(f)
    candidate = merge_patch(
        app,
        ProjectPatch(
            changed_files=safe_files
            or [ProjectFile(path="README.md", content=files["README.md"])],
            addressed_issue_ids=patch.addressed_issue_ids,
            notes=app.notes + " " + patch.notes,
        ),
    )
    # Reject new broken links, rather than replacing a sound starter with missing assets.
    if any(i.rule_id.startswith("resources.broken") for i in project_issues(candidate)):
        rejected.append(
            "Patch introduced a missing linked asset; preserved the validated base project"
        )
        return app, rejected
    return candidate, rejected
