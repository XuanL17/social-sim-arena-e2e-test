"""Pull real questions and test free models on the isolated HTTPS entrant.
No official submissions or fabricated future scores are made.
"""
import json,sys,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ssa import agent_api,signing,bundle,ranking_round
BASE='https://social-sim-arena-e2e-test.vercel.app'
BACKEND='https://social-sim-arena-e2e-agent.vercel.app/forecast'
MODELS=['liquid/lfm-2.5-2.6b:free','nex-agi/nex-n2.5-mini:free','google/gemma-4-31b-it:free','dots-studio/dots-3-note-preview:free']
def main():
 manifest=requests.get(BASE+'/api/v1/questionnaire',timeout=30);manifest.raise_for_status();manifest=manifest.json()
 data=requests.get(BASE+'/data.json',timeout=30);data.raise_for_status();data=data.json()
 picked=[next(q for q in manifest['questions'] if q['target_type']==t) for t in ['continuous_normal','profile_energy','ranking_list']]
 env=dict(l.split('=',1) for l in (ROOT/'.local/e2e-signing.env').read_text().splitlines() if '=' in l)
 report={'run_at':datetime.now(timezone.utc).isoformat(),'caller':'local-validator-to-real-vercel-backend','manifest_url':BASE+'/api/v1/questionnaire','question_count':len(manifest['questions']),'selected_questions':picked,'attempts':[],'future_scoring':'pending real outcomes; no fabricated scores'}
 out=ROOT/'site/validation-live-free.json'
 for model in MODELS:
  for q in picked:
   raw=next(r for r in data['rounds'] if r['round_id']==q['round_id'])
   prompt=agent_api.build_envelope('e2e_remote_backend',raw)
   prompt['e2e_model']=model
   # Carry the real manifest's public reference, never a future resolution.
   prompt['round']['context']['latest_public_reference']=q['latest_public_reference']
   prompt['round']['resolution_rule']=q['resolution_rule']
   prompt['round']['release_at']=q['release_at']
   body=json.dumps(prompt,sort_keys=True,separators=(',',':')).encode()
   def post():return requests.post(BACKEND,data=body,headers={'Content-Type':'application/json',**signing.sign(env['SSA_SIGNING_KEY'],body,env['SSA_SIGNING_KEY_ID'])},timeout=(15,65))
   row={'model':model,'round_id':q['round_id'],'shape':q['target_type']};started=time.monotonic()
   try:
    r=post();row['http_status']=r.status_code;r.raise_for_status()
    if q['target_type']=='continuous_normal':answer=agent_api.parse_scalar(r.text)
    elif q['target_type']=='profile_energy':answer=agent_api.parse_profile(r.text,q['cells'])
    else:answer=agent_api.parse_ranking(r.text,ranking_round.spec_for(raw))
    row.update(forecast=r.json()['forecast'],generation_id=r.headers.get('X-OpenRouter-Generation'),cost=r.headers.get('X-OpenRouter-Cost'),backend_deployment=r.headers.get('X-E2E-Deployment'))
    assert row['generation_id'] and float(row['cost'])==0
    replay=post();assert replay.status_code==200 and replay.json()['forecast']==r.json()['forecast'] and replay.headers.get('X-E2E-Cache')=='hit'
    row['replay']='passed'
    qb=bundle.build_bundle([raw],now=datetime.now(timezone.utc));assert not bundle.check_bundle(qb)
    response={'schema_version':qb['schema_version'],'batch_id':qb['batch_id'],'entrant_id':'e2e_remote_backend','answers':[{'round_id':q['round_id'],bundle.ANSWER_KEY[q['target_type']]:answer}]}
    accepted=bundle.normalise(response,qb,now=datetime.now(timezone.utc));assert accepted['receipt']['accepted']==1
    late=bundle.normalise(response,qb,now=datetime.fromisoformat(q['deadline'].replace('Z','+00:00'))+timedelta(seconds=1));assert late['receipt']['rejected']==1
    row.update(status='passed',current_time_acceptance=accepted['receipt'],late_rejection=late['results'])
   except Exception as e:row.update(status='failed',error=type(e).__name__+': '+str(e)[:200])
   row['seconds']=round(time.monotonic()-started,2);report['attempts'].append(row)
   out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k not in ['forecast','current_time_acceptance','late_rejection']}),flush=True)
 return report
if __name__=='__main__':main()
