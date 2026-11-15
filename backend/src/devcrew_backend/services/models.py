from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectionReasons(Record):
    designer: str | None = None
    standards: str | None = None
    security: str | None = None


class Plan(Record):
    summary: str
    acceptance_criteria: list[str] = Field(min_length=1, max_length=12)
    specialists: list[Literal["designer", "standards", "security"]] = Field(
        default_factory=list
    )
    selection_reasons: SelectionReasons = Field(default_factory=SelectionReasons)
    implementation_steps: list[str] = Field(min_length=1)


class Source(Record):
    title: str
    url: str
    requirement: str


class Research(Record):
    summary: str
    recommendations: list[str]
    sources: list[Source] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DesignToken(Record):
    name: str
    value: str


class DesignSpec(Research):
    visual_direction: str
    desktop_layout: str
    mobile_layout: str
    typography: str
    color_tokens: list[DesignToken]
    spacing_and_components: list[str]
    asset_direction: str
    acceptance_checks: list[str]


class ProjectFile(Record):
    path: str
    content: str


class Application(Record):
    files: list[ProjectFile] = Field(min_length=4)
    notes: str
    feedback_responses: list[str] = Field(default_factory=list)

    # Read index.html from the structured file list.
    @property
    def html(self):
        return next((f.content for f in self.files if f.path == "index.html"), "")


class ProjectPatch(Record):
    changed_files: list[ProjectFile] = Field(min_length=1)
    addressed_issue_ids: list[str]
    notes: str


class BrowserCheck(Record):
    rule_id: str
    passed: bool
    detail: str


class BrowserReport(Record):
    available: bool
    checks: list[BrowserCheck] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Issue(Record):
    rule_id: str = ""
    file: str = ""
    severity: Literal["low", "medium", "high", "critical"]
    evidence: str
    fix: str


class Review(Record):
    summary: str
    issues: list[Issue] = Field(default_factory=list)
    manual_checks: list[str] = Field(default_factory=list)
    executed_tests: list[str] = Field(default_factory=list)


class VisualReview(Review):
    design_score: int = Field(ge=0, le=10)
    brief_adherence: str


class Criterion(Record):
    criterion: str
    status: Literal["met_by_inspection", "failed", "unverified"]
    evidence: str


class Assessment(Record):
    decision: Literal["release", "revise"]
    criteria: list[Criterion] = Field(min_length=1)
    rationale: str
    required_changes: list[str] = Field(default_factory=list)


class Handoff(Record):
    sender: str
    recipient: str
    artifact: str
    revision: int
    message: str
