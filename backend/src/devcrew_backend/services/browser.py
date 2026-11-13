"""Render local project files in sandboxed headless Chrome/Edge and collect evidence."""
import base64
import functools
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from .models import BrowserReport,BrowserCheck

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def end_headers(self):
        self.send_header("Content-Security-Policy","default-src 'self'; img-src 'self' https://images.unsplash.com data:; style-src 'self'; script-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'")
        super().end_headers()

def browser_executable():
    options=[os.getenv("CHROME_PATH"),shutil.which("google-chrome"),shutil.which("chromium"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"]
    return next((str(p) for p in options if p and Path(p).exists()),None)

MEASURE=r"""(()=>{
const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
const inputs=[...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(visible);
const badLabels=inputs.filter(e=>!(e.labels&&e.labels.length)&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')).map(e=>e.id||e.type);
const overflow=[...document.querySelectorAll('input,button,select,textarea')].filter(visible).filter(e=>{const r=e.getBoundingClientRect(),p=(e.closest('form')||e.parentElement).getBoundingClientRect();return r.left<0||r.right>innerWidth+1||r.right>p.right+2||r.left<p.left-2}).map(e=>e.id||e.tagName);
return {width:innerWidth,pageOverflow:document.documentElement.scrollWidth>innerWidth+2,overflow,badLabels,brokenImages:[...document.images].filter(e=>!e.complete||e.naturalWidth===0).map(e=>e.getAttribute('src')),hasStyles:[...document.styleSheets].some(s=>s.href),hasScripts:[...document.scripts].some(s=>s.src)};
})()"""

LOGIN_CHECK=r"""(()=>{
const email=document.querySelector('[data-testid=email]')||document.querySelector('input[type=email]');
const password=document.querySelector('[data-testid=password]')||document.querySelector('input[type=password]');
if(!email||!password)return {applicable:false};
const initial=email.value;email.value='not-an-email';const rejectsInvalid=!email.checkValidity();email.value='person+tag@example.com';const acceptsAlias=email.checkValidity();email.value=initial;
const toggle=document.querySelector('[data-testid=password-toggle]');let toggleWorks=false;if(toggle){const t=password.type;toggle.click();toggleWorks=password.type!==t;toggle.click();}
const oldEmail=email.value,oldPassword=password.value;email.value="person@example.com";password.value="demo-password";const submit=document.querySelector('[data-testid=submit]');if(submit)submit.click();const feedback=document.querySelector('[data-testid=status]');const demoFeedback=Boolean(feedback&&feedback.textContent.trim());email.value=oldEmail;password.value=oldPassword;
return {applicable:true,rejectsInvalid,acceptsAlias,toggleWorks,demoFeedback};
})()"""

def inspect_project(folder,evidence_dir):
    folder=Path(folder).resolve();evidence_dir=Path(evidence_dir).resolve();evidence_dir.mkdir(parents=True,exist_ok=True)
    executable=browser_executable()
    if not executable:return BrowserReport(available=False,limitations=["Chrome/Edge not installed. Set CHROME_PATH to enable actual rendering."])
    server=ThreadingHTTPServer(("127.0.0.1",0),functools.partial(QuietHandler,directory=str(folder)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    profile=evidence_dir/"browser-profile"
    process=subprocess.Popen([executable,"--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--remote-debugging-port=0","--user-data-dir="+str(profile),"about:blank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**({"creationflags":subprocess.CREATE_NO_WINDOW} if os.name=="nt" else {}))
    ws=None;checks=[];screens=[];errors=[]
    try:
        marker=profile/"DevToolsActivePort";deadline=time.monotonic()+20
        while not marker.exists():
            if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError("Browser did not start")
            time.sleep(.1)
        port=int(marker.read_text().splitlines()[0])
        targets=json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list",timeout=10))
        import websocket
        ws=websocket.create_connection(next(t for t in targets if t["type"]=="page")["webSocketDebuggerUrl"],suppress_origin=True,timeout=15)
        sequence=0
        def command(method,params=None):
            nonlocal sequence
            sequence+=1;ws.send(json.dumps({"id":sequence,"method":method,"params":params or {}}))
            while True:
                item=json.loads(ws.recv())
                if item.get("method")=="Runtime.exceptionThrown":errors.append(item.get("params",{}).get("exceptionDetails",{}).get("text","JavaScript exception"))
                if item.get("id")==sequence:
                    if "error" in item:raise RuntimeError(item["error"].get("message","Browser command failed"))
                    return item.get("result",{})
        def evaluate(expression):return command("Runtime.evaluate",{"expression":expression,"returnByValue":True,"awaitPromise":True}).get("result",{}).get("value")
        command("Runtime.enable");command("Page.enable")
        for name,width,height in [("desktop",1440,1000),("mobile",390,844)]:
            command("Emulation.setDeviceMetricsOverride",{"width":width,"height":height,"deviceScaleFactor":1,"mobile":False})
            command("Page.navigate",{"url":f"http://127.0.0.1:{server.server_port}/index.html"})
            for _ in range(60):
                if evaluate("document.readyState === 'complete' && location.pathname === '/index.html'"):break
                time.sleep(.1)
            time.sleep(.3)
            data=evaluate(MEASURE) or {}
            (evidence_dir/(name+".json")).write_text(json.dumps(data,indent=2),encoding="utf-8")
            for rule,passed,detail in [("layout.viewport",not data.get("pageOverflow",True),"No horizontal page overflow"),("layout.controls",not data.get("overflow",["unknown"]),"Controls remain inside their form and viewport"),("accessibility.labels",not data.get("badLabels",["unknown"]),"Visible form controls have associated labels"),("assets.images",not data.get("brokenImages",["unknown"]),"Referenced images loaded"),("structure.styles",data.get("hasStyles",False),"External stylesheet loaded"),("structure.scripts",data.get("hasScripts",False),"External JavaScript linked")]:
                checks.append(BrowserCheck(rule_id=name+"."+rule,passed=bool(passed),detail=detail+"; measured="+json.dumps(data)))
            screenshot=evidence_dir/(name+".png")
            screenshot.write_bytes(base64.b64decode(command("Page.captureScreenshot",{"format":"png"})["data"]));screens.append(str(screenshot))
            login=evaluate(LOGIN_CHECK) or {}
            if login.get("applicable"):
                for key in ["rejectsInvalid","acceptsAlias","toggleWorks","demoFeedback"]:checks.append(BrowserCheck(rule_id=name+".login."+key,passed=bool(login.get(key)),detail="Browser interaction: "+key))
        checks.append(BrowserCheck(rule_id="runtime.javascript",passed=not errors,detail="No uncaught JavaScript exceptions" if not errors else "; ".join(errors)))
        return BrowserReport(available=True,checks=checks,screenshots=screens,console_errors=errors,limitations=["Automated checks cover sampled desktop/mobile viewports and basic interactions, not all browsers or a full accessibility audit."])
    except Exception as exc:
        return BrowserReport(available=False,checks=checks,screenshots=screens,limitations=["Browser check unavailable: "+type(exc).__name__+". Inspect local browser setup."])
    finally:
        if ws:
            try:ws.send(json.dumps({"id":9999,"method":"Browser.close"}));ws.close()
            except Exception:pass
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
        server.shutdown();server.server_close()
