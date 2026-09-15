"""Audit downloaded public artifacts without refreshing or filing forecasts."""
import json,sys,math
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ssa import scoring
p=ROOT/'.local';d=json.loads((p/'validation-data.json').read_text());m=json.loads((p/'validation-manifest.json').read_text());up=json.loads((p/'validation-upstream_questions.json').read_text())
now=datetime.fromisoformat(m['generated_at'].replace('Z','+00:00'));lookup={r['round_id']:r for r in d['rounds']};up_lookup={r['round_id']:r for r in up['rounds']}
rows=[];checks=0;mismatches=[]
for q in m['questions']:
 r=lookup[q['round_id']];published=r.get('published_at');rows.append({'round_id':q['round_id'],'published_at':published,'deadline':q['deadline'],'not_yet_published':bool(published and datetime.fromisoformat(published.replace('Z','+00:00'))>now),'source_url_missing':not q.get('resolution_source_url'),'upstream_wording_matches':q['question']==up_lookup.get(q['round_id'],{}).get('question')})
for r in d['rounds']:
 if r.get('target_type','continuous_normal')!='continuous_normal' or r.get('status')!='resolved':continue
 y=r.get('resolution',{}).get('value')
 if not isinstance(y,(int,float)):continue
 for entrant,f in r.get('forecasts',{}).items():
  s=r.get('scores',{}).get(entrant,{}).get('crps')
  if s is None or not all(k in f for k in ['mean','sd']):continue
  record=ROOT/'forecasts'/r['round_id']/(entrant+'.json')
  full=json.loads(record.read_text()).get('topline',f) if record.exists() else f
  expected=scoring.crps_forecast(full,y);checks+=1
  if abs(expected-s)>0.00011:mismatches.append({'round_id':r['round_id'],'entrant':entrant,'published':s,'recomputed':expected})
report={'at':m['generated_at'],'snapshot_generated_at':d['generated_at'],'manifest_count':len(rows),'upstream_question_count':len(up['rounds']),'not_yet_published_count':sum(r['not_yet_published'] for r in rows),'missing_source_url_count':sum(r['source_url_missing'] for r in rows),'wording_matches_upstream_count':sum(r['upstream_wording_matches'] for r in rows),'scalar_score_recomputations':checks,'scalar_score_mismatches':mismatches,'source_health':d['source_health'],'questions':rows}
(ROOT/'site/validation-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ['questions','source_health']})
