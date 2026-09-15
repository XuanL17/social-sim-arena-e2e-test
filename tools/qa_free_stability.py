"""Bounded live free-model probe; no private LLM key, retries or paid fallback."""
import argparse,json,sys,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ssa import signing
MODELS=['liquid/lfm-2.5-2.6b:free','nex-agi/nex-n2.5-mini:free','google/gemma-4-31b-it:free','dots-studio/dots-3-note-preview:free']
ENDPOINT='https://social-sim-arena-e2e-agent.vercel.app/forecast'
def probe(body):
 started=time.monotonic()
 try:
  r=requests.post(ENDPOINT,data=body,headers={'Content-Type':'application/json',**signing.sign(signing.TEST_PRIVATE_KEY,body,signing.TEST_KEY_ID)},timeout=(10,65),allow_redirects=False)
  row={'status':r.status_code,'seconds':round(time.monotonic()-started,3),'generation':r.headers.get('X-OpenRouter-Generation'),'cost':r.headers.get('X-OpenRouter-Cost'),'cache':r.headers.get('X-E2E-Cache')}
  if r.status_code==200:
   fc=r.json()['forecast'];assert isinstance(fc['mean'],(int,float)) and not isinstance(fc['mean'],bool) and fc['sd']>0
   assert row['generation'] and float(row['cost'])==0
   row['forecast']=fc
  return row
 except Exception as e:return {'status':'error','error':type(e).__name__,'seconds':round(time.monotonic()-started,3)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--race',action='store_true');ap.add_argument('--out',default='qa-stability');args=ap.parse_args()
 now=datetime.now(timezone.utc);runid=now.strftime('%Y%m%dT%H%M%SZ');rows=[]
 for model in MODELS:
  prompt={'schema_version':'ssa-agent-api-v2','request_id':'qa-stability:'+runid+':'+model,'e2e_model':model,'round':{'round_id':'qa-stability','target_type':'continuous_normal','question':'Non-scored reliability test: return a normal forecast with mean 50 and positive sd.','unit':'points','lock_at':'2099-01-01T00:00:00Z','context':{'persistence':50}}}
  body=json.dumps(prompt,sort_keys=True,separators=(',',':')).encode()
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:probe(body),range(2 if args.race else 1)))
  replay=probe(body) if any(r['status']==200 for r in results) else None
  successes=[r for r in results if r['status']==200]
  row={'model':model,'initial':results,'replay':replay,'initial_all_passed':len(successes)==len(results),'race_same_generation':len({r.get('generation') for r in successes})==1 if args.race and len(successes)==2 else None,'replay_cache_hit':bool(replay and replay['status']==200 and replay['cache']=='hit')};rows.append(row);print(json.dumps(row),flush=True)
 report={'run_at':now.isoformat(),'endpoint':ENDPOINT,'mode':'concurrent-identical-miss' if args.race else 'scheduled-fresh-request','models':rows,'limitations':'A single run is not long-term reliability evidence. Failures retained. Runtime Cache is not a distributed lock.'}
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 for name in [runid+'.json','latest.json']:(out/name).write_text(json.dumps(report,indent=2)+'\n')
 return 0 if all(r['initial_all_passed'] and r['replay_cache_hit'] and (not args.race or r['race_same_generation']) for r in rows) else 1
if __name__=='__main__':sys.exit(main())
