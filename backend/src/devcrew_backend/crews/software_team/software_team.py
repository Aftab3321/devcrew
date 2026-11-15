"""Classic CLI scaffold adapted to select predefined stage crews."""

from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from ...services.models import Application
from ...services.guardrails import application_guardrail


@CrewBase
class SoftwareTeamCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # Store the model, schema and tool bindings for the selected role.
    def __init__(self, role, llm, tools, schema, step_callback):
        self.selected_role = role
        self.llm = llm
        self.stage_tools = tools
        self.schema = schema
        self.step_callback = step_callback

    # Build an agent from YAML with the tools assigned to its stage.
    def _agent(self, name):
        return Agent(
            config=self.agents_config[name],
            llm=self.llm,
            tools=self.stage_tools if name == self.selected_role else [],
            step_callback=self.step_callback,
            allow_delegation=False,
            max_retry_limit=0,
            verbose=False,
        )

    # Bind the YAML task to its agent and the output schema selected at runtime.
    def _task(self, name):
        config = {
            **self.tasks_config[name + "_task"],
            "expected_output": "Valid " + self.schema.__name__,
        }
        return Task(
            config=config,
            agent=getattr(self, name)(),
            output_pydantic=self.schema,
            response_model=self.schema if not self.stage_tools else None,
            guardrail=(
                application_guardrail
                if name == "developer" and self.schema is Application
                else None
            ),
            guardrail_max_retries=1,
        )

    # Build the predefined planner agent.
    @agent
    def planner(self):
        return self._agent("planner")

    # Bind the planner task to its configured output.
    @task
    def planner_task(self):
        return self._task("planner")

    # Build the predefined designer agent.
    @agent
    def designer(self):
        return self._agent("designer")

    # Bind the designer task to its configured output.
    @task
    def designer_task(self):
        return self._task("designer")

    # Build the predefined standards agent.
    @agent
    def standards(self):
        return self._agent("standards")

    # Bind the standards task to its configured output.
    @task
    def standards_task(self):
        return self._task("standards")

    # Build the predefined developer agent.
    @agent
    def developer(self):
        return self._agent("developer")

    # Bind the developer task to its configured output.
    @task
    def developer_task(self):
        return self._task("developer")

    # Build the predefined reviewer agent.
    @agent
    def reviewer(self):
        return self._agent("reviewer")

    # Bind the reviewer task to its configured output.
    @task
    def reviewer_task(self):
        return self._task("reviewer")

    # Build the predefined security agent.
    @agent
    def security(self):
        return self._agent("security")

    # Bind the security task to its configured output.
    @task
    def security_task(self):
        return self._task("security")

    # Build the predefined quality agent.
    @agent
    def quality(self):
        return self._agent("quality")

    # Bind the quality task to its configured output.
    @task
    def quality_task(self):
        return self._task("quality")

    # Build the predefined visual agent.
    @agent
    def visual(self):
        return self._agent("visual")

    # Bind the visual task to its configured output.
    @task
    def visual_task(self):
        return self._task("visual")

    # Assemble a single-stage crew while the Flow handles ordering and concurrency.
    @crew
    def crew(self):
        worker = getattr(self, self.selected_role)()
        work = getattr(self, self.selected_role + "_task")()
        return Crew(
            agents=[worker],
            tasks=[work],
            process=Process.sequential,
            memory=False,
            planning=False,
            verbose=False,
        )
