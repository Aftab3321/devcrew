# DevCrew backend

## 1. Create an environment

Use Python 3.13 to match this repository's pin. Run the commands from DevCrew's root. Pick one environment method. Examples use PowerShell.

**Python venv, recommended with the existing lockfile**

~~~powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install uv
uv sync --locked
~~~

On macOS or Linux, use python3.13 -m venv .venv and source .venv/bin/activate. If uv is already installed, skip the pip installation. uv sync also creates and manages .venv automatically when it is absent.

**Conda**

~~~powershell
conda create -n devcrew-backend python=3.13 pip
conda activate devcrew-backend
cd backend
python -m pip install -e .
~~~

The Conda route installs into the active environment using pyproject.toml. For the CrewAI CLI launch below, also install uv in that environment with python -m pip install uv. CrewAI's run command can invoke uv internally to run the configured entry point. Set UV_PROJECT_ENVIRONMENT to the absolute Conda environment path to keep that invocation in your chosen environment:

~~~powershell
$env:UV_PROJECT_ENVIRONMENT = $env:CONDA_PREFIX
uv sync --locked
~~~

**What installs CrewAI?** The backend declares crewai==1.15.39 in pyproject.toml. The project install includes the CrewAI CLI and the other application dependencies. The standalone CLI installation in the class lab below is useful for generating a separate starter project.

## 2. Configure and start

~~~powershell
Copy-Item .env.example .env
# Open .env and replace the OpenAI key placeholder.
uv run crewai run
~~~

Copy the example only on first setup. Keep the existing .env if you already have credentials. Use OPENAI_API_KEY for the model, MODEL to select the OpenAI model, TAVILY_API_KEY optionally for research, and DEVCREW_BACKEND_PORT to change port 8000. MAX_TOKENS controls the provider's per-response token allowance. Keep .env out of version control. Start the frontend in another terminal. Check the service with:

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/health
~~~

Chrome or Edge supports the rendered checks. Set CHROME_PATH to the executable if detection fails. The service binds to 127.0.0.1.

## 3. Read the code in execution order

| File | How it participates |
| --- | --- |
| pyproject.toml | Declares pinned CrewAI, dependencies and the Flow CLI script targets. |
| uv.lock / .python-version | Record dependency resolution and the Python interpreter pin. |
| .env.example / .gitignore | Show configuration names and exclude local secrets and generated files as configured. |
| src/devcrew_backend/main.py | kickoff starts Uvicorn. plot creates the native graph. run_with_trigger reads a JSON brief for direct execution. |
| services/api.py | Starlette validates a brief, starts a run, returns snapshots, exposes history, stops jobs and serves downloads. |
| services/runner.py | Creates the run directory and starts an isolated Python worker. Tracks its status and can terminate an active run. |
| services/worker.py | Reads the saved brief, invokes run_team and records the result or a safe error message. |
| services/facade.py | Loads configuration, checks the brief and API key, then constructs and starts DevelopmentFlow. |
| flows/development_flow.py | Coordinates the stages using typed state and CrewAI Flow decorators. |
| crews/software_team/software_team.py | Uses CrewBase and agent/task/crew decorators to assemble one single-agent crew for each selected text stage. |
| crews/software_team/config/agents.yaml | Defines the role, goal and backstory of each predefined role. |
| crews/software_team/config/tasks.yaml | Defines the stage prompts. Python assigns the runtime output schema and sets expected_output. |
| services/registry.py | Connects YAML role keys to schemas and optional tool names. |
| services/backend.py | Calls the configured model, exposes Tavily through MCP when configured, and makes the visual review image request directly. |
| services/models.py | Pydantic classes define the plan, design, research, code files, patches, findings and assessment. |
| services/policy.py | Selects model-aware reasoning instructions. |
| services/limits.py | Records provider status and usage and detects repeated tool actions. |
| services/errors.py | Converts provider failures into displayable diagnostics. |
| services/guardrails.py | Checks briefs and validates structured developer output. |
| services/project.py | Checks project file paths and linkage, merges patches, writes files and builds the ZIP. |
| services/starter.py | Adapts the Forma login foundation and preserves protected layout and hooks. |
| services/browser.py | Renders the generated UI locally, captures screenshots and evaluates browser checks. |
| services/storage.py | Writes structured artifacts, events and shared session data. |
| services/paths.py | Locates the backend project root. |
| services/ui.py | Event formatting helpers kept for backend regression tests. |
| tools/ and __init__.py | Scaffold package markers. The actual Tavily tool is registered in services/backend.py. |
| examples/studio_login/ | The HTML, CSS, JavaScript, SVG assets and notes used by live login runs. |
| knowledge/ui_standards.json | Maintained references loaded explicitly by backend.py for standards work. |
| outputs/ | One directory per run, created at runtime. Contains status, reports, revisions, screenshots and generated files. |
| tests/ | Regression checks for API, orchestration, provider handling, schemas and project output. fixture_backend.py supplies fixed test results. |

