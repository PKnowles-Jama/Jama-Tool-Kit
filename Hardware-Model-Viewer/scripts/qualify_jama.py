"""Read-only Cloud qualification. Never print credentials or raw Jama content."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from jama_model_viewer.jama_rest import Jama, connection_arguments

p=argparse.ArgumentParser(description=__doc__)
connection_arguments(p)
p.add_argument('--viewer-origin',required=True)
args=p.parse_args()
jama=Jama(args)
user=jama.get('/users/current')
item=jama.get('/items/9782')
cors=requests.options(jama.base+'/rest/v1/items/9782',headers={'Origin':args.viewer_origin,'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'},timeout=30,allow_redirects=False)
headers={k:v for k,v in cors.headers.items() if k.lower().startswith('access-control-')}
report={'checkedAt':datetime.now(timezone.utc).isoformat(),'jamaOrigin':jama.base,'viewerOrigin':args.viewer_origin,
        'authenticatedRead':bool(user.get('id')),'promptItemId':item['id'],'promptProject':item['project'],
        'corsOptionsStatus':cors.status_code,'corsHeaders':headers,
        'staticQualification':'requires browser/host qualification; OPTIONS alone does not prove delegated iframe support',
        'writesPerformed':False,'selfHostedQualification':'not available in this workspace'}
(ROOT/'docs').mkdir(exist_ok=True)
(ROOT/'docs/jama-read-qualification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
