from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from client import BackendClient
from streamlit.testing.v1 import AppTest

def test_http_ui_parallel_progress_and_stop(monkeypatch):
    stamp=datetime.now(timezone.utc).isoformat()
    state={'running':True,'elapsed':2,'events':[{'time':stamp,'kind':'agent_started','agent':r} for r in ['reviewer','security']],
           'terminal':None,'result':None,'id':'demo','artifacts':{},'project_files':[]}
    monkeypatch.setattr(BackendClient,'health',lambda self:{'status':'ok'})
    monkeypatch.setattr(BackendClient,'snapshot',lambda self,identifier:state.copy())
    monkeypatch.setattr(BackendClient,'history',lambda self:[])
    monkeypatch.setattr(BackendClient,'diagrams',lambda self,regenerate=False:[])
    monkeypatch.setattr(BackendClient,'download',lambda *args:b'ZIP')
    def stop(self,identifier):
        state['running']=False
        state['terminal']={'status':'stopped','message':'Stopped by user'}
    monkeypatch.setattr(BackendClient,'stop',stop)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
    app.session_state['job']='demo';app.run(timeout=30)
    assert not app.exception
    assert not app.slider
    assert any('Code review + Security audit' in item.value for item in app.info)
    next(b for b in app.button if b.label=='Stop run now').click().run(timeout=30)
    assert not app.exception
    assert not state['running']

def test_backend_unavailable_is_readable(monkeypatch):
    def unavailable(self):raise ConnectionError('offline')
    monkeypatch.setattr(BackendClient,'health',unavailable)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert any('Backend unavailable' in item.value for item in app.error)
