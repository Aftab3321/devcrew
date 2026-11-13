# Implemented execution architecture

Generated from Flow decorators, task calls, capability registry and MCP client endpoint. Dotted edges describe capabilities/contained work; solid edges are Flow dependencies. review_cycles contains an actual asyncio.gather and revision loop stopped on no progress. Design, standards and security are required UI stages; login projects use a transparent tested design foundation. This is the static architecture, not evidence that a tool ran. See each session's events.jsonl for actual execution.

```mermaid
flowchart TD
frontend["Streamlit HTTP client"] --> api["Local backend API"]
api --> launch_job["Launch isolated worker"]
query["User query"] --> frontend
launch_job --> worker["Worker subprocess"]
worker --> validate_request
validate_request["validate_request"]
plan_team["plan_team"]
design_research["design_research"]
standards_research["standards_research"]
develop["develop"]
review_cycles["review_cycles"]
release_route["release_route"]
release["release"]
save_unresolved["save_unresolved"]
validate_request --> plan_team
plan_team --> design_research
plan_team --> standards_research
design_research --> develop
standards_research --> develop
develop --> review_cycles
review_cycles --> release_route
release_candidate --> release
needs_attention --> save_unresolved
release_route --> needs_attention
release_route --> release_candidate
plan_team -. task .-> agent_planner["Engineering Manager: Plan"]
research_task -. task .-> agent_designer["UI UX Designer: DesignSpec"]
research_task -. task .-> agent_standards["Standards Researcher: Research"]
develop -. task .-> agent_developer["Frontend Developer: Application"]
review_cycles -. task .-> agent_developer["Frontend Developer: Application"]
review_cycles -. task .-> agent_reviewer["Code Reviewer: Review"]
review_cycles -. task .-> agent_security["Security Auditor: Review"]
review_cycles -. task .-> agent_quality["Quality Assessor: Assessment"]
review_cycles -. task .-> agent_visual["Visual Design Reviewer: VisualReview"]
agent_planner -. mandatory UI specialists .-> research_task
develop -. tested login foundation .-> starter["Local design system and SVG assets"]
review_cycles -. renders project .-> render["Desktop/mobile browser checks"]
render -. actual screenshots .-> agent_visual
review_cycles -. parallel screenshot review .-> agent_visual
agent_developer -. targeted changed files .-> patch["ProjectPatch: preserve unchanged files"]
worker -. manually cancellable .-> stop["Stop control: terminates worker"]
model -. observes each HTTP request .-> monitor["Request telemetry + repeated-action recovery"]
monitor -. logs status and usage .-> activity["Live event timeline"]
design_research -. calls .-> research_task
standards_research -. calls .-> research_task
agent_planner -. configured model .-> model["LLM: MODEL environment setting"]
agent_planner["Engineering Manager: Plan"]
agent_designer -. configured model .-> model["LLM: MODEL environment setting"]
agent_designer["UI UX Designer: DesignSpec"]
agent_designer -. capability .-> tool_tavily_search["tavily_search"]
agent_standards -. configured model .-> model["LLM: MODEL environment setting"]
agent_standards["Standards Researcher: Research"]
agent_standards -. capability .-> tool_tavily_search["tavily_search"]
agent_developer -. configured model .-> model["LLM: MODEL environment setting"]
agent_developer["Frontend Developer: Application"]
agent_reviewer -. configured model .-> model["LLM: MODEL environment setting"]
agent_reviewer["Code Reviewer: Review"]
agent_security -. configured model .-> model["LLM: MODEL environment setting"]
agent_security["Security Auditor: Review"]
agent_quality -. configured model .-> model["LLM: MODEL environment setting"]
agent_quality["Quality Assessor: Assessment"]
agent_visual -. configured model .-> model["LLM: MODEL environment setting"]
agent_visual["Visual Design Reviewer: VisualReview"]
tool_tavily_search -. when enabled .-> mcp_0["MCP: https://mcp.tavily.com/mcp/"]
worker -. shared project state .-> memory["Session blackboard: memory.json"]
review_cycles -. asyncio.gather: same code version .-> agent_reviewer
review_cycles -. required parallel audit .-> agent_security
review_cycles -. after both reports .-> agent_quality
review_cycles -. feedback revision until completion or no progress .-> agent_developer
review_cycles -. project scan .-> scan["File linkage and static checks"]
release -. writes .-> artifacts["Per-session artifacts, handoffs and events"]
save_unresolved -. saves draft .-> artifacts
agent_developer -. output validation .-> schema["Pydantic project + linkage validation"]
```
