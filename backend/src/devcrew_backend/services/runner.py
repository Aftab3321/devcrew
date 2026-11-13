"""Process-isolated UI jobs: real stop, without run deadlines."""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from .paths import BACKEND_ROOT
from .storage import Session

ROOT=BACKEND_ROOT

def events(path):
    try:
        lines=(Path(path)/"events.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    result=[]
    for line in lines:
        try: result.append(json.loads(line))
        except ValueError: pass  # A concurrent append may still be incomplete.
    return result

class Job:
    def __init__(self,path,command):
        self.path=Path(path)
        self.started=time.monotonic()
        self.lock=threading.RLock()
        self.reason=None
        self.finished=None
        self.log=(self.path/"worker.log").open("w",encoding="utf-8")
        options={"creationflags":subprocess.CREATE_NO_WINDOW} if sys.platform=="win32" else {}
        self.process=subprocess.Popen(command,cwd=ROOT,stdout=self.log,stderr=subprocess.STDOUT,**options)
        self.pid=self.process.pid
        threading.Thread(target=self._watch,daemon=True).start()

    def stop(self,reason="Stopped by user"):
        with self.lock:
            if self.process.poll() is not None: return
            self.reason=reason
            self.process.terminate()
            try: self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            Session.attach(self.path).event("run_stopped",message=reason)
            Session.attach(self.path).write("terminal.json",{"status":"stopped","message":reason})

    def _watch(self):
        self.process.wait()
        self.finished=time.monotonic()
        self.log.close()

    @property
    def running(self): return self.process.poll() is None

    def _snapshot(self):
        records=events(self.path)
        result=None
        terminal=None
        for filename in ["result.json","terminal.json"]:
            try:
                value=json.loads((self.path/filename).read_text(encoding="utf-8"))
                if filename=="result.json": result=value
                else: terminal=value
            except (OSError,ValueError): pass
        if not self.running and terminal is None and result is None:
            terminal={"status":"failed","message":"Worker exited unexpectedly (code "+str(self.process.returncode)+"). Check saved diagnostics."}
        return {"running":self.running,"elapsed":(self.finished or time.monotonic())-self.started,
                "events":records,"result":result,"terminal":terminal}

    def snapshot(self):
        with self.lock:
            return self._snapshot()

def launch(requirements,*,offline=True):
    from .guardrails import check_request
    check_request(requirements)
    session=Session(ROOT/"outputs",requirements,"offline fixture" if offline else "live")
    session.write("job.json",{"requirements":requirements,"offline":offline})
    return Job(session.path,[sys.executable,"-X","utf8","-u","-m","devcrew_backend.services.worker",str(session.path)])
