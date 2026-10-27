"""Read-only inspection of the live Jama API contract for this execution."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from jama_model_viewer.jama_rest import Jama
from jama_model_viewer.core import save_json

j = Jama(argparse.Namespace(base_url='https://a-d-consulting.jamacloud.com',
    credentials=ROOT.parents[1] / 'Requirements-to-Hardware/Scripts/info.json'))
out = ROOT / 'docs/jctk-2026-10-27'
for path in ('/rest/labs/api-docs',):
    r = j.session.get(j.base + path, params={'project': 56} if path.endswith('baselines') else None,
        timeout=45, allow_redirects=False)
    print(path, r.status_code, r.headers.get('Content-Type'), flush=True)
    if r.status_code == 200:
        if 'json' in r.headers.get('Content-Type', ''):
            data = r.json()
            save_json(out / ('probe-' + path.strip('/').replace('/', '-') + '.json'), data)
            print(json.dumps(data)[:2500], flush=True)
        else:
            (out / 'api-docs.html').write_text(r.text, encoding='utf-8')
            print(r.text[:4500], flush=True)
