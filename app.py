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
        # Structured operational records only: never render a full API envelope.
        if key == 'general':
            return []
        return [data] if any(k in data for k in ('rule_code','rule_name','advice_instructions','name','pricing')) else []
    return []


# Guidance fields are extracted only when explicitly present in the source rule.
# Unknown operational details are never generated.
GUIDANCE_FIELDS = {
    'steps': ('troubleshootingsteps', 'troubleshooting', 'steps', 'diagnosticsteps', 'resolutionsteps', 'procedure', 'actions', 'actionsteps', 'recommendations'),
    'questions': ('questions', 'questionstoask', 'customerquestions', 'verificationquestions', 'diagnosticquestions'),
    'routing': ('ttrouting', 'routing', 'routingteam', 'dispatchteam', 'department', 'assignedteam', 'escalation', 'escalationpath', 'ttcategory', 'ticketcategory'),
}

def normalized(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def to_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return ' '.join(to_text(x) for x in value)
    if isinstance(value, dict):
        return ' '.join(f'{k}: {to_text(v)}' for k, v in value.items())
    return ''

def matching_fields(record, field_names):
    matches = []
    def visit(node, depth=0):
        if depth > 4 or not isinstance(node, dict):
            return
        for key, value in node.items():
            if normalized(key) in field_names and value not in (None, '', [], {}):
                matches.append(value)
            elif isinstance(value, dict):
                visit(value, depth + 1)
    visit(record)
    return matches

def as_guidance_items(value):
    if isinstance(value, list):
        return [to_text(item).strip() for item in value if to_text(item).strip()][:15]
    if isinstance(value, dict):
        return [f'{k}: {to_text(v)}' for k, v in value.items() if to_text(v).strip()][:15]
    if isinstance(value, str):
        return [x.strip(' -•\t') for x in re.split(r'\n+|(?<=;)\s+', value) if x.strip(' -•\t')][:15]
    return [to_text(value)] if to_text(value).strip() else []

def format_guidance(record):
    title_fields = matching_fields(record, ('title', 'name', 'rulename', 'faultname', 'issuename', 'rule', 'fault', 'category', 'faulttype', 'issue'))
    id_fields = matching_fields(record, ('id', 'ruleid', 'code', 'rulecode'))
    sections = {}
    for kind, names in GUIDANCE_FIELDS.items():
        items = []
        for value in matching_fields(record, names):
            items.extend(as_guidance_items(value))
        sections[kind] = list(dict.fromkeys(items))[:15]
    used = set(sum((list(names) for names in GUIDANCE_FIELDS.values()), []) + ['title','name','rulename','faultname','issuename','rule','fault','category','faulttype','issue','id','ruleid','code','rulecode'])
    details = [{'label': k, 'value': v} for k, v in record.items() if normalized(k) not in used and v not in (None, '', [], {})][:20]
    return {
        'title': to_text(title_fields[0])[:150] if title_fields else 'Matched Knowledge Hub rule',
        'rule_id': to_text(id_fields[0])[:100] if id_fields else None,
        'steps': sections['steps'],
        'questions': sections['questions'],
        'routing': sections['routing'],
        'details': details,
    }

APP_VERSION = "4g-dashboard-fix-20261122-b"

@app.get('/api/version')
def api_version():
    return {'version': APP_VERSION, 'features': ['4g-prepaid-postpaid','4g-recharge-rules','trio-packages']}

@app.get('/')
def home():return FileResponse(Path(__file__).parent/'static'/'index.html', headers={'Cache-Control':'no-store, max-age=0'})


# Search uses the actual Knowledge Hub collection schema rather than treating
# the whole API response (success, telemetry, metrics) as a knowledge record.
def knowledge_data(payload):
    if not isinstance(payload, dict):
        return {}
    for name in ('data', 'knowledgeHub', 'knowledge_hub'):
        nested = payload.get(name)
        if isinstance(nested, dict) and any(k in nested for k in ('collections', 'rules', 'trio')):
            payload = nested
            break
    result = dict(payload)
    if isinstance(payload.get('collections'), dict):
        result.update(payload['collections'])
    return result

def list_of(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values()) if value and all(isinstance(x, dict) for x in value.values()) else []
    return []

def classify_intent(transcript):
    t = transcript.lower()
    # Check 4G before generic fault classification, including requests spoken
    # as "four g", "4 g", "LTE", or Sinhala 4G references.
    if re.search(r'4\s*g|four\s*g|\blte\b|4ජී|ෆෝජී', t, re.I):
        return '4g', '4G LTE Services'
    if re.search(r'\btrio\b|\bshine\b|\bvibe\b', t) and re.search(r'price|cost|rent|package|plan|මිල|ගාස්තු', t):
        return 'trio_packages', 'Trio Package Prices'
    return classify(transcript)

def four_g_rules(payload):
    data = knowledge_data(payload)
    return [
        x for x in list_of(data.get('rules'))
        if isinstance(x, dict) and
        (re.search(r'4g|lte', ' '.join(map(str, [x.get('rule_code',''),x.get('rule_name',''),x.get('description','')])), re.I))
        and x.get('is_active', True) is not False
    ]

def four_g_information(payload):
    records = four_g_rules(payload)
    return [{
        'title': rule.get('rule_name','4G service rule'),
        'rule_id': rule.get('rule_code'),
        'description': rule.get('description'),
        'symptoms': rule.get('symptom_patterns',[]),
        'action_type': rule.get('action_type'),
        'target_group': rule.get('target_group'),
        'advice': rule.get('advice_instructions'),
        'required_fields': rule.get('validation_requirements',{}).get('required_fields',[]),
        'allowed_channels': rule.get('validation_requirements',{}).get('thresholds',{}).get('allowed_channels',[]),
    } for rule in records]

# 4G package data must come from a distinct 4G/LTE collection.
# Never identify Trio/fibre offers as 4G products.
FOUR_G_COLLECTIONS = ('four_g','fourG','4g','lte','ltePackages',
                      'fourGPackages','4gPackages','mobile4g','mobile4G',
                      'mobileBroadband','mobile_broadband')

def first_value(source, *names):
    if not isinstance(source, dict):
        return None
    for name in names:
        if source.get(name) is not None:
            return source[name]
    return None

def package_kind(package):
    text = ' '.join(str(x) for x in (
        first_value(package,'type','planType','plan_type','category',
                    'connectionType','billingType','subscriptionType') or '',
        first_value(package,'name','packageName','title') or '')).lower()
    if 'postpaid' in text or 'post-paid' in text:
        return 'postpaid'
    if 'prepaid' in text or 'pre-paid' in text:
        return 'prepaid'
    return 'unspecified'

def four_g_packages(payload):
    data = knowledge_data(payload)
    sources = []
    # Dedicated /api/knowledge-hub/4g returns prepaid/postpaid arrays at root.
    # Keep support for earlier collection-based response shapes.
    for kind in ('prepaid','postpaid'):
        for plan in list_of(data.get(kind)):
            if isinstance(plan, dict):
                item = dict(plan)
                item['type'] = kind
                sources.append(item)
    for key in FOUR_G_COLLECTIONS:
        node = data.get(key)
        if isinstance(node, list):
            sources.extend(node)
        elif isinstance(node, dict):
            for subkey in ('packages','plans','prepaid','postpaid','dataPackages','data_plans'):
                value = node.get(subkey)
                if isinstance(value, list):
                    for p in value:
                        if isinstance(p, dict):
                            entry = dict(p)
                            if subkey in ('prepaid','postpaid'):
                                entry.setdefault('type', subkey)
                            sources.append(entry)
            if not sources and ('name' in node or 'packageName' in node):
                sources.append(node)
    results, seen = [], set()
    for p in sources:
        if not isinstance(p, dict):
            continue
        price = first_value(p,'priceWithTaxLkr','price_with_tax_lkr',
                            'monthlyRentalLkr','rentalLkr','priceLkr',
                            'price','amountLkr','amount')
        price_info = p.get('pricing',{})
        if price is None and isinstance(price_info, dict):
            price = first_value(price_info,'priceWithTaxLkr','monthlyRentalLkr',
                                'basePriceWithoutTaxLkr','priceLkr','price')
        if isinstance(price, dict):
            price = first_value(price,'amount','value','lkr')
        name = first_value(p,'name','packageName','planName','title')
        if not name:
            continue
        kind = package_kind(p)
        quota = first_value(p,'dataQuota','quota','quotaGb','dataGb','anytimeGb','anytimeQuotaGb','dataAllowance')
        if quota is None and isinstance(p.get('broadband'),dict):
            quota = p['broadband'].get('anytimeQuotaGb')
        item = {
            'name':str(name), 'type':kind, 'price_lkr':price,
            'quota':quota,
            'validity':first_value(p,'validity','validityDays','duration','validityPeriod'),
            'description':first_value(p,'description','details','tagline'),
            'features':first_value(p,'highlights','features','benefits') or [],
            'tax_included':first_value(p,'taxIncluded','isTaxIncluded'),
        }
        item['status'] = first_value(p,'status','availability') or 'Not specified'
        item['category'] = first_value(p,'category') or ''
        item['source_page'] = first_value(p,'sourcePage')
        key = (item['name'].lower(),kind)
        if key not in seen:
            seen.add(key)
            results.append(item)
    return results

def trio_packages(payload):
    data = knowledge_data(payload)
    trio = data.get('trio',{})
    if isinstance(trio, dict):
        packages = list_of(trio.get('packages',[]))
    else:
        packages = []
    return [{
        'name': p.get('name'), 'discontinued': p.get('isDiscontinued',False),
        'base_price_lkr': p.get('pricing',{}).get('basePriceWithoutTaxLkr'),
        'tax_lkr': p.get('pricing',{}).get('totalTaxLkr'),
        'total_price_lkr': p.get('pricing',{}).get('priceWithTaxLkr'),
        'anytime_gb': p.get('broadband',{}).get('anytimeQuotaGb'),
        'channels': p.get('peoTv',{}).get('channelCount'),
        'highlights': p.get('highlights',[]),
    } for p in packages if isinstance(p,dict)]

@app.post('/api/analyze')
async def analyze(q:Query):
    key,label = classify_intent(q.transcript)
    # The 4G prices are published from a dedicated Knowledge Hub endpoint.
    path = '/api/knowledge-hub/4g' if key == '4g' else '/api/knowledge-hub' if key == 'trio_packages' else endpoint(key)
    url = BASE + path
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            if key == '4g':
                # Fetch pricing and recharge fault procedures independently:
                # either source can still work when the other is unavailable.
                import asyncio
                requests = await asyncio.gather(
                    client.get(BASE + '/api/knowledge-hub/4g', headers={'Accept':'application/json'}),
                    client.get(BASE + '/api/knowledge-hub', headers={'Accept':'application/json'}),
                    return_exceptions=True,
                )
                pricing_data, rule_data = {}, {}
                for index, result in enumerate(requests):
                    if not isinstance(result, Exception) and result.status_code == 200:
                        try:
                            response_data = result.json()
                            if isinstance(response_data, dict) and response_data.get('success') is not False:
                                if index == 0:
                                    pricing_data = response_data
                                else:
                                    rule_data = response_data
                        except ValueError:
                            pass
                if not pricing_data and not rule_data:
                    return {'issue':label,'category':key,'source':url,'status':'unavailable',
                            'packages':[],'four_g':[],'message':'Both Knowledge Hub endpoints are unavailable.'}
                plans = four_g_packages(pricing_data)
                rules = four_g_information(rule_data)
                return {
                    'issue':label,'category':key,'source':url,
                    'status':'matched' if (plans or rules) else 'no_match',
                    'packages':plans,'four_g':rules,
                    'prepaid_packages':[p for p in plans if p['type']=='prepaid'],
                    'postpaid_packages':[p for p in plans if p['type']=='postpaid'],
                    'pricing_available':any(p['price_lkr'] is not None for p in plans),
                    'message':'4G package tariffs and service guidance from Smart Knowledge Hub.'
                    if plans else '4G tariff API has not returned packages. Recharge rules may still be available.'
                }
            response = await client.get(url, headers={'Accept':'application/json'})
            response.raise_for_status()
            payload = response.json()
        if key == 'trio_packages':
            items = trio_packages(payload)
            return {'issue':label,'category':key,'source':url,
                    'status':'matched' if items else 'no_match','packages':items,
                    'message':'Trio package prices from Knowledge Hub.' if items else 'No Trio prices available.'}
        # A collection is not a rule. Unwrap before matching operational records.
        if key in ('fiber_los','slow_internet','tt_routing'):
            records = knowledge_data(payload).get('rules',[])
            matches = select_records({'rules': records},key)
        else:
            matches = select_records(knowledge_data(payload),key)
        return {'issue':label,'category':key,'source':url,
                'status':'matched' if matches else 'no_match',
                'guidance':[format_guidance(record) for record in matches if isinstance(record,dict)],
                'message':'Matching Knowledge Hub records found.' if matches else 'No matching operational record was found.'}
    except (httpx.HTTPError,ValueError) as exc:
        return {'issue':label,'category':key,'source':url,'status':'unavailable',
                'guidance':[], 'four_g':[], 'packages':[],
                'message':'Knowledge Hub unavailable. No prices or instructions can be verified.',
                'error':type(exc).__name__}
