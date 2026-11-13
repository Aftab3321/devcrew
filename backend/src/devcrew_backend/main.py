"""CLI entry points from the generated CrewAI Flow project."""
import json
import os
import sys
from dotenv import load_dotenv
from .services.paths import BACKEND_ROOT

load_dotenv(BACKEND_ROOT / '.env')

def kickoff():
    """Keep the local backend available; launched by crewai run."""
    import uvicorn
    port=int(os.getenv('DEVCREW_BACKEND_PORT','8000'))
    uvicorn.run('devcrew_backend.services.api:app',host='127.0.0.1',port=port)

def plot():
    from .services.diagrams import generate_diagrams
    generate_diagrams(BACKEND_ROOT/'diagrams')
    print('Diagrams saved to backend/diagrams')

def run_with_trigger():
    from .services.facade import run_team
    payload=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
    result=run_team(payload.get('requirements','Build a polished login page'),offline=payload.get('offline',True))
    print(json.dumps(result))

if __name__=='__main__': kickoff()
