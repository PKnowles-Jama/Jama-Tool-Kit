"""Build-time download of pinned npm archives; no downloads at viewer runtime."""
import base64
import hashlib
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'frontend' / 'vendor'
inventory = []


def package(name, version):
    meta = json.load(urllib.request.urlopen(f'https://registry.npmjs.org/{name}/{version}', timeout=30))
    data = urllib.request.urlopen(meta['dist']['tarball'], timeout=60).read()
    expected = meta['dist']['integrity']
    actual = 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if actual != expected:
        raise RuntimeError('npm archive integrity mismatch')
    inventory.append({'name': name, 'version': version, 'url': meta['dist']['tarball'], 'integrity': actual})
    return tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')


three = package('three', '0.180.0')
paths = ['build/three.module.js', 'build/three.core.js', 'examples/jsm/controls/OrbitControls.js',
         'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/loaders/3MFLoader.js', 'LICENSE']
done = set()
while paths:
    name = paths.pop()
    if name in done:
        continue
    done.add(name)
    data = three.extractfile('package/' + name).read()
    if name.endswith('.js'):
        text = data.decode()
        for dep in re.findall(r"(?:from\s*|import\s*)['\"]([^'\"]+)['\"]", text):
            if dep.startswith('.'):
                import posixpath
                paths.append(posixpath.normpath(posixpath.join(posixpath.dirname(name), dep)))
        # Resolve bare imports without an inline import map (strict CSP).
        import posixpath
        relative = posixpath.relpath('build/three.module.js', posixpath.dirname(name))
        if not relative.startswith('.'):
            relative = './' + relative
        text = re.sub(r"(['\"])three\1", lambda m: m[1] + relative + m[1], text)
        data = text.encode()
    target = out / 'three' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

occt = package('occt-import-js', '0.0.23')
for member in occt.getmembers():
    name = member.name.removeprefix('package/')
    if name in ('dist/occt-import-js.js', 'dist/occt-import-js.wasm', 'LICENSE.md'):
        target = out / 'occt' / Path(name).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(occt.extractfile(member).read())
inventory.append({'files': [{'path': str(p.relative_to(ROOT)).replace('\\', '/'), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in sorted(out.rglob('*')) if p.is_file()]})
(ROOT / 'third_party' / 'vendor-lock.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
print('Bundled verified Three.js and local STEP converter dependencies.')
