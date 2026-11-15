"""Deterministic role outputs used only by the backend tests."""

from devcrew_backend.services.paths import BACKEND_ROOT
from devcrew_backend.services.models import (
    Plan,
    Research,
    Application,
    Review,
    Assessment,
    Criterion,
    ProjectPatch,
    DesignSpec,
    DesignToken,
    ProjectFile,
    VisualReview,
)


class FixtureBackend:
    """Labeled fixed design fixture; real Flow and browser checks, no AI/MCP calls."""

    # Point the fixture at the authored login files and initialize empty model usage.
    def __init__(self):
        from pathlib import Path

        self.base = BACKEND_ROOT / "examples/studio_login"
        self.usage = []

    # Return a deterministic typed result for the role under test.
    def execute(self, role, prompt, images=None):
        if role == "planner":
            return Plan(
                summary="Fixed Forma login rehearsal",
                acceptance_criteria=[
                    "Accessible responsive login interface with working password toggle"
                ],
                specialists=["designer", "standards", "security"],
                implementation_steps=["Build the designed multi-file project"],
            )
        if role == "designer":
            return DesignSpec(
                summary="Fixed Forma art direction",
                recommendations=["Split branded landscape and form composition"],
                sources=[],
                limitations=["Fixed rehearsal, no web research"],
                visual_direction="Warm editorial workspace",
                desktop_layout="46/54 split panel",
                mobile_layout="Stacked compact hero and form",
                typography="System sans, 36px headline",
                color_tokens=[DesignToken(name="forest", value="#284d3b")],
                spacing_and_components=["48px inputs, 8px radii"],
                asset_direction="Original local SVG landscape and logo",
                acceptance_checks=["No clipped controls"],
            )
        if role == "standards":
            return Research(
                summary="Fixed standards fixture",
                recommendations=["Use associated labels and browser email validity"],
                limitations=["No MCP call in rehearsal"],
            )
        if role == "developer":
            files = [
                ProjectFile(
                    path=p.relative_to(self.base).as_posix(),
                    content=p.read_text(encoding="utf-8"),
                )
                for p in self.base.rglob("*")
                if p.is_file()
            ]
            if prompt.startswith(("REVISION_PATCH", "STARTER_PATCH")):
                return ProjectPatch(
                    changed_files=files,
                    addressed_issue_ids=[],
                    notes="Fixed sample; no AI revision performed",
                )
            return Application(
                files=files,
                notes="Fixed offline design fixture; not generated from the prompt",
            )
        if role == "visual":
            return VisualReview(
                summary="Fixed visual-review fixture, not an AI image assessment",
                design_score=8,
                brief_adherence="Fixed design sample",
                issues=[],
            )
        if role in {"reviewer", "security"}:
            return Review(summary="Fixed inspection fixture", issues=[])
        return Assessment(
            decision="release",
            criteria=[
                Criterion(
                    criterion="Accessible responsive login interface with working password toggle",
                    status="met_by_inspection",
                    evidence="Fixture code and browser results",
                )
            ],
            rationale="Fixed fixture assessment",
        )
