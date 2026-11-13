"""Request observability and automatic repeated-action recovery (no run budgets)."""
import json
import hashlib
import threading
import time

class ConfigurationError(ValueError):
    """Safe configuration message for the UI."""

class RequestMonitor:
    def __init__(self,session):
        self.session=session
        self.lock=threading.RLock()
        self.requests=0
        self.stage_counts={}
        self.actions={}
        self.finalizing=set()
    def begin(self,stage):
        with self.lock:
            self.stage_counts[stage]=0
            self.actions[stage]=set()
            self.finalizing.discard(stage)
    def before_request(self,stage,request):
        with self.lock:
            if stage in self.finalizing:
                try:
                    import httpx
                    body=json.loads(request.content)
                    if body.get("tools"):
                        body["tool_choice"]="none"
                        if "messages" in body:
                            body["messages"].append({"role":"system","content":"The same tool action was repeated without new evidence. Use the available results and return the final structured answer now. Do not call another tool."})
                        encoded=json.dumps(body).encode()
                        request._content=encoded
                        request.stream=httpx.ByteStream(encoded)
                        request.headers["content-length"]=str(len(encoded))
                except (ValueError,AttributeError): pass
            self.requests+=1
            self.stage_counts[stage]=self.stage_counts.get(stage,0)+1
            request.extensions["devcrew_started"]=time.monotonic()
            self.session.event("model_request",agent=stage,request_number=self.requests,stage_request=self.stage_counts[stage])
    def after_response(self,stage,response):
        elapsed=time.monotonic()-response.request.extensions.get("devcrew_started",time.monotonic())
        response.read()
        body={}
        usage={}
        finish=None
        try:
            body=response.json()
            usage={k:v for k,v in body.get("usage",{}).items() if k in {"prompt_tokens","completion_tokens","total_tokens","input_tokens","output_tokens"} and isinstance(v,(int,float))}
            finish=(body.get("choices") or [{}])[0].get("finish_reason")
        except (ValueError,KeyError,TypeError):
            pass
        self.session.event("model_response",agent=stage,http_status=response.status_code,
                           elapsed_seconds=round(elapsed,2),usage=usage,finish_reason=finish)
        if response.status_code >= 400 or (isinstance(body,dict) and body.get("error")):
            from .errors import provider_error
            detail=provider_error(response.status_code,body)
            self.session.write("provider_error.json",detail)
            self.session.event("provider_error",agent=stage,**detail)


        try:
            for call in (body.get("choices") or [{}])[0].get("message",{}).get("tool_calls",[]):
                fn=call.get("function",{})
                args=json.loads(fn.get("arguments","{}"))
                if isinstance(args,dict): args={k:v for k,v in args.items() if k not in {"context","backstory"}}
                signature=hashlib.sha256(json.dumps([fn.get("name"),args],sort_keys=True).encode()).hexdigest()
                with self.lock:
                    if signature in self.actions.setdefault(stage,set()) and stage not in self.finalizing:
                        self.finalizing.add(stage)
                        self.session.event("loop_recovered",agent=stage,message="Repeated action detected; switching to final answer using existing evidence")
                    self.actions[stage].add(signature)
        except (ValueError,TypeError,AttributeError,UnboundLocalError): pass
