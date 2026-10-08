const token=document.querySelector('meta[name="trainer-token"]').content,$=id=>document.getElementById(id);
let state,selected=new Set(),page=0,initialized=false,saveChain=Promise.resolve(),languageBusy=false,refreshBusy=false;
let saveStatusKey='savedHint',languageRevision=0,appliedLanguage=null,startBusy=false;
function syncStartButton(){
 const active=!!state?.active;
 $('start').textContent=t(active?(state.removal_enabled?'startRunning':'startDiagnostic'):'start');
 $('start').disabled=startBusy||active;
 $('startHint').textContent=t(active?'startRunningHint':'startIdleHint');
}
const phobia=new Set(['c1090','c1130','c2040','c2060','c2070','c2080','c2100','c2110','c2130','c2131','c2132','c2140','c2180','c2270','c2271','c2280','c3110','c3210','c6090','c6130','c6330','c6331']);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const lang=()=>state?.language||'ko';
function t(key,args={}){return (labels[lang()][key]||key).replace(/\{(\w+)\}/g,(_,k)=>args[k]??'');}
async function api(path,body){
 let r;try{r=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:{'X-Trainer-Token':token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});}catch(e){throw Error(t('requestFailed'));}
 let data=await r.json();if(!r.ok)throw Error(data.error);return data;
}
function localize(){
 appliedLanguage=lang();
 document.documentElement.lang=lang();document.title=t('title')+' · DS3 Enemy Trainer';
 document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
 $('search').placeholder=t('search');$('search').setAttribute('aria-label',t('search'));
 $('map').setAttribute('aria-label',t('filter'));$('language').setAttribute('aria-label',t('language'));$('language').value=lang();
 const current=$('map').value;
 $('map').innerHTML=['all','loaded','selected'].map(k=>`<option value="${k}">${esc(t(k))}</option>`).join('')+`<optgroup label="${esc(t('maps'))}">`+state.maps.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('')+'</optgroup>';
 if([...$('map').options].some(o=>o.value===current))$('map').value=current;
 $('saveStatus').textContent=t(saveStatusKey);
}
function render(){
 if(!state)return;
 syncStartButton();
 $('modeAll').checked=state.removal_mode==='all';$('modePlacements').checked=state.removal_mode==='placements';
 $('modNote').hidden=!(state.mod_detected&&state.removal_mode==='all');
 let query=$('search').value.trim().toLowerCase(),mode=$('map').value;
 const mapView=state.maps.find(m=>m.id===mode);
 let rows=state.rows.filter(r=>(r.name_ko+' '+r.name_en+' '+r.id).toLowerCase().includes(query)&&($('protected').checked||r.category!=='보호 대상')&&(!$('phobia').checked||phobia.has(r.id))&&(mode!=='loaded'||state.loaded[r.id])&&(mode!=='selected'||selected.has(r.id))&&(!mapView||mapView.models[r.id])).sort((a,b)=>a.name.localeCompare(b.name,lang()));
 let pages=Math.max(1,Math.ceil(rows.length/18));page=Math.min(page,pages-1);
 $('page').textContent=`${page+1} / ${pages}`;$('result').textContent=t('count',{n:rows.length});$('prev').disabled=page===0;$('next').disabled=page===pages-1;
 $('grid').className='grid'+($('images').checked?'':' textonly');
 $('grid').innerHTML=rows.slice(page*18,(page+1)*18).map(r=>`<label class="card ${selected.has(r.id)?'selected':''} ${r.category==='보호 대상'?'locked':''}"><input type="checkbox" data-id="${esc(r.id)}" ${selected.has(r.id)?'checked':''} ${r.category==='보호 대상'?'disabled':''} aria-label="${esc(t('selectCard',{name:r.name}))}"><div class="sprite" style="background-position:${r.icon%8/7*100}% ${Math.floor(r.icon/8)/7*100}%"></div><h3>${esc(r.name)}</h3><div class="small">${r.category==='보호 대상'?esc(t('protectedCard')):esc(t('loadedCount',{n:state.loaded[r.id]||0}))}</div></label>`).join('')||`<p>${esc(t('empty'))}</p>`;
 $('grid').querySelectorAll('[data-id]').forEach(e=>e.onchange=()=>{selected.has(e.dataset.id)?selected.delete(e.dataset.id):selected.add(e.dataset.id);save();render();});
 $('chosen').textContent=t('count',{n:selected.size});$('selection').textContent=state.rows.filter(r=>selected.has(r.id)).map(r=>r.name).join(' · ');
 $('status').textContent=state.status;$('area').textContent=state.maps.find(m=>m.id===state.map)?.name||t('areaPending');
 $('completionHint').hidden=!state.removal_complete;
 $('completionHint').textContent=t('completionHint');
 $('attempts').textContent=t('attempts',{n:state.attempts,mode:t(state.active?'monitoring':'standby')});
}
function save(){
 const snapshot=[...selected];saveStatusKey='saving';$('saveStatus').textContent=t(saveStatusKey);
 saveChain=saveChain.catch(()=>{}).then(()=>api('selection',{selection:snapshot})).then(()=>{saveStatusKey='saved';$('saveStatus').textContent=t(saveStatusKey);}).catch(e=>{$('saveStatus').textContent=t('saveFailed',{error:e.message});throw e;});saveChain.catch(()=>{});
}
async function refresh(){
 if(refreshBusy||languageBusy)return;refreshBusy=true;const revision=languageRevision;
 try{const fresh=await api('state');if(revision!==languageRevision)return;state=fresh;if(!initialized){selected=new Set(state.selection);initialized=true;}if(appliedLanguage!==lang())localize();render();}catch(e){$('status').textContent=e.message;}finally{refreshBusy=false;}
}
for(const id of ['search','map','images','phobia','protected'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;render();});
$('prev').onclick=()=>{page--;render();};$('next').onclick=()=>{page++;render();};$('clear').onclick=()=>{selected.clear();save();render();};
$('language').onchange=async()=>{
 const requested=$('language').value;languageRevision++;languageBusy=true;$('language').disabled=true;
 try{await api('language',{language:requested});state=await api('state');localize();render();}
 catch(e){$('status').textContent=t('languageFailed',{error:e.message});$('language').value=lang();}
 finally{languageBusy=false;$('language').disabled=false;}
};
for(const id of ['modeAll','modePlacements'])$(id).onchange=async()=>{
 const mode=$(id).value;languageRevision++;languageBusy=true;$('modeAll').disabled=$('modePlacements').disabled=true;
 try{await api('mode',{mode});state=await api('state');render();}
 catch(e){render();$('status').textContent=e.message;}
 finally{languageBusy=false;$('modeAll').disabled=$('modePlacements').disabled=false;}
};
function confirmModWarning(){
 const dialog=$('modWarning');dialog.returnValue='cancel';
 return new Promise(resolve=>{dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true});dialog.showModal();});
}
$('modCancel').onclick=()=>$('modWarning').close('cancel');$('modContinue').onclick=()=>$('modWarning').close('confirm');
$('start').onclick=async()=>{
 if(startBusy||state?.active)return;languageRevision++;startBusy=true;syncStartButton();
 try{await saveChain;if(!$('offline').checked)throw Error(t('offlineHint'));state=await api('state');render();let ack=false;
  if($('experimental').checked&&state.mod_warning_required){ack=await confirmModWarning();if(!ack)return;}
  await api('start',{offline:$('offline').checked,experimental:$('experimental').checked,mod_warning_ack:ack});state=await api('state');render();
 }catch(e){$('status').textContent=e.message;}finally{startBusy=false;syncStartButton();}
};
$('pause').onclick=async()=>{languageRevision++;try{await api('pause',{});state=await api('state');render();}catch(e){$('status').textContent=e.message;}};
$('quit').onclick=async()=>{try{await saveChain;await api('quit',{});document.body.innerHTML=`<main><h1>${esc(t('exited'))}</h1></main>`;}catch(e){$('status').textContent=e.message;}};
refresh();setInterval(refresh,1500);
