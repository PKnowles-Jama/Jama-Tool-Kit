"""Create whitelisted native and static archives without credentials or run data."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
dist=ROOT/'dist';dist.mkdir(exist_ok=True)
paths=[]
for name in ('README.md','Implementation-Plan.md','viewer.py','requirements.txt'):
    paths.append(ROOT/name)
for name in ('src','frontend','scripts','schemas','deploy','third_party','wheelhouse'):
    paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('update_execution_prompt.py','qualify_jama.py'))
paths.append(ROOT/'config/viewer.example.json')
paths.extend(ROOT/'docs'/name for name in ('deployment.md','validation.md'))
paths=sorted(set(p for p in paths if p.exists()))
with zipfile.ZipFile(dist/'hardware-model-viewer.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    archive.writestr('release-checksums.json',json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
with zipfile.ZipFile(dist/'static-viewer.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in paths:
        if p.is_relative_to(ROOT/'frontend') and not p.is_relative_to(ROOT/'frontend/vendor/occt') and not p.is_relative_to(ROOT/'frontend/demo') and p.name!='step-to-glb.cjs':
            archive.write(p,p.relative_to(ROOT/'frontend').as_posix())
    config=json.loads((ROOT/'config/viewer.example.json').read_text());config['mode']='static'
    archive.writestr('viewer-config.json',json.dumps(config,indent=2))
    archive.writestr('DEPLOYMENT.md',(ROOT/'docs/deployment.md').read_text(encoding='utf-8'))
    archive.writestr('THIRD-PARTY-NOTICE.md',(ROOT/'third_party/NOTICE.md').read_text(encoding='utf-8'))
for name in ('hardware-model-viewer.zip','static-viewer.zip'):
    path=dist/name
    (dist/(name+'.sha256')).write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+name+'\n',encoding='ascii')
print('Created native and static archives in dist; review target configuration and third-party distribution requirements.')
