"""Real OpenRouter inference, restricted to an explicitly free model."""
import hashlib
import json
import math
import os
import requests

BASE = 'https://openrouter.ai/api/v1'
TEST_MODELS = {'liquid/lfm-2.5-2.6b:free', 'nex-agi/nex-n2.5-mini:free', 'google/gemma-4-31b-it:free', 'dots-studio/dots-3-note-preview:free'}


def validate_forecast(fc, round_spec):
    def normal(value):
        if not isinstance(value, dict) or set(value) != {'mean', 'sd'}:
            raise ValueError('Expected mean and sd')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value.values()) or value['sd'] <= 0:
            raise ValueError('Invalid normal distribution')
    if not isinstance(fc, dict):
        raise ValueError('Forecast must be an object')
    kind = round_spec['target_type']
    if kind == 'continuous_normal':
        normal(fc)
    elif kind == 'profile_energy':
        if set(fc) != {'profile'} or not isinstance(fc['profile'], dict) or set(fc['profile']) != set(round_spec['cells']):
            raise ValueError('Profile cells must match exactly')
        for value in fc['profile'].values(): normal(value)
    elif kind == 'ranking_list':
        items = fc.get('ranking')
        if set(fc) != {'ranking'} or not isinstance(items, list) or any(not isinstance(i, str) for i in items) or len(set(items)) != len(items) or len(items) != round_spec['ranking']['length']:
            raise ValueError('Invalid ranking')
        declared = round_spec['ranking'].get('items')
        if declared and set(items) != set(declared): raise ValueError('Ranking items must match')
    else:
        raise ValueError('Unsupported target_type')
    return fc


def forecast_schema(r):
    normal = {'type':'object','properties':{'mean':{'type':'number'},'sd':{'type':'number','exclusiveMinimum':0}},'required':['mean','sd'],'additionalProperties':False}
    kind = r['target_type']
    if kind == 'continuous_normal': return normal
    if kind == 'profile_energy':
        cells = r['cells']
        return {'type':'object','properties':{'profile':{'type':'object','properties':{c:normal for c in cells},'required':cells,'additionalProperties':False}},'required':['profile'],'additionalProperties':False}
    if kind == 'ranking_list':
        spec = r['ranking'];item = {'type':'string'}
        if spec.get('items'):item['enum']=spec['items']
        return {'type':'object','properties':{'ranking':{'type':'array','items':item,'minItems':spec['length'],'maxItems':spec['length']}},'required':['ranking'],'additionalProperties':False}
    raise ValueError('Unsupported target_type')


def infer(prompt, cache=None, session=None):
    model = prompt.get('e2e_model', os.environ.get('OPENROUTER_MODEL', ''))
    if 'e2e_model' in prompt and model not in TEST_MODELS:
        raise ValueError('Unsupported test model')
    key = os.environ.get('OPENROUTER_API_KEY', '')
    if not model.endswith(':free') or not key:
        raise RuntimeError('A :free model and OpenRouter key must be configured')
    if cache is None:
        from vercel.functions import RuntimeCache
        cache = RuntimeCache(namespace='ssa-openrouter-free-v2')
    session = session or requests
    cache_key = hashlib.sha256(json.dumps([model, prompt],sort_keys=True,separators=(',', ':')).encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        validate_forecast(cached['forecast'], prompt['round'])
        return cached, True
    catalog = session.get(BASE+'/models',timeout=15)
    catalog.raise_for_status()
    entry = next((m for m in catalog.json()['data'] if m['id']==model), None)
    if entry is None or any(float(entry['pricing'].get(k, '0')) != 0 for k in ('prompt','completion','request')):
        raise RuntimeError('Configured model is not currently zero-priced')
    instruction = ('You are a forecast entrant. Return ONLY a JSON object, no markdown. '
        'For continuous_normal return {"mean": number, "sd": positive number}. '
        'For profile_energy return {"profile": {cell_name: {"mean": number, "sd": positive number}}} '
        'with exactly all the provided cells. For ranking_list return {"ranking": [item_names]} '
        'with exactly the requested number of distinct items, using every declared item if a basket is provided. '
        'Use the question and supplied context; do not claim to know future results.')
    payload = {'model':model,'messages':[{'role':'system','content':instruction},
        {'role':'user','content':json.dumps(prompt['round'],sort_keys=True)}],
        'temperature':0,'max_tokens':4096,
        'response_format':{'type':'json_schema','json_schema':{'name':'forecast','strict':True,'schema':forecast_schema(prompt['round'])}},
        'provider':{'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0}}}
    response = session.post(BASE+'/chat/completions',headers={'Authorization':'Bearer '+key,
        'HTTP-Referer':'https://social-sim-arena-e2e-agent.vercel.app','X-Title':'SSA isolated E2E free entrant'},json=payload,timeout=(10,45))
    if response.status_code != 200:
        raise RuntimeError(f'OpenRouter HTTP {response.status_code}; no paid fallback')
    data = response.json()
    if 'error' in data: raise RuntimeError('OpenRouter generation failed; no fallback')
    text = data['choices'][0]['message']['content']
    fc = validate_forecast(json.loads(text),prompt['round'])
    cost = data.get('usage', {}).get('cost')
    if cost is None or float(cost) != 0:
        raise RuntimeError('OpenRouter did not confirm zero generation cost')
    result = {'forecast':fc,'model':data.get('model',model),'requested_model':model,
              'generation_id':data['id'],'cost':cost,'usage':data.get('usage',{})}
    cache.set(cache_key,result,{'ttl':86400})
    return result, False
