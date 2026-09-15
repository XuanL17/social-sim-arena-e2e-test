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
      catch(_) {status.textContent='暂时无法读取报告，请稍后重试。';return;}
    }
    body.replaceChildren();
    const pub=data._publication;
    status.textContent=(live?'自动发布结果':'自动结果暂不可读，显示本次部署的旧快照')+' · 测试时间：'+(data.generated_at||data.run_at||'未知')+(pub?' · 发布时间：'+pub.published_at:'')+' · 页面每分钟检查更新';
    const source=panel.querySelector('[data-source]');source.href=live?base+path:'/'+path;source.textContent=live?'最新机器报告':'快照机器报告';
    for(const item of (channel==='lifecycle'?data.rounds:data.models)||[]) {
      const tr=document.createElement('tr');
      if(channel==='lifecycle') [item.round_id,item.mode,item.status,item.filed_at,item.score??'pending',item.reason||''].forEach(v=>cell(tr,v));
      else [item.model,(item.initial||[]).map(r=>r.status).join(', '),item.replay_cache_hit?'通过':'未通过',item.race_same_generation===false?'并发生成不一致':(item.race_same_generation===true?'通过':'本轮未测并发')].forEach(v=>cell(tr,v));
      body.appendChild(tr);
    }
  }
  for(const panel of document.querySelectorAll('[data-qa-live]')) {
    refresh(panel);setInterval(()=>{if(!document.hidden)refresh(panel);},60000);
  }
})();
