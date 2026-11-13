"""HTTP-only client; backend packages and files are never imported."""
import os
from urllib.parse import quote
import httpx
class BackendClient:
    def __init__(self):self.url=os.getenv('DEVCREW_BACKEND_URL','http://127.0.0.1:8000').rstrip('/')
    def request(self,method,path,**kwargs):
        response=httpx.request(method,self.url+path,timeout=30,**kwargs)
        response.raise_for_status()
        return response
    def health(self):return self.request('GET','/health').json()
    def launch(self,requirements,offline):return self.request('POST','/runs',json={'requirements':requirements,'offline':offline}).json()['id']
    def snapshot(self,identifier):return self.request('GET','/runs/'+quote(identifier,safe='')).json()
    def history(self):return self.request('GET','/runs').json()
    def stop(self,identifier):return self.request('POST','/runs/'+quote(identifier,safe='')+'/stop').json()
    def download(self,identifier,kind):return self.request('GET','/runs/'+quote(identifier,safe='')+'/download/'+kind).content
    def artifact(self,identifier,name):return self.request('GET','/runs/'+quote(identifier,safe='')+'/files/'+quote(name,safe='/')).content
    def diagrams(self,regenerate=False):return self.request('POST' if regenerate else 'GET','/diagrams').json()
    def diagram(self,name):return self.request('GET','/diagrams/'+quote(name,safe='')).content
