import re
from html.parser import HTMLParser
from .models import Issue

class RequestBlocked(ValueError):
    pass

def check_request(text):
    if not 5 <= len(text.strip()) <= 4000:
        raise RequestBlocked("Enter between 5 and 4,000 characters.")
    # Demonstration policy, not a comprehensive intent classifier.
    rules = [r"\b(?:steal|harvest|exfiltrate)\b.{0,60}\b(?:passwords?|credentials?|cookies?|tokens?)\b",
             r"\b(?:ransomware|keylogger|credential[- ]stealer)\b",
             r"\b(?:ignore|override)\b.{0,40}\b(?:system|guardrails?|safety)\b"]
    if any(re.search(rule, text, re.I | re.S) for rule in rules):
        raise RequestBlocked("This request matches the demo's blocked-request policy.")

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.issues = []
    def flag(self, evidence, fix):
        self.issues.append(Issue(severity="high", evidence=evidence, fix=fix))
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"iframe", "object", "embed", "base"}:
            self.flag("Disallowed element: " + tag, "Remove embedded/external content.")
        for key, value in attrs.items():
            value = (value or "").strip().lower()
            if key in {"src", "href", "action", "formaction"} and (value.startswith(("http:", "https:", "//", "javascript:", "data:"))):
                self.flag("External or active URL in " + key, "Use self-contained resources and local behavior.")

def scan_html(html):
    parser = Inspector()
    parser.feed(html)
    for pattern, fix in [(r"\beval\s*\(", "Remove eval."),
                         (r"\bnew\s+Function\s*\(", "Remove dynamic code construction."),
                         (r"\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(", "Remove network access."),
                         (r"\.innerHTML\s*=", "Use textContent or safe DOM construction for user data."),
                         (r"@import|url\s*\(", "Remove CSS resource loading.")]:
        if re.search(pattern, html, re.I):
            parser.flag("Static pattern: " + pattern, fix)
    return parser.issues

def validate_html(html):
    if "<html" not in html.lower() or "</html>" not in html.lower():
        raise ValueError("Expected a complete HTML document")

def application_guardrail(output):
    try:
        from .models import Application
        app = output.pydantic or Application.model_validate_json(output.raw)
        from .project import validate_project
        validate_project(app)
        from crewai.tasks.output_format import OutputFormat
        output.pydantic = app
        output.raw = app.model_dump_json()
        output.output_format = OutputFormat.PYDANTIC
        return True, output
    except (ValueError, AttributeError):
        return False, "Return a valid Application with a complete HTML document."
