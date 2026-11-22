import os, re, time
from pathlib import Path
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE=os.getenv('KNOWLEDGE_URL','https://smart-knowledge-hub-sandy.vercel.app').rstrip('/')
app=FastAPI(title='Smart Knowledge Agent Assist Demo')
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
class Query(BaseModel):
    transcript:str=Field(min_length=2,max_length=3000)

CATEGORIES=[
 ('fiber_los','Fiber / LOS signal fault',[r'\blos\b',r'loss of signal',r'optical signal',r'fiber.*red',r'fibre.*red',r'router.*red',r'රතු',r'ෆයිබර්']),
 ('slow_internet','Slow internet',[r'\bslow\b',r'\bspeed\b',r'buffer',r'ස්ලෝ',r'වේගය']),
 ('trio_shine','Trio Shine',[r'\bshine\b',r'ෂයින්']),
 ('trio_vibe_plus','Trio Vibe+',[r'vibe\s*\+',r'vibe.plus',r'වයිබ් ප්ලස්']),
 ('trio_vibe','Trio Vibe',[r'\bvibe\b',r'වයිබ්']),
 ('taxes','Taxes',[r'\btax\b',r'\bvat\b',r'\bcess\b',r'\bsscl\b',r'බදු']),
 ('tt_routing','Trouble-ticket routing',[r'\bticket\b',r'\btt\b',r'escalat',r'routing',r'ටිකට්']),
 ('contacts','Contacts',[r'contact',r'teleshop',r'hotline',r'දුරකථන']),
 ('sops','Operational SOP',[r'\bsop\b',r'procedure',r'පටිපාටි'])]

def classify(text):
    for key,label,patterns in CATEGORIES:
        if any(re.search(p,text,re.I) for p in patterns):return key,label
    return 'general','General inquiry'

def endpoint(key):
    return {'trio_shine':'/api/knowledge-hub/trio?package=shine','trio_vibe_plus':'/api/knowledge-hub/trio?package=vibe-plus','trio_vibe':'/api/knowledge-hub/trio?package=vibe','taxes':'/api/knowledge-hub/trio?section=taxes','sops':'/api/knowledge-hub/trio?section=sops'}.get(key,'/api/knowledge-hub')

def collections(payload,key):
    if not isinstance(payload,dict):return payload
    # The API may wrap collections under data/knowledgeHub; unwrap conservatively.
    for wrapper in ('data','knowledgeHub','knowledge_hub'):
        if isinstance(payload.get(wrapper),dict) and any(k in payload[wrapper] for k in ('rules','trio','contacts')):
            payload=payload[wrapper];break
    field={'fiber_los':'rules','slow_internet':'rules','tt_routing':'rules','contacts':'contacts'}.get(key)
    return payload.get(field,[]) if field else payload

def relevance(record,key):
    text=str(record).lower()
    if key=='fiber_los':
        # Do not treat every fiber rule as an LOS rule.
        return 6*bool(re.search(r'\blos\b|loss of signal',text))+3*bool(re.search(r'optical|signal',text))+bool(re.search(r'fiber|fibre|red',text))
    if key=='slow_internet':return 4*bool(re.search(r'\bslow\b|speed|bandwidth|throughput',text))+bool('internet' in text)
    if key=='tt_routing':return 4*bool(re.search(r'\btt\b|ticket|dispatch|routing|escalat',text))
    return 1

def select_records(payload,key):
    data=collections(payload,key)
    if isinstance(data,list):
        ranked=sorted(((relevance(x,key),x) for x in data),key=lambda t:t[0],reverse=True)
        matches=[x for score,x in ranked if score>= (3 if key=='fiber_los' else 1)]
        return matches[:3]
    if isinstance(data,dict):
        # Never show unrelated telemetry as operational guidance.
        return [data] if key not in ('fiber_los','slow_internet','tt_routing') else []
    return []

@app.get('/')
def home():return FileResponse(Path(__file__).parent/'static'/'index.html')

@app.post('/api/analyze')
async def analyze(q:Query):
    key,label=classify(q.transcript)
    path=endpoint(key)
    try:
        async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
            response=await client.get(BASE+path,headers={'Accept':'application/json'})
            response.raise_for_status(); payload=response.json()
        matches=select_records(payload,key)
        return {'issue':label,'category':key,'source':BASE+path,'status':'matched' if matches else 'no_match','records':matches,'message':'Matching knowledge records found.' if matches else 'No matching operational rule was found. Do not infer troubleshooting or TT routing.'}
    except (httpx.HTTPError,ValueError) as exc:
        return {'issue':label,'category':key,'source':BASE+path,'status':'unavailable','records':[],'message':'Knowledge Hub is unavailable. No operational advice can be verified.','error':type(exc).__name__}
