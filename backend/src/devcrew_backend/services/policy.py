"""Automatic execution choices; no user-tuned quotas or run deadlines."""
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelPolicy:
    mode: str
    native_reasoning: bool | None
    guidance: str

def model_policy(model,role):
    name=model.lower().split("/")[-1]
    # Conservative documented families, not a claim that every provider exposes metadata.
    native=bool(re.match(r"^(?:o[134](?:-|$)|gpt-5(?:[.\-]|$))",name))
    ordinary=name.startswith(("gpt-4o","gpt-4.1","gpt-3.5"))
    if native:
        return ModelPolicy("native",True,"Use the model's native reasoning. Return only the requested result, brief decisions and evidence; do not add a separate planning conversation.")
    if ordinary:
        focus={"planner":"Identify the exact deliverable and minimal acceptance criteria before selecting specialists.",
               "developer":"Check required behavior, edge cases and safe DOM handling before returning complete code.",
               "reviewer":"Trace each acceptance criterion through the code and distinguish defects from preferences.",
               "security":"Check data flow from input to sinks and substantiate each finding with code evidence.",
               "quality":"Compare criteria and reports; resolve conflicts using evidence."}.get(role,"Separate applicable evidence from general advice.")
        return ModelPolicy("in_task_self_check",False,focus+" Do this within the existing task; return concise conclusions, not a separate reasoning transcript.")
    return ModelPolicy("provider_default",None,"Preserve the provider's reasoning defaults. Check the requested deliverable before answering. No additional framework reasoning loop is added; native capability is unknown for this model.")
