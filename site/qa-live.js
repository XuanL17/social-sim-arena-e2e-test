(() => {
  const base = 'https://raw.githubusercontent.com/assassin808/social-sim-arena-e2e-test/qa-results/';
  const paths = {lifecycle:'qa-lifecycle/report.json', stability:'qa-stability/latest.json'};
  const cell = (row, value) => { const td=document.createElement('td');td.textContent=String(value??'—');row.appendChild(td); };
  async function refresh(panel) {
    const channel=panel.dataset.qaLive, path=paths[channel];
    const status=panel.querySelector('[data-status]'), body=panel.querySelector('tbody');
    let data,live=true;
    try {
      const reply=await fetch(base+path+'?refresh='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if(!reply.ok)throw Error('HTTP '+reply.status);data=await reply.json();
    } catch(error) {
      live=false;
      try {const reply=await fetch('/'+path,{cache:'no-store'});if(!reply.ok)throw Error();data=await reply.json();}
      catch(_) {status.textContent='The report could not be read just now. Retrying shortly.';return;}
    }
    body.replaceChildren();
    const pub=data._publication;
    status.textContent=(live?'automatically published result':'The live result is unreadable; showing the snapshot from this deployment')+' \u00b7 run at '+(data.generated_at||data.run_at||'unknown')+(pub?' \u00b7 published '+pub.published_at:'')+' \u00b7 this page checks for updates every minute';
    const source=panel.querySelector('[data-source]');source.href=live?base+path:'/'+path;source.textContent=live?'latest machine report':'snapshot machine report';
    for(const item of (channel==='lifecycle'?data.rounds:data.models)||[]) {
      const tr=document.createElement('tr');
      if(channel==='lifecycle') [item.round_id,item.mode,item.status,item.filed_at,item.score??'pending',item.reason||''].forEach(v=>cell(tr,v));
      else [item.model,(item.initial||[]).map(r=>r.status).join(', '),item.replay_cache_hit?'passed':'failed',item.race_same_generation===false?'race produced different generations':(item.race_same_generation===true?'passed':'no race test this run')].forEach(v=>cell(tr,v));
      body.appendChild(tr);
    }
  }
  for(const panel of document.querySelectorAll('[data-qa-live]')) {
    refresh(panel);setInterval(()=>{if(!document.hidden)refresh(panel);},60000);
  }
})();
