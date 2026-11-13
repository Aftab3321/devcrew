"""Extract Flow decorator edges and task/tool bindings from the implementation."""
import ast
import hashlib
import inspect
import json
import shutil
import re
from pathlib import Path
from .registry import REGISTRY

ROOT = Path(__file__).resolve().parent

def generate_diagrams(folder):
    from ..flows.development_flow import DevelopmentFlow
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    # Native CrewAI visualization: no kickoff, model calls or MCP connections.
    flow = DevelopmentFlow(None, None)
    native_path = Path(flow.plot(filename="crewai_flow.html", show=False))
    native_html = native_path.read_text(encoding="utf-8")
    for asset in native_path.parent.iterdir():
        if asset.suffix == ".js":
            script = asset.read_text(encoding="utf-8").replace("</script", "<\\/script")
            native_html = re.sub(r'<script\s+src="' + re.escape(asset.name) + r'"[^>]*></script>', lambda _: "<script>" + script + "</script>", native_html)
        elif asset.suffix == ".css":
            css = asset.read_text(encoding="utf-8")
            native_html = re.sub(r'<link[^>]*href="' + re.escape(asset.name) + r'"[^>]*>', lambda _: "<style>" + css + "</style>", native_html)
    (folder / "crewai_flow.html").write_text(native_html, encoding="utf-8")
    tree = ast.parse(inspect.getsource(DevelopmentFlow))
    methods = {n.name:n for n in tree.body[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    lines = ["flowchart TD", 'frontend["Streamlit HTTP client"] --> api["Local backend API"]', 'api --> launch_job["Launch isolated worker"]', 'query["User query"] --> frontend', 'launch_job --> worker["Worker subprocess"]', 'worker --> validate_request']
    edges = []
    starts = []
    def dependencies(expr):
        if isinstance(expr, ast.Name):
            return [expr.id]
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return [expr.value]
        if isinstance(expr, ast.Call):
            return [x for a in expr.args for x in dependencies(a)]
        return []
    for name, method in methods.items():
        if not method.decorator_list:
            continue
        lines.append(f'{name}["{name}"]')
        for dec in method.decorator_list:
            if isinstance(dec, ast.Call):
                for arg in dec.args:
                    for dep in dependencies(arg):
                        edges.append((dep, name))
    for name, method in methods.items():
        if any(isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "router" for dec in method.decorator_list):
            for node in ast.walk(method):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    edges.append((name, node.value.value))
    for a,b in edges:
        lines.append(f'{a} --> {b}')
    # Attach actual agent calls discovered in methods (including helper methods).
    for name, method in methods.items():
        for node in ast.walk(method):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "task" and node.args:
                arg = node.args[0]
                roles = [arg.value] if isinstance(arg, ast.Constant) else []
                if isinstance(arg, ast.Name) and arg.id == "role":
                    # role loops / research helper use the literal registry keys present in their source.
                    source = ast.unparse(method)
                    if name == "research_task":
                        roles = [call.args[0].value for m in methods.values() for call in ast.walk(m)
                                 if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                                 and call.func.attr == "research_task" and call.args and isinstance(call.args[0], ast.Constant)]
                    else:
                        roles = [r for r in REGISTRY if repr(r) in source]
                for role in roles:
                    if role in REGISTRY:
                        lines.append(f'{name} -. task .-> agent_{role}["{REGISTRY[role].role}"]')
    backend_source = (ROOT / "backend.py").read_text(encoding="utf-8")
    backend_tree = ast.parse(backend_source)
    # Manager selects fixed registry entries; there is no runtime delegation/agent creation.
    assert "Process.hierarchical" not in backend_source
    assert "RequestMonitor" in backend_source
    lines += ['agent_planner -. mandatory UI specialists .-> research_task',
              'develop -. tested login foundation .-> starter["Local design system and SVG assets"]',
              'review_cycles -. renders project .-> render["Desktop/mobile browser checks"]',
              'render -. actual screenshots .-> agent_visual',
              'review_cycles -. parallel screenshot review .-> agent_visual',
              'agent_developer -. targeted changed files .-> patch["ProjectPatch: preserve unchanged files"]',
              'worker -. manually cancellable .-> stop["Stop control: terminates worker"]',
              'model -. observes each HTTP request .-> monitor["Request telemetry + repeated-action recovery"]',
              'monitor -. logs status and usage .-> activity["Live event timeline"]',
              'design_research -. calls .-> research_task',
              'standards_research -. calls .-> research_task']
    for role, cap in REGISTRY.items():
        lines.append(f'agent_{role} -. configured model .-> model["LLM: MODEL environment setting"]')
        lines.append(f'agent_{role}["{cap.role}"]')
        for tool in cap.tools:
            lines.append(f'agent_{role} -. capability .-> tool_{tool}["{tool}"]')
    # Extract MCP endpoint literal directly from its client call.
    urls = [n.args[0].value for n in ast.walk(backend_tree) if isinstance(n,ast.Call)
            and isinstance(n.func,ast.Name) and n.func.id == "streamable_http_client"
            and n.args and isinstance(n.args[0],ast.Constant)]
    for i,url in enumerate(urls):
        lines.append(f'tool_tavily_search -. when enabled .-> mcp_{i}["MCP: {url}"]')
    lines += ['worker -. shared project state .-> memory["Session blackboard: memory.json"]',
              'review_cycles -. asyncio.gather: same code version .-> agent_reviewer',
              'review_cycles -. required parallel audit .-> agent_security',
              'review_cycles -. after both reports .-> agent_quality',
              'review_cycles -. feedback revision until completion or no progress .-> agent_developer',
              'review_cycles -. project scan .-> scan["File linkage and static checks"]',
              'release -. writes .-> artifacts["Per-session artifacts, handoffs and events"]',
              'save_unresolved -. saves draft .-> artifacts',
              'agent_developer -. output validation .-> schema["Pydantic project + linkage validation"]']
    # Remove duplicates while preserving order.
    diagram = "\n".join(dict.fromkeys(lines)) + "\n"
    for role, cap in REGISTRY.items():
        diagram = diagram.replace(f'agent_{role}["{cap.role}"]', f'agent_{role}["{cap.role}: {cap.schema.__name__}"]')
    (folder / "execution.mmd").write_text(diagram,encoding="utf-8")
    source_root = ROOT.parent
    sources = list(source_root.rglob("*.py")) + list(source_root.rglob("*.yaml"))
    hashes = {p.relative_to(source_root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (folder / "diagram_sources.json").write_text(json.dumps(hashes,indent=2),encoding="utf-8")
    (folder / "execution.md").write_text("# Implemented execution architecture\n\nGenerated from Flow decorators, task calls, capability registry and MCP client endpoint. Dotted edges describe capabilities/contained work; solid edges are Flow dependencies. review_cycles contains an actual asyncio.gather and revision loop stopped on no progress. Design, standards and security are required UI stages; login projects use a transparent tested design foundation. This is the static architecture, not evidence that a tool ran. See each session's events.jsonl for actual execution.\n\n```mermaid\n" + diagram + "```\n",encoding="utf-8")
    from .render_diagram import render
    render(folder)
    return diagram

if __name__ == "__main__":
    generate_diagrams(ROOT.parent / "diagrams")
