import {Transport,validate} from './transport.js';
const $=id=>document.getElementById(id), params=new URLSearchParams(location.search);
let config,transport,runs=[],run,token=null,epoch=0;
const models=new Map(),urls=new Set(),stoppers=new Set(),channels=new Set(),cleanups=new Set();
const status=text=>{$('status').textContent=text;};
function node(tag,text){const n=document.createElement(tag);if(text)n.textContent=text;return n;}
function blobURL(data,mime){const u=URL.createObjectURL(new Blob([data],{type:mime}));urls.add(u);return u;}
function clear(){epoch++;for(const state of models.values())state.view?.dispose();models.clear();for(const stop of stoppers)stop();stoppers.clear();for(const cleanup of cleanups)cleanup();cleanups.clear();for(const url of urls)URL.revokeObjectURL(url);urls.clear();$('animations').replaceChildren();$('models').replaceChildren();$('sources').replaceChildren();}
function listen(target,type,handler){target.addEventListener(type,handler);cleanups.add(()=>target.removeEventListener(type,handler));}
function invalidate(){token=null;if(transport)transport.token=null;clear();$('content').hidden=true;for(const ch of channels)ch.close();channels.clear();}
function fail(error){status(error.message||String(error));}
async function bytes(asset,expected=epoch){const selected=run,result=await transport.asset(selected,asset);if(expected!==epoch||selected!==run||!token&&config.mode!=='demo')throw Error('The selected session or run changed.');return result;}
async function download(asset){const expected=epoch,data=await bytes(asset,expected);const link=node('a');link.href=blobURL(data,asset.mime);link.download=asset.name;link.click();}
function downloadButton(asset){const b=node('button','Download '+asset.name);b.onclick=()=>download(asset).catch(fail);return b;}
async function loadModel(state){
  if(state.view||state.loading||!run||!state.visible())return;
  state.loading=true;const expected=epoch,selected=run;status('Loading model preview…');
  try{
    const data=await bytes(state.asset,expected),{ModelView}=await import('./model.js');if(expected!==epoch)return;
    state.view=new ModelView(state.canvas,state.wrap,config);await state.view.load(data,state.asset,selected);if(expected!==epoch)return;
    state.view.active=state.visible();state.view.render();state.message.hidden=true;state.sliders.forEach(input=>{input.disabled=false;});
    status('Model ready. Viewing published revision '+selected.revision+'.');
  }catch(error){if(expected===epoch){state.view?.dispose();state.view=null;state.message.textContent=error.message+' Original-file downloads remain available.';fail(error);}}
  finally{if(expected===epoch)state.loading=false;}
}
function modelCard(asset,nested,index){
  const card=node(nested?'details':'div');card.className='model-card';
  card.append(node(nested?'summary':'p',asset.name));if(nested)card.open=index===0;
  const tools=node('div');tools.className='model-tools';const axes=node('fieldset');axes.className='axis-controls';axes.append(node('legend','Rotate model'));
  const wrap=node('div');wrap.className='canvas-wrap';const message=node('p','Expand to load the model.');message.className='model-message';const canvas=node('canvas');canvas.setAttribute('aria-label','Interactive model. Drag freely to rotate; right drag to pan; scroll to zoom.');wrap.append(message,canvas);
  const state={asset,canvas,wrap,message,sliders:[],angles:{x:0,y:0,z:0},view:null,loading:false,visible:()=>$('model-section').open&&(!nested||card.open)};
  models.set(asset.name,state);
  function resetAngles(){for(const axis of ['x','y','z'])state.angles[axis]=0;for(const input of state.sliders){input.value=0;input.nextElementSibling.value='0°';}state.view?.rotate(state.angles);}
  for(const [label,view] of [['Isometric','iso'],['Front','front'],['Top','top'],['Right','right'],['Fit / reset','fit']]){const button=node('button',label);button.dataset.view=view;button.onclick=()=>{resetAngles();state.view?.view(view);};tools.append(button);}
  for(const axis of ['x','y','z']){const label=node('label',axis.toUpperCase()),input=node('input'),value=node('output','0°');input.type='range';input.min=-180;input.max=180;input.step=1;input.value=0;input.disabled=true;input.setAttribute('aria-label',axis.toUpperCase()+' rotation');input.oninput=()=>{state.angles[axis]=Number(input.value);value.value=input.value+'°';state.view?.rotate(state.angles);};label.append(input,value);axes.append(label);state.sliders.push(input);}
  card.append(tools,axes,wrap,node('p','Drag freely to rotate · Right drag to pan · Scroll to zoom · X/Y/Z sliders rotate the model around each axis.'),downloadButton(asset));$('models').append(card);
  if(nested)listen(card,'toggle',()=>{syncModel(state);resizeHost();});
}
function syncModel(state){if(state.view){state.view.active=state.visible();state.view.render();}else loadModel(state);}
function animationCard(asset,nested){
  const parent=$('animations-section'),card=node(nested?'details':'div');card.className='asset-card';card.append(node(nested?'summary':'p',asset.name));
  const body=node('div'),message=node('p'),img=node('img');img.alt=asset.name;
  const play=node('button','Play'),stopButton=node('button','Stop');body.append(message,play,stopButton,img,downloadButton(asset));card.append(body);$('animations').append(card);
  let loaded=false,loading=false,poster=null,gif=null;const expected=epoch,selected=run;
  const visible=()=>parent.open&&(!nested||card.open),stop=()=>{if(poster)img.src=poster;else img.removeAttribute('src');};stoppers.add(stop);
  async function update(){if(!visible()){stop();return;}if(loaded||loading)return;loading=true;try{message.textContent='Loading…';const source=selected.assets.find(a=>a.name===asset.poster),data=await bytes(source,expected);if(expected!==epoch)return;poster=blobURL(data,source.mime);img.src=poster;loaded=true;message.textContent='';resizeHost();}catch(error){message.textContent=error.message;}finally{loading=false;}}
  play.onclick=async()=>{try{if(!visible())return;if(!gif)gif=blobURL(await bytes(asset,expected),'image/gif');if(expected!==epoch||!visible())return;img.src=gif;}catch(error){message.textContent=error.message;}};
  stopButton.onclick=stop;listen(parent,'toggle',update);if(nested)listen(card,'toggle',()=>{update();resizeHost();});update();
}
async function selectRun(){clear();run=runs[$('runs').selectedIndex];if(!run)return;const selected=run;
  $('metadata').textContent=`Revision ${run.revision} · ${run.publishedAt} · ${run.units} · Run ${run.runId}`;
  const gifs=run.assets.filter(a=>a.role==='animation'),previews=run.assets.filter(a=>a.role==='model');
  $('animations-label').textContent=`Animations (${gifs.length})`;$('models-label').textContent=previews.length===1?'Interactive model':`Interactive models (${previews.length})`;
  previews.forEach((asset,index)=>modelCard(asset,previews.length>1,index));gifs.forEach(asset=>animationCard(asset,gifs.length>1));if(!gifs.length)$('animations').append(node('p','No animations were generated for this run.'));
  for(const a of run.assets.filter(a=>a.role==='source'))$('sources').append(downloadButton(a));
  status('Published run ready. Expand a model to view it.');
  await Promise.all([...models.values()].map(loadModel));if(selected===run)resizeHost();
}
function resizeHost(){if(config&&window.parent!==window&&!location.pathname.endsWith('/panel'))window.parent.postMessage({type:'resizeIframe',size:Math.min(1000,Math.max(400,document.body.scrollHeight+25))},config.jamaOrigin);}
function requestToken(){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{window.removeEventListener('message',listener);reject(Error('Jama delegated session timed out. Reopen from the OSLC item view.'));},10000);function listener(e){if(e.origin===config.jamaOrigin&&e.source===window.parent&&typeof e.data?.access_token==='string'&&e.data.access_token.length>0&&e.data.access_token.length<=8192&&!/\s/.test(e.data.access_token)){clearTimeout(timer);window.removeEventListener('message',listener);resolve(e.data.access_token);}}window.addEventListener('message',listener);window.parent.postMessage({type:'oslcLoadIframe'},config.jamaOrigin);});}
function receiveHandoff(){return new Promise((resolve,reject)=>{const id=params.get('handoff');if(!/^[a-f0-9]{32}$/.test(id||''))return reject(Error('Invalid drawer handoff.'));const ch=new BroadcastChannel('jhmv-handoff-'+id);channels.add(ch);const timer=setTimeout(()=>{ch.close();channels.delete(ch);reject(Error('Drawer session handoff expired.'));},10000);ch.onmessage=e=>{if(e.data?.type==='delegated-token'&&typeof e.data.access_token==='string'&&e.data.access_token.length<=8192){clearTimeout(timer);ch.close();channels.delete(ch);resolve(e.data.access_token);}};ch.postMessage({type:'request-token'});});}
$('larger').onclick=()=>{if(!token)return;const id=Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');const ch=new BroadcastChannel('jhmv-handoff-'+id);channels.add(ch);const close=()=>{ch.close();channels.delete(ch);};ch.onmessage=e=>{if(e.data?.type==='request-token'&&token){ch.postMessage({type:'delegated-token',access_token:token});close();}};setTimeout(close,10000);const url=new URL('/spa/panel',location.origin);for(const key of ['artifact','projectId','name'])if(params.has(key))url.searchParams.set(key,params.get(key));url.searchParams.set('handoff',id);window.parent.postMessage({type:'showDUI',url:url.href,title:'Hardware Model Viewer'},config.jamaOrigin);};
$('runs').onchange=()=>selectRun().catch(fail);
$('refresh').onclick=()=>refresh().catch(fail);
$('model-section').addEventListener('toggle',()=>{for(const state of models.values())syncModel(state);resizeHost();});
$('animations-section').addEventListener('toggle',()=>{if(!$('animations-section').open)for(const stop of stoppers)stop();resizeHost();});
$('theme').onchange=()=>{const value=$('theme').value;if(value==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=value;try{localStorage.setItem('jhmv-theme',value);}catch{};};
try{const theme=localStorage.getItem('jhmv-theme');if(['system','light','dark'].includes(theme)){$('theme').value=theme;$('theme').onchange();}}catch{}
document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const stop of stoppers)stop();else for(const state of models.values())state.view?.render();});window.addEventListener('pagehide',invalidate);
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
