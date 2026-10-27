"""Mocked Jama host qualification: real browser messaging and both transports."""
import copy
import hashlib
import json
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.test-deps'),str(ROOT/'src')]
from playwright.sync_api import sync_playwright,expect
from jama_model_viewer.core import read_json

config=read_json(ROOT/'config/viewer.example.json')
config.update(jamaOrigin='https://jama.test',publicOrigin='https://viewer.test')
base=read_json(ROOT/'frontend/demo/manifest.json')
base['binding']={'jamaOrigin':config['jamaOrigin'],'projectId':53,'itemId':100,'summaryId':100}
fixture_token='synthetic-test-session'
host='''<!doctype html><html><body><iframe id="tool" width="1100" height="900" src="https://viewer.test/spa?artifact=https%3A%2F%2Fjama.test%2Fitems%2F100&projectId=53"></iframe><script>
window.addEventListener('message',e=>{if(e.origin!=='https://viewer.test')return;if(e.data.type==='oslcLoadIframe')e.source.postMessage({access_token:'synthetic-test-session'},e.origin);if(e.data.type==='showDUI'){const f=document.createElement('iframe');f.id='drawer';f.src=e.data.url;f.width='1100';f.height='900';document.body.append(f);}});
</script></body></html>'''

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for mode,format in (('adapter','glb'),('static','glb'),('adapter','3mf')):
        c=browser.new_context(viewport={'width':1200,'height':1000})
        state={'expire':False,'reads':0,'requests':[]}
        manifest=copy.deepcopy(base)
        # Test a real STEP-derived assembly in the authenticated adapter path.
        rocket=ROOT/'tests/output/rocket-preview.glb'
        if mode=='adapter' and rocket.exists():
            a=manifest['assets'][0];data=rocket.read_bytes();a.update(name='rocket-preview.glb',bytes=len(data),sha256=hashlib.sha256(data).hexdigest());manifest['revision']='Rocket STEP preview test'
        if format=='3mf':
            a=manifest['assets'][0];data=(ROOT/'frontend/demo/demo.3mf').read_bytes();a.update(name='demo.3mf',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mime='model/3mf');manifest.update(revision='Synthetic 3MF test',units='mm')
        blobs={a['name']: (rocket.read_bytes() if a['name']=='rocket-preview.glb' else (ROOT/'frontend/demo'/a['name']).read_bytes()) for a in manifest['assets']}
        manifest_name='jhmv-'+manifest['runId']+'.json'
        blobs[manifest_name]=json.dumps(manifest).encode()
        metadata={a['attachmentId']:{'id':a['attachmentId'],'project':53,'fileName':a['name'],'fileSize':a['bytes'],'fields':{'attachment':a['fileId'],'name':'JHMV asset'}} for a in manifest['assets']}
        metadata[10]={'id':10,'project':53,'fileName':manifest_name,'fileSize':len(blobs[manifest_name]),'fields':{'attachment':10,'name':'JHMV manifest v1 '+manifest['runId']}}
        def handle(route):
            request=route.request;u=urlsplit(request.url);path=u.path
            headers={'Access-Control-Allow-Origin':'https://viewer.test','Access-Control-Allow-Headers':'authorization','Access-Control-Allow-Methods':'GET, OPTIONS'}
            def send(body, mime='application/json',status=200):
                if isinstance(body,(dict,list)):body=json.dumps(body)
                route.fulfill(status=status,body=body,content_type=mime,headers=headers)
            if request.method=='OPTIONS':return send('')
            if u.netloc=='jama.test' and path=='/host':return send(host,'text/html')
            if u.netloc=='viewer.test' and path=='/viewer-config.json':return send({**config,'mode':mode})
            protected=(u.netloc=='jama.test' and path.startswith('/rest/')) or path.startswith('/api/')
            if protected:
                assert request.headers.get('authorization')=='Bearer '+fixture_token
                state['reads']+=1
                if state['expire']:return send({'error':'Session expired'},status=401)
                if path=='/api/context':return send({'item':{'id':100,'name':'Summary','documentKey':'REQHW-SUM-TEST'},'runs':[manifest]})
                if path=='/api/asset':
                    body=request.post_data_json;assert body['projectId']==53 and body['itemId']==100 and body['runId']==manifest['runId'];return send(blobs[body['name']],'application/octet-stream')
                if path=='/rest/v1/items/100':return send({'data':{'id':100,'project':53,'documentKey':'REQHW-SUM-TEST','fields':{'name':'Summary'}}})
                if path=='/rest/v1/items/100/attachments':return send({'data':list(metadata.values()) if parse_qs(u.query).get('startAt',['0'])[0]=='0' else []})
                if path.startswith('/rest/v1/attachments/'):return send({'data':metadata[int(path.rsplit('/',1)[1])]})
                if path=='/rest/v1/files':
                    name=unquote(urlsplit(parse_qs(u.query)['url'][0]).path.rsplit('/',1)[1]);return send(blobs[name],'application/octet-stream')
            if u.netloc=='viewer.test':
                name='index.html' if path in ('/spa','/spa/panel') else path.lstrip('/')
                file=(ROOT/'frontend'/name).resolve()
                if file.is_relative_to((ROOT/'frontend').resolve()) and file.is_file():return send(file.read_bytes(),{'.js':'text/javascript'}.get(file.suffix,mimetypes.guess_type(file)[0] or 'application/octet-stream'))
            state['requests'].append(request.url);route.abort()
        c.route('**/*',handle)
        page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('https://jama.test/host')
        frame=page.frame_locator('#tool')
        expect(frame.locator('#status')).to_have_text(re.compile('^Model ready'),timeout=30000)
        page.screenshot(path=str(ROOT/'tests/output'/f'integration-{mode}-{format}.png'),full_page=True)
        frame.get_by_role('button',name='Open larger view').click()
        drawer=page.frame_locator('#drawer')
        expect(drawer.locator('#status')).to_have_text(re.compile('^Model ready'),timeout=30000)
        assert not drawer.get_by_role('button',name='Open larger view').is_visible()
        state['expire']=True
        frame.get_by_role('button',name='Refresh',exact=True).click()
        expect(frame.locator('#content')).to_be_hidden()
        expect(frame.locator('#status')).to_have_text(re.compile('expired|denied',re.I))
        assert not errors,errors
        assert not state['requests'],state['requests']
        print(mode+' '+format+': host handshake, authenticated rendering, native drawer handoff and session expiry passed.')
        c.close()
    browser.close()