Paths beginning with services/, crews/, flows/ or tools/ in the table are relative to src/devcrew_backend/.

## 4. Follow one run

1. POST /runs receives a brief. GET /runs/{id} returns the current snapshot. POST /runs/{id}/stop cancels a running worker.
2. The Flow validates and plans, then starts UI design and standards research in parallel. Development waits for both.
3. Browser checks run on the generated revision. Code and security review run in parallel, with visual review when screenshots are available. QA uses the verified evidence.
4. Release candidates are exported. A supported defect can trigger a targeted patch. Repeated findings or unchanged files preserve the current draft for inspection.
5. The UI reads the timeline, reports and ZIP through HTTP. The project ZIP contains the linked deliverable. The session ZIP includes debugging evidence.

The project defines eight roles. SoftwareTeamCrew is one reusable crew class instantiated per compatible stage, while the visual reviewer uses a separate multimodal call. The Flow owns orchestration and passes context between stages. Session artifacts are stored on disk. Login output adapts the Forma starter.

## 5. Classroom labs

Run the standalone labs in a separate scratch directory so they do not change DevCrew. Prepare dependencies before class.

### Lab 1.1 — Install the CLI and generate a starter

Install uv using the official installation page. Then run:

~~~powershell
uv tool install "crewai==1.15.39"
uv tool update-shell
crewai --version
crewai create crew class_lab --classic --skip-provider
cd class_lab
tree /F
~~~

Open src/class_lab and identify main.py, crew.py, config/agents.yaml, config/tasks.yaml and tools/. Check the actual generated package name if the CLI normalizes it differently.

### Lab 1.2 — Sync dependencies and run the starter

~~~powershell
uv sync
uv run crewai run
~~~

Before running, configure OPENAI_API_KEY and a supported MODEL in the starter's .env. Inspect its actual run() inputs in main.py. Show the starter output and any file written by the scaffold task.

### Lab 2.1 — Trace a Crew, Agent and Task

Start in crew.py and locate the method decorated with @crew. Follow its agents and tasks to @agent and @task methods, then open the matching YAML keys. Change one role goal or task requirement and explain the expected output change. Run again if time permits. Show where context or kickoff inputs reach the task.

### Lab 3.1 — Run and plot a simple Flow

Generate a separate project with crewai create flow flow_lab --classic --skip-provider, enter flow_lab and run uv sync. Replace the generated package's main.py with the following small deterministic Flow, leaving the scaffold script targets intact.

~~~python
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel


class LabState(BaseModel):
    topic: str = "CrewAI"
    message: str = ""


class LabFlow(Flow[LabState]):
    @start()
    def prepare(self):
        self.state.message = f"Ready to explain {self.state.topic}."

    @listen(prepare)
    def report(self):
        print(self.state.message)
        return self.state.message


def kickoff():
    LabFlow().kickoff()


def plot():
    LabFlow().plot(filename="class_flow", show=False)


def run_with_trigger():
    kickoff()
~~~

~~~powershell
uv run crewai run
uv run crewai flow plot
~~~

Expected output includes Ready to explain CrewAI. Open the generated HTML graph and connect the arrow to @listen(prepare). This sample has two Python steps and requires no model call.

### Lab 4.1 — Locate train and test

From the classic crew starter, run uv run crewai train --help and uv run crewai test --help. Training runs feedback iterations and produces local guidance artifacts. Testing runs evaluations and reports scores. Both can call models. Inspect the scaffold entry points and help output in class. DevCrew uses ordinary pytest regression checks in addition to any manual rehearsal.

### Lab 5.1 — Create and attach a custom tool

In the classic starter, place this in tools/custom_tool.py:

~~~python
from crewai.tools import tool


@tool("estimate_minutes")
def estimate_minutes(slides: int, minutes_per_slide: int) -> int:
    """Calculate the presentation time for a number of slides."""
    return slides * minutes_per_slide
~~~

Import estimate_minutes in crew.py using the generated package name. Add tools=[estimate_minutes] to the Agent constructor for the role assigned to the task. In tasks.yaml, ask that role to call the tool for six slides at two minutes per slide and report the returned value. Expected value: 12. Inspect the tool invocation in the trace. You can verify the calculation directly with estimate_minutes.run(slides=6, minutes_per_slide=2). This tool has no service credentials.

### Lab 6.1 — DevCrew code tour

Open main.py, the Flow, the crew factory and both YAML files. Then show the file guide above.

### Lab 6.2 — DevCrew live run

Start both services and submit: “Build a responsive login UI with email validation and a show-password button.” Follow the stages, open the rendered result and download the ZIP. Label the result as a frontend demonstration adapted from Forma. For a slow provider, show the saved artifacts from a rehearsal.

## References

- [CrewAI installation](https://docs.crewai.com/en/installation)
- [CrewAI CLI](https://docs.crewai.com/en/concepts/cli)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [Create custom tools](https://docs.crewai.com/en/learn/create-custom-tools)
- [Built-in tools catalog](https://docs.crewai.com/en/tools/overview)
