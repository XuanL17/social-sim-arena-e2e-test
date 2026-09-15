import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('free_ai',ROOT/'examples/remote-entrant/openrouter_ai.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Cache:
 def __init__(self):self.rows={}
 def get(self,k):return self.rows.get(k)
 def set(self,k,v,options):self.rows[k]=v
class Response:
 status_code=200
 def __init__(self,data):self.data=data
 def json(self):return self.data
 def raise_for_status(self):pass
class Session:
 def __init__(self,price='0',cost=0):self.calls=0;self.price=price;self.cost=cost
 def get(self,*a,**k):return Response({'data':[{'id':'test/model:free','pricing':{'prompt':self.price,'completion':'0'}}]})
 def post(self,*a,**k):
  self.calls+=1
  payload=k['json']
  assert payload['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0}}
  assert payload['model']=='test/model:free' and 'models' not in payload
  return Response({'id':'test-generation','model':'test/model:free','usage':{'cost':self.cost},'choices':[{'message':{'content':'{"mean":42,"sd":2}'}}]})
prompt={'schema_version':'ssa-agent-api-v2','request_id':'test:scalar','round':{'target_type':'continuous_normal'}}
with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-only-key','OPENROUTER_MODEL':'test/model:free'}):
 cache=Cache();session=Session()
 first,hit=m.infer(prompt,cache,session);assert not hit
 second,hit=m.infer(prompt,cache,session);assert hit and first==second and session.calls==1
 for price,cost in [('1',0),('0',1),('0',None)]:
  s=Session(price,cost)
  try:m.infer(prompt,Cache(),s)
  except RuntimeError:pass
  else:raise AssertionError('Nonzero or unverified pricing accepted')
  if price=='1':assert s.calls==0
with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-only-key','OPENROUTER_MODEL':'paid/model'}):
 s=Session()
 try:m.infer(prompt,Cache(),s)
 except RuntimeError:pass
 else:raise AssertionError('Paid model accepted')
 assert s.calls==0
print('passed: free-model guard, zero-price cap, no fallback, cost verification and replay cache')

ranking={'target_type':'ranking_list','ranking':{'length':2,'items':['a','b']}}
assert 'uniqueItems' not in m.forecast_schema(ranking)['properties']['ranking']
assert m.validate_forecast({'ranking':['b','a']},ranking)
try:m.validate_forecast({'ranking':['a','a']},ranking)
except ValueError:pass
else:raise AssertionError('Duplicate ranking accepted')
print('passed: provider-compatible ranking schema and local uniqueness validation')
