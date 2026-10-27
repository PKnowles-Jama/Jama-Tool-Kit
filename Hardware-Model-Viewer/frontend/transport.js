// Static mode deliberately implements the same bounded read contract as the adapter.
export class Transport {
  constructor(config, token, context, invalidate) { Object.assign(this, {config,token,context,invalidate}); }
  async fetchBytes(url, options={}, bound=this.config.maxManifestBytes) {
    const response=await fetch(url,{...options,redirect:'error',credentials:'omit',cache:'no-store',headers:{...options.headers,Authorization:`Bearer ${this.token}`}});
    if([401,403].includes(response.status)){this.invalidate();throw Error('Jama access expired or denied. Reopen this tool from Jama.');}
    if(!response.ok)throw Error(`Read failed (HTTP ${response.status}).`);
    const reader=response.body.getReader();let size=0;const chunks=[];
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>bound)throw Error('Response exceeds configured size limit.');chunks.push(value);}}catch(e){await reader.cancel();throw e;}
    const result=new Uint8Array(size);let offset=0;for(const c of chunks){result.set(c,offset);offset+=c.length;}return result;
  }
  async restPage(path,params={}){const u=new URL(this.config.apiRoot+path,this.config.jamaOrigin);Object.entries(params).forEach(([k,v])=>u.searchParams.set(k,v));return JSON.parse(new TextDecoder().decode(await this.fetchBytes(u)));}
  async rest(path,params={}){return (await this.restPage(path,params)).data;}
  async post(path,payload,bound){return this.fetchBytes(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...this.context,...payload})},bound);}
  async attachments(){let rows=[],start=0;while(true){const page=await this.restPage(`/items/${this.context.itemId}/attachments`,{startAt:start,maxResults:50}),batch=page.data;if(!Array.isArray(batch))throw Error('Invalid attachment inventory.');rows.push(...batch);if(rows.length>this.config.maxAttachments)throw Error('Too many attachments.');if(!batch.length)return rows;const info=page.meta?.pageInfo;if(info?.startIndex!==undefined&&info.startIndex!==start)throw Error('Unexpected attachment page offset.');start+=batch.length;if(info?.totalResults!==undefined&&start>=info.totalResults)return rows;}}
  async file(meta,bound){if(meta.project!==this.context.projectId||!Number.isInteger(meta.fields.attachment)||meta.fileSize>bound)throw Error('Attachment binding or size differs.');const url=`${this.config.jamaOrigin}/attachment/${meta.fields.attachment}/${encodeURIComponent(meta.fileName)}`;const endpoint=new URL(this.config.apiRoot+'/files',this.config.jamaOrigin);endpoint.searchParams.set('url',url);return this.fetchBytes(endpoint,{},bound);}
  async contextData(){
    if(this.config.mode==='adapter')return JSON.parse(new TextDecoder().decode(await this.post('/api/context',{},8*1024*1024)));
    const item=await this.rest(`/items/${this.context.itemId}`);if(item.project!==this.context.projectId)throw Error('Selected item is in a different project.');
    const attachments=await this.attachments(), linked=new Set(attachments.map(a=>a.id));
    const candidates=attachments.filter(a=>a.fields?.name?.startsWith('JHMV manifest v1 '));if(candidates.length>30)throw Error('Archive older manifest associations; at most 30 runs are supported.');const runs=[];
    for(const candidate of candidates){const meta=await this.rest(`/attachments/${candidate.id}`);const m=JSON.parse(new TextDecoder().decode(await this.file(meta,this.config.maxManifestBytes)));validate(m,this.config,this.context);if(meta.fields.name!=='JHMV manifest v1 '+m.runId||!m.assets.every(a=>linked.has(a.attachmentId)))throw Error('Manifest association differs.');runs.push(m);}
    runs.sort((a,b)=>b.publishedAt.localeCompare(a.publishedAt)||b.runId.localeCompare(a.runId));return {item:{id:item.id,name:item.fields.name,documentKey:item.documentKey||String(item.id)},runs};
  }
  async asset(run,asset){let data;if(this.config.mode==='adapter')data=await this.post('/api/asset',{runId:run.runId,name:asset.name},Math.min(asset.bytes,this.config.maxFileBytes));else{
    // Revalidate permissions and current attachment association for every read.
    const item=await this.rest(`/items/${this.context.itemId}`), attached=await this.attachments();if(item.project!==this.context.projectId||!attached.some(a=>a.id===asset.attachmentId))throw Error('Artifact is no longer associated with the selected item.');
    const meta=await this.rest(`/attachments/${asset.attachmentId}`);if(meta.fileName!==asset.name||meta.fields.attachment!==asset.fileId)throw Error('Artifact identity differs.');data=await this.file(meta,Math.min(asset.bytes,this.config.maxFileBytes));}
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),x=>x.toString(16).padStart(2,'0')).join('');if(data.length!==asset.bytes||hash!==asset.sha256)throw Error('Published artifact has changed.');return data;
  }
}
export function validate(m,c,ctx){
  if(m.schemaVersion!==1||m.status!=='complete'||typeof m.runId!=='string'||!/^[-0-9a-f]{36}$/.test(m.runId)||!Number.isFinite(Date.parse(m.publishedAt)))throw Error('Unsupported or incomplete manifest.');
  const b=m.binding;if(b.jamaOrigin!==c.jamaOrigin||b.projectId!==ctx.projectId||b.itemId!==ctx.itemId||b.summaryId!==ctx.itemId)throw Error('Manifest belongs to a different Jama item.');
  if(!['Y','Z'].includes(m.upAxis)||!['mm','cm','m','in','ft'].includes(m.units)||!Array.isArray(m.assets)||!m.assets.length||m.assets.length>100)throw Error('Invalid model metadata.');
  const names=new Set(),ids=new Set();for(const a of m.assets){if(typeof a.name!=='string'||!a.name||/[\\/:]/.test(a.name)||names.has(a.name)||!Number.isInteger(a.attachmentId)||a.attachmentId<1||ids.has(a.attachmentId)||!Number.isInteger(a.fileId)||a.fileId<1||!Number.isInteger(a.bytes)||a.bytes<1||a.bytes>c.maxFileBytes||!/^[0-9a-f]{64}$/.test(a.sha256)||!['model','source','animation','poster','drawing','document'].includes(a.role))throw Error('Invalid artifact metadata.');names.add(a.name);ids.add(a.attachmentId);}
  if(m.assets.filter(a=>a.role==='model').length!==1)throw Error('Expected one model preview.');
  for(const a of m.assets){if(a.role==='model'&&!/\.(glb|3mf)$/i.test(a.name))throw Error('Unsupported model preview.');if(['drawing','poster'].includes(a.role)&&!['image/png','image/jpeg'].includes(a.mime))throw Error('Unsafe image format.');if(a.role==='animation'&&(a.mime!=='image/gif'||!m.assets.some(p=>p.name===a.poster&&p.role==='poster')))throw Error('Animation poster is missing.');}
}
