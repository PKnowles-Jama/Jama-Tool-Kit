import {Transport,validate} from './transport.js';
const $=id=>document.getElementById(id), params=new URLSearchParams(location.search);
let config,transport,runs=[],run,model,token=null,epoch=0,modelLoading=false;
const urls=new Set(),stoppers=new Set(),channels=new Set();
const status=text=>{$('status').textContent=text;};
function node(tag,text){const n=document.createElement(tag);if(text)n.textContent=text;return n;}
function blobURL(data,mime){const u=URL.createObjectURL(new Blob([data],{type:mime}));urls.add(u);return u;}
function clear(){epoch++;model?.dispose();model=null;modelLoading=false;for(const stop of stoppers)stop();stoppers.clear();for(const url of urls)URL.revokeObjectURL(url);urls.clear();$('animations').replaceChildren();$('drawings').replaceChildren();$('sources').replaceChildren();$('model-message').textContent='Expand to load the model.';$('model-message').hidden=false;}
function invalidate(){token=null;if(transport)transport.token=null;clear();$('content').hidden=true;for(const ch of channels)ch.close();channels.clear();}
function fail(error){status(error.message||String(error));}
async function bytes(asset,expected=epoch){const selected=run,result=await transport.asset(selected,asset);if(expected!==epoch||selected!==run||!token&&config.mode!=='demo')throw Error('The selected session or run changed.');return result;}
async function download(asset){const expected=epoch,data=await bytes(asset,expected);const link=node('a');link.href=blobURL(data,asset.mime);link.download=asset.name;link.click();}
function downloadButton(asset){const b=node('button','Download '+asset.name);b.onclick=()=>download(asset).catch(fail);return b;}
async function loadModel(){if(model||modelLoading||!run||!$('model-section').open)return;modelLoading=true;const expected=epoch,selected=run;status('Loading model preview…');try{
  const asset=selected.assets.find(a=>a.role==='model'),data=await bytes(asset,expected);const {ModelView}=await import('./model.js');if(expected!==epoch)return;
  const candidate=new ModelView($('canvas'),$('canvas-wrap'),config);model=candidate;await candidate.load(data,asset,selected);if(expected!==epoch)return;$('model-message').hidden=true;status('Model ready. Viewing published revision '+selected.revision+'.');
}catch(error){if(expected===epoch){model?.dispose();model=null;$('model-message').textContent=error.message+' Original-file downloads remain available.';fail(error);}}finally{if(expected===epoch)modelLoading=false;}}
function imageCard(asset,container,isGIF=false){
  const card=node('details');card.className='asset-card';card.append(node('summary',asset.name));const body=node('div'),message=node('p'),img=node('img');img.alt=asset.name;
  body.append(message);card.append(body);container.append(card);let loaded=false,playing=false,poster=null,gif=null;
  const expected=epoch,selected=run;
  const stop=()=>{playing=false;if(poster)img.src=poster;else img.removeAttribute('src');};stoppers.add(stop);
  if(isGIF){const play=node('button','Play'),pause=node('button','Stop');body.append(play,pause,img);play.onclick=async()=>{try{if(!card.open)return;if(!gif)gif=blobURL(await bytes(asset,expected),'image/gif');if(expected!==epoch||!card.open)return;img.src=gif;playing=true;}catch(e){message.textContent=e.message;}};pause.onclick=stop;}
  else {
    const tools=node('div'),viewport=node('div');viewport.className='drawing-viewport';let scale=1;
    const zoom=(factor)=>{scale=Math.max(.2,Math.min(6,factor));img.style.width=(scale*100)+'%';img.style.height='auto';};
    for(const [label,factor] of [['Zoom in',1.25],['Zoom out',.8],['Fit',0]]){const b=node('button',label);b.onclick=()=>zoom(factor?scale*factor:1);tools.append(b);}body.append(tools,viewport);viewport.append(img);
    let drag;img.ondragstart=()=>false;viewport.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);};viewport.onpointermove=e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}};viewport.onpointerup=viewport.onpointercancel=()=>{drag=null;};
  }
  body.append(downloadButton(asset));
  card.addEventListener('toggle',async()=>{if(!card.open){if(isGIF)stop();return;}if(loaded)return;try{message.textContent='Loading…';const source=isGIF?selected.assets.find(a=>a.name===asset.poster):asset;const data=await bytes(source,expected);if(expected!==epoch)return;poster=blobURL(data,source.mime);img.src=poster;loaded=true;message.textContent='';}catch(e){message.textContent=e.message;}});
}
async function selectRun(){clear();run=runs[$('runs').selectedIndex];if(!run)return;const selected=run;
  $('metadata').textContent=`Revision ${run.revision} · ${run.publishedAt} · ${run.units} · Run ${run.runId}`;
  const gifs=run.assets.filter(a=>a.role==='animation'),drawings=run.assets.filter(a=>a.role==='drawing');
  $('animations-label').textContent=`Animations (${gifs.length})`;$('drawings-label').textContent=`Drawings (${drawings.length})`;
  for(const a of gifs)imageCard(a,$('animations'),true);if(!gifs.length)$('animations').append(node('p','No animations were generated for this run.'));
  for(const a of drawings)imageCard(a,$('drawings'));if(!drawings.length)$('drawings').append(node('p','No drawings were published for this run.'));
  $('drawings').prepend(node('p',`${run.projection} · ${run.drawingKind}`));
  for(const a of run.assets.filter(a=>['source','model'].includes(a.role)))$('sources').append(downloadButton(a));
  for(const a of run.assets.filter(a=>a.role==='document'))$('drawings').append(downloadButton(a));
  await loadModel();if(selected===run)resizeHost();
}
function resizeHost(){if(config&&window.parent!==window&&!location.pathname.endsWith('/panel'))window.parent.postMessage({type:'resizeIframe',size:Math.min(1000,Math.max(400,document.body.scrollHeight+25))},config.jamaOrigin);}
function requestToken(){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{window.removeEventListener('message',listener);reject(Error('Jama delegated session timed out. Reopen from the OSLC item view.'));},10000);function listener(e){if(e.origin===config.jamaOrigin&&e.source===window.parent&&typeof e.data?.access_token==='string'&&e.data.access_token.length>0&&e.data.access_token.length<=8192&&!/\s/.test(e.data.access_token)){clearTimeout(timer);window.removeEventListener('message',listener);resolve(e.data.access_token);}}window.addEventListener('message',listener);window.parent.postMessage({type:'oslcLoadIframe'},config.jamaOrigin);});}
function receiveHandoff(){return new Promise((resolve,reject)=>{const id=params.get('handoff');if(!/^[a-f0-9]{32}$/.test(id||''))return reject(Error('Invalid drawer handoff.'));const ch=new BroadcastChannel('jhmv-handoff-'+id);channels.add(ch);const timer=setTimeout(()=>{ch.close();channels.delete(ch);reject(Error('Drawer session handoff expired.'));},10000);ch.onmessage=e=>{if(e.data?.type==='delegated-token'&&typeof e.data.access_token==='string'&&e.data.access_token.length<=8192){clearTimeout(timer);ch.close();channels.delete(ch);resolve(e.data.access_token);}};ch.postMessage({type:'request-token'});});}
$('larger').onclick=()=>{if(!token)return;const id=Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');const ch=new BroadcastChannel('jhmv-handoff-'+id);channels.add(ch);const close=()=>{ch.close();channels.delete(ch);};ch.onmessage=e=>{if(e.data?.type==='request-token'&&token){ch.postMessage({type:'delegated-token',access_token:token});close();}};setTimeout(close,10000);const url=new URL('/spa/panel',location.origin);for(const key of ['artifact','projectId','name'])if(params.has(key))url.searchParams.set(key,params.get(key));url.searchParams.set('handoff',id);window.parent.postMessage({type:'showDUI',url:url.href,title:'Hardware Model Viewer'},config.jamaOrigin);};
$('runs').onchange=()=>selectRun().catch(fail);
$('refresh').onclick=()=>refresh().catch(fail);
$('model-section').addEventListener('toggle',()=>{if(model){model.active=$('model-section').open;model.render();}else loadModel();resizeHost();});
for(const id of ['animations-section','drawings-section'])$(id).addEventListener('toggle',()=>{if(!$(id).open&&id==='animations-section')for(const stop of stoppers)stop();resizeHost();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>model?.view(b.dataset.view));
$('sheet').onclick=async()=>{if(!model)return;const expected=epoch,blob=await model.sheet();if(expected!==epoch)return;const link=node('a');link.href=blobURL(await blob.arrayBuffer(),'image/png');link.download='four-view-undimensioned.png';link.click();};
$('theme').onchange=()=>{const value=$('theme').value;if(value==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=value;try{localStorage.setItem('jhmv-theme',value);}catch{};};
try{const theme=localStorage.getItem('jhmv-theme');if(['system','light','dark'].includes(theme)){$('theme').value=theme;$('theme').onchange();}}catch{}
document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const stop of stoppers)stop();else model?.render();});window.addEventListener('pagehide',invalidate);
async function refresh(){clear();$('content').hidden=true;if(!token&&config.mode!=='demo')throw Error('Reopen this tool from Jama to authenticate.');status('Reading published runs…');const data=await transport.contextData();runs=data.runs;runs.forEach(m=>validate(m,config,transport.context));$('title').textContent=`${data.item.documentKey} — ${data.item.name}`;$('runs').replaceChildren(...runs.map(m=>node('option',`${m.revision} · ${m.publishedAt}`)));if(!runs.length){status('No complete viewer run is published on this item. Complete REQHW step 7.');return;}$('content').hidden=false;await selectRun();}
async function start(){
  config=await (await fetch('/viewer-config.json',{cache:'no-store'})).json();
  if(params.get('demo')==='1'){
    const manifest=await (await fetch('/demo/manifest.json')).json();config={...config,mode:'demo'};transport={context: {projectId:53,itemId:1},contextData:async()=>({item:{documentKey:'DEMO',name:'Synthetic bracket assembly'},runs:[manifest]}),asset:async(m,a)=>new Uint8Array(await (await fetch('/demo/'+a.name)).arrayBuffer())};$('larger').hidden=true;status('Synthetic local demonstration. No Jama connection.');await refresh();return;
  }
  for(const key of params.keys())if(!['artifact','projectId','name','handoff'].includes(key)||params.getAll(key).length!==1)throw Error('Unsupported or duplicate launcher parameter.');
  const artifact=new URL(params.get('artifact'));if(artifact.origin!==config.jamaOrigin||artifact.username||artifact.password||artifact.protocol!=='https:')throw Error('Jama artifact origin is not configured.');
  const match=(artifact.pathname+'/'+artifact.hash).match(/(?:^|\/)(?:items|testCases)\/(\d+)(?:\/|$)/);const projectId=Number(params.get('projectId'));
  if(!match||!Number.isSafeInteger(projectId)||!config.allowedProjectIds.includes(projectId))throw Error('Unsupported Jama item or project.');
  token=location.pathname.endsWith('/panel')?await receiveHandoff():await requestToken();
  transport=new Transport(config,token,{projectId,itemId:Number(match[1])},invalidate);$('larger').hidden=location.pathname.endsWith('/panel');await refresh();
}
start().catch(fail);
