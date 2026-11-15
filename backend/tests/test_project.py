import io
import zipfile
import pytest
from fixture_backend import FixtureBackend
from devcrew_backend.services.models import ProjectPatch, ProjectFile
from devcrew_backend.services.project import (
    validate_project,
    project_issues,
    safe_path,
    merge_patch,
    materialize,
    project_zip,
)


# Verify that real linkage and portable zip.
def test_real_linkage_and_portable_zip(tmp_path):
    app = FixtureBackend().execute("developer", "")
    validate_project(app)
    assert not project_issues(app)
    materialize(app, tmp_path / "project")
    with zipfile.ZipFile(io.BytesIO(project_zip(tmp_path / "project"))) as archive:
        assert {
            "index.html",
            "assets/css/styles.css",
            "assets/js/app.js",
            "assets/images/brand.svg",
            "README.md",
        } <= set(archive.namelist())
        assert b"assets/css/styles.css" in archive.read("index.html")


# Verify that paths cannot escape project.
@pytest.mark.parametrize(
    "path",
    [
        "../secret.js",
        "/absolute.css",
        "C:/secret.html",
        "assets/../../bad.js",
        "evil.exe",
        "bad\\escape.js",
    ],
)
def test_paths_cannot_escape_project(path):
    with pytest.raises(ValueError):
        safe_path(path)


# Verify that targeted patch preserves unrelated files.
def test_targeted_patch_preserves_unrelated_files():
    app = FixtureBackend().execute("developer", "")
    original = {f.path: f.content for f in app.files}
    patch = ProjectPatch(
        changed_files=[
            ProjectFile(
                path="assets/css/styles.css",
                content=original["assets/css/styles.css"] + "\n/* patch */",
            )
        ],
        addressed_issue_ids=["layout"],
        notes="CSS fix only",
    )
    changed = merge_patch(app, patch)
    after = {f.path: f.content for f in changed.files}
    assert after["assets/js/app.js"] == original["assets/js/app.js"]
    assert after["index.html"] == original["index.html"]
    assert after["assets/css/styles.css"] != original["assets/css/styles.css"]


# Verify that broken link is reported.
def test_broken_link_is_reported():
    app = FixtureBackend().execute("developer", "")
    app.files[0].content = app.files[0].content
    index = next(f for f in app.files if f.path == "index.html")
    index.content = index.content.replace(
        "assets/css/styles.css", "assets/css/missing.css"
    )
    assert any("broken" in x.rule_id for x in project_issues(app))


# Verify that tested design foundation cannot be replaced by generic card.
def test_tested_design_foundation_cannot_be_replaced_by_generic_card():
    from devcrew_backend.services.starter import login_starter, integrate_login_patch

    design = FixtureBackend().execute("designer", "")
    app = login_starter(design)
    patch = ProjectPatch(
        changed_files=[
            ProjectFile(
                path="index.html",
                content="<html><body><form>Generic card</form></body></html>",
            ),
            ProjectFile(path="assets/css/styles.css", content="body {background:gray}"),
        ],
        addressed_issue_ids=[],
        notes="Bad blanket rewrite",
    )
    result, rejected = integrate_login_patch(app, patch)
    assert 'class="story"' in result.html
    assert rejected
    assert not project_issues(result)


# Verify that invalid unicode control patch cannot corrupt clean text.
def test_invalid_unicode_control_patch_cannot_corrupt_clean_text():
    from devcrew_backend.services.starter import login_starter, integrate_login_patch

    app = login_starter(FixtureBackend().execute("designer", ""))
    bad = ProjectPatch(
        changed_files=[
            ProjectFile(
                path="index.html",
                content=app.html.replace("Welcome back.", "Welcome\u001e"),
            )
        ],
        addressed_issue_ids=[],
        notes="corrupted encoding",
    )
    result, rejected = integrate_login_patch(app, bad)
    assert result.html == app.html
    assert any("control characters" in item for item in rejected)
