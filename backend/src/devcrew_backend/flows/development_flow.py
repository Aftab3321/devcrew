import asyncio
import hashlib
import json
import shutil
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,Field,SerializeAsAny
from crewai.flow.flow import Flow,start,listen,router,and_
from ..services.models import Plan,Research,DesignSpec,Application,Review,Assessment,Handoff,BrowserReport,Issue
from ..services.guardrails import check_request
from ..services.project import validate_project,project_issues,materialize,merge_patch,digest
from ..services.browser import inspect_project

class State(BaseModel):
    requirements:str=""
    plan:Plan|None=None
    research:dict[str,Research]=Field(default_factory=dict)
    design:DesignSpec|None=None
    app:Application|None=None
    reviews:dict[str,SerializeAsAny[Review]]=Field(default_factory=dict)
    assessment:Assessment|None=None
    browser:BrowserReport|None=None
    revision:int=0
    outcome:str="pending"

class DevelopmentFlow(Flow[State]):
    def __init__(self,session,backend,on_stage=None):
        super().__init__();self.session,self.backend=session,backend
        self.on_stage=on_stage or (lambda name,content:None)
    def publish(self,key,value):
        content=value.model_dump() if isinstance(value,BaseModel) else value
        self.session.write(key+".json",content);self.session.remember(key,content)
        self.on_stage(key,json.dumps(content,indent=2))
    def handoff(self,sender,recipient,artifact,message):
        self.session.event("handoff",**Handoff(sender=sender,recipient=recipient,artifact=artifact,revision=self.state.revision,message=message).model_dump())
    async def task(self,role,prompt,images=None):
        import time
        self.session.event("agent_started",agent=role,revision=self.state.revision);started=time.monotonic()
        try:
            result=await asyncio.to_thread(self.backend.execute,role,prompt,**({"images":images} if images is not None else {}))
        except BaseException as exc:
            self.session.event("agent_failed",agent=role,exception_type=type(exc).__name__);raise
        self.session.event("agent_completed",agent=role,revision=self.state.revision,elapsed_seconds=round(time.monotonic()-started,2))
        return result
    @start()
    def validate_request(self):check_request(self.state.requirements);self.session.event("input_guardrail",passed=True)
    @listen(validate_request)
    async def plan_team(self):
        self.state.plan=await self.task("planner","USER BRIEF:\n"+self.state.requirements+"\nPlan a multi-file UI deliverable. Design, standards and security are required baseline stages. Avoid invented requirements.")
        for role in ["designer","standards","security"]:
            if role not in self.state.plan.specialists:
                self.state.plan.specialists.append(role)
                setattr(self.state.plan.selection_reasons,role,"Required UI delivery baseline")
                self.session.event("required_stage",agent=role,message="Required UI delivery baseline; cannot be skipped")
        self.publish("plan",self.state.plan)
    async def research_task(self,role):
        self.handoff("manager",role,"plan.json","Provide the required design/standards specification")
        result=await self.task(role,json.dumps({"original_user_brief":self.state.requirements,"plan":self.state.plan.model_dump(),"instruction":"Preserve the requested visual composition and requirements; do not replace them with a generic centered card."}))
        self.state.research[role]=result
        if role=="designer":self.state.design=result
        self.publish(role,result)
    @listen(plan_team)
    async def design_research(self):await self.research_task("designer")
    @listen(plan_team)
    async def standards_research(self):await self.research_task("standards")
    @listen(and_(design_research,standards_research))
    async def develop(self):
        self.handoff("manager","developer","designer.json","Implement the approved visual direction as linked files")
        from ..services.starter import is_login,login_starter,integrate_login_patch
        context={"brief":self.state.requirements,"plan":self.state.plan.model_dump(),"design":self.state.design.model_dump(),"standards":self.state.research["standards"].model_dump()}
        if is_login(self.state.requirements):
            base=login_starter(self.state.design)
            context["starting_files"]=[f.model_dump() for f in base.files if f.path in {"index.html","assets/css/styles.css","assets/js/app.js","README.md"}]
            patch=await self.task("developer","STARTER_PATCH\nAdapt the tested design foundation to the brief. Return only genuinely needed changed_files. Keep shell/story/signin layout classes, all local assets, existing hooks and assets/css/layout.css. Theme overrides use CSS custom properties only. Do not replace the interface with a generic card. If current behavior meets the brief, improve README instead of rewriting correct code.\n"+json.dumps(context))
            self.state.app,rejected=integrate_login_patch(base,patch)
            self.publish("design_foundation",{"name":"Forma login design system","kind":"Reusable authored foundation, not claimed as fresh AI generation","retained_contracts":rejected})
        else:
            self.state.app=await self.task("developer",json.dumps(context))
        self.save_code()
    def save_code(self):
        validate_project(self.state.app)
        materialize(self.state.app,self.session.path/f"project_v{self.state.revision}")
        self.publish(f"implementation_v{self.state.revision}",self.state.app)
        self.session.event("code_snapshot",revision=self.state.revision,sha256=digest(self.state.app),files=[f.path for f in self.state.app.files])
    async def render(self):
        self.session.event("agent_started",agent="browser",revision=self.state.revision)
        report=await asyncio.to_thread(inspect_project,self.session.path/f"project_v{self.state.revision}",self.session.path/f"browser_v{self.state.revision}")
        self.state.browser=report;self.publish(f"browser_v{self.state.revision}",report)
        self.session.event("agent_completed" if report.available else "agent_failed",agent="browser",message="Desktop/mobile browser checks completed" if report.available else "; ".join(report.limitations))
        return report
    def verified_findings(self,reviews):
        files={f.path:f.content for f in self.state.app.files};blockers=[];advisory=[]
        for role,review in reviews.items():
            for issue in review.issues:
                if not issue.rule_id:issue.rule_id=role+"."+hashlib.sha256((issue.file+issue.fix).encode()).hexdigest()[:12]
                real_code=bool(issue.file in files and issue.evidence.strip() and issue.evidence.strip() in files[issue.file])
                real_screen=role=="visual" and self.state.browser.available and issue.file in {"screenshot:desktop","screenshot:mobile"}
                if issue.severity in {"high","critical"} and (real_code or real_screen):blockers.append(issue)
                else:advisory.append(issue)
        return blockers,advisory
    @listen(develop)
    async def review_cycles(self):
        seen_code=set();previous_rules=set()
        while True:
            revision=self.state.revision
            structural=project_issues(self.state.app)
            self.publish(f"static_checks_v{revision}",{"issues":[i.model_dump() for i in structural]})
            browser=await self.render()
            context={"plan":self.state.plan.model_dump(),"design":self.state.design.model_dump(),"project":self.state.app.model_dump(),"browser":browser.model_dump()}
            roles=["reviewer","security"]
            jobs=[self.task(role,json.dumps(context)) for role in roles]
            if browser.available:
                roles.append("visual")
                jobs.append(self.task("visual",json.dumps({"original_user_brief":self.state.requirements,"design":self.state.design.model_dump(),"browser_checks":[c.model_dump() for c in browser.checks]}),images=browser.screenshots))
            results=await asyncio.gather(*jobs)
            self.state.reviews=dict(zip(roles,results))
            for role,result in self.state.reviews.items():self.publish(f"{role}_v{revision}",result)
            visual=self.state.reviews.get("visual")
            if visual and visual.design_score < 7:
                visual.issues.append(Issue(rule_id="visual.design_brief",file="screenshot:desktop",severity="high",evidence=visual.brief_adherence,fix="Improve the rendered composition to match the design brief: "+visual.summary))
            verified,advisory=self.verified_findings(self.state.reviews)
            blockers=structural+verified
            browser_failed=[c for c in browser.checks if not c.passed]
            ids={i.rule_id for i in blockers}|{c.rule_id for c in browser_failed}
            self.publish(f"verified_findings_v{revision}",{"blocking":[i.model_dump() for i in blockers],"advisory":[i.model_dump() for i in advisory],"failed_browser_checks":[c.model_dump() for c in browser_failed]})
            # QA sees concise verified evidence, not another copy of the full code.
            assessment=await self.task("quality",json.dumps({"plan":self.state.plan.model_dump(),"design":self.state.design.model_dump(),"verified_issues":[i.model_dump() for i in blockers],"browser":browser.model_dump(),"visual":self.state.reviews.get("visual").model_dump() if "visual" in self.state.reviews else None,"review_summaries":{k:v.summary for k,v in self.state.reviews.items()}}))
            assessment.decision="revise" if ids or not browser.available else "release"
            self.state.assessment=assessment;self.publish(f"quality_v{revision}",assessment)
            if assessment.decision=="release":self.state.outcome="release_candidate";return
            fingerprint=digest(self.state.app)
            if not browser.available or fingerprint in seen_code or ids & previous_rules:
                self.session.event("no_progress",message="Browser unavailable or the same verified defect remains after its targeted repair; preserving the project instead of repeating broad rewrites")
                self.state.outcome="needs_attention";return
            seen_code.add(fingerprint);previous_rules=ids
            self.handoff("quality","developer",f"verified_findings_v{revision}.json","Patch only substantiated defects; keep unrelated files intact")
            patch=await self.task("developer","REVISION_PATCH\nReturn changed_files only, stable addressed_issue_ids and notes. Do not regenerate unchanged files.\n"+json.dumps({"project":self.state.app.model_dump(),"design":self.state.design.model_dump(),"blocking_issues":[i.model_dump() for i in blockers],"browser_failures":[c.model_dump() for c in browser_failed]}))
            from ..services.starter import is_login,integrate_login_patch
            if is_login(self.state.requirements):
                self.state.app,rejected=integrate_login_patch(self.state.app,patch)
                if rejected:self.publish(f"patch_notes_v{revision}",{"retained_contracts":rejected})
            else:self.state.app=merge_patch(self.state.app,patch)
            self.state.revision+=1;self.save_code()
    @router(review_cycles)
    def release_route(self)->Literal["release_candidate","needs_attention"]:
        if self.state.outcome=="release_candidate":return "release_candidate"
        return "needs_attention"
    @listen("release_candidate")
    def release(self):
        materialize(self.state.app,self.session.path/"project");self.finish()
    @listen("needs_attention")
    def save_unresolved(self):self.finish()
    def finish(self):
        self.session.write("state.json",self.state.model_dump());self.session.write("usage.json",self.backend.usage)
        self.session.event("finished",outcome=self.state.outcome)
