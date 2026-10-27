"""Apply the authorized step-7 addition; preserve the live original HTML verbatim."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from jama_model_viewer.jama_rest import Jama,connection_arguments

p=argparse.ArgumentParser(description=__doc__);connection_arguments(p);p.add_argument('--apply',action='store_true');args=p.parse_args()
jama=Jama(args)
if jama.base!='https://a-d-consulting.jamacloud.com':raise SystemExit('This migration is scoped to the connected REQHW instance')
current=jama.get('/items/9782')
if current['project']!=53 or current['itemType']!=33:raise SystemExit('Unexpected execution prompt identity')
body=current['fields']['description']
before=(ROOT/'docs/REQHW-TXT-5.before.html').read_text(encoding='utf-8').strip()
prepared=(ROOT/'docs/REQHW-TXT-5.updated.html').read_text(encoding='utf-8').strip()
anchor='<h1>Ground Rules</h1>'
addition=prepared[prepared.index('<h2>7 PUBLISH INTERACTIVE MODEL VIEWER</h2>'):prepared.index(anchor)]
already='<h2>7 PUBLISH INTERACTIVE MODEL VIEWER</h2>' in body
print(json.dumps({'itemId':current['id'],'project':current['project'],'version':current.get('currentVersion'),'step7Present':already,'originalMatchesPreparedSnapshot':body.strip()==before,'applyRequested':args.apply}))
if not args.apply:raise SystemExit(0)
if already:
    if addition.strip() not in body:raise SystemExit('Step 7 exists with different content; reconcile before editing')
    updated=body
else:
    if body.strip()!=before:raise SystemExit('Original live prompt differs from the prepared snapshot; reconcile before editing')
    updated=body.replace(anchor,addition+anchor)
    (ROOT/'docs/REQHW-TXT-5.raw-before.html').write_text(body,encoding='utf-8')
    check=jama.get('/items/9782')
    if check['fields']['description']!=body:raise SystemExit('Prompt changed before update; no write made')
    jama.request('PATCH','/items/9782',json=[{'op':'replace','path':'/fields/description','value':updated}])
saved=jama.get('/items/9782')
if saved['fields']['description'].strip()!=updated.strip():raise SystemExit('Saved prompt verification differs; inspect before retrying')
(ROOT/'docs/REQHW-TXT-5.saved.html').write_text(saved['fields']['description'],encoding='utf-8')
print(json.dumps({'verified':True,'itemId':saved['id'],'version':saved.get('currentVersion'),'onlyDescriptionSubmitted':True}))
