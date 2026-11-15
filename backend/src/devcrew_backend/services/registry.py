from dataclasses import dataclass
from pathlib import Path
import yaml
from . import models

CONFIG = Path(__file__).resolve().parents[1] / "crews/software_team/config"


@dataclass(frozen=True)
class Capability:
    role: str
    goal: str
    schema: type
    backstory: str
    instructions: str
    tools: tuple[str, ...] = ()


SCHEMAS = {
    "planner": "Plan",
    "designer": "DesignSpec",
    "standards": "Research",
    "developer": "Application",
    "reviewer": "Review",
    "security": "Review",
    "quality": "Assessment",
    "visual": "VisualReview",
}
TOOLS = {
    "planner": (),
    "designer": ("tavily_search",),
    "standards": ("tavily_search",),
    "developer": (),
    "reviewer": (),
    "security": (),
    "quality": (),
    "visual": (),
}
agents = yaml.safe_load((CONFIG / "agents.yaml").read_text(encoding="utf-8"))
tasks = yaml.safe_load((CONFIG / "tasks.yaml").read_text(encoding="utf-8"))
REGISTRY = {
    key: Capability(
        **config,
        schema=getattr(models, SCHEMAS[key]),
        instructions=tasks[key + "_task"]["description"].replace(
            "\n{task_context}", ""
        ),
        tools=TOOLS[key]
    )
    for key, config in agents.items()
}
