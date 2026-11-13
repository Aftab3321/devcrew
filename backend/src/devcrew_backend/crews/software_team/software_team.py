"""Classic CLI scaffold adapted to select predefined stage crews."""
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from ...services.models import Application
from ...services.guardrails import application_guardrail

@CrewBase
class SoftwareTeamCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, role, llm, tools, schema, step_callback):
        self.selected_role = role
        self.llm = llm
        self.stage_tools = tools
        self.schema = schema
        self.step_callback = step_callback

    def _agent(self, name):
        return Agent(config=self.agents_config[name], llm=self.llm,
                     tools=self.stage_tools if name == self.selected_role else [],
                     step_callback=self.step_callback, allow_delegation=False,
                     max_retry_limit=0, verbose=False)

    def _task(self, name):
        config = {**self.tasks_config[name + "_task"], "expected_output": "Valid " + self.schema.__name__}
        return Task(config=config, agent=getattr(self, name)(),
                    output_pydantic=self.schema,
                    response_model=self.schema if not self.stage_tools else None,
                    guardrail=application_guardrail if name == "developer" and self.schema is Application else None,
                    guardrail_max_retries=1)

    @agent
    def planner(self):
        return self._agent("planner")

    @task
    def planner_task(self):
        return self._task("planner")

    @agent
    def designer(self):
        return self._agent("designer")

    @task
    def designer_task(self):
        return self._task("designer")

    @agent
    def standards(self):
        return self._agent("standards")

    @task
    def standards_task(self):
        return self._task("standards")

    @agent
    def developer(self):
        return self._agent("developer")

    @task
    def developer_task(self):
        return self._task("developer")

    @agent
    def reviewer(self):
        return self._agent("reviewer")

    @task
    def reviewer_task(self):
        return self._task("reviewer")

    @agent
    def security(self):
        return self._agent("security")

    @task
    def security_task(self):
        return self._task("security")

    @agent
    def quality(self):
        return self._agent("quality")

    @task
    def quality_task(self):
        return self._task("quality")

    @agent
    def visual(self):
        return self._agent("visual")

    @task
    def visual_task(self):
        return self._task("visual")

    @crew
    def crew(self):
        worker = getattr(self, self.selected_role)()
        work = getattr(self, self.selected_role + "_task")()
        return Crew(agents=[worker], tasks=[work], process=Process.sequential,
                    memory=False, planning=False, verbose=False)
