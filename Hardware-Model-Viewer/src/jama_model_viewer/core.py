"""Bounded manifests, self-contained models, and exact Jama item binding."""
import hashlib
import io
import json
import re
import struct
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, quote

MANIFEST_PREFIX = 'JHMV manifest v1 '
MAX_FILE = 50 * 1024 * 1024
MIMES = {'.glb': 'model/gltf-binary', '.3mf': 'model/3mf', '.step': 'application/step',
         '.stp': 'application/step', '.png': 'image/png', '.jpg': 'image/jpeg',
         '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.pdf': 'application/pdf'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    # OneDrive/antivirus can briefly hold the previous ledger after a read.
    for attempt in range(7):
        try:
            temp.replace(path)
            break
        except PermissionError:
            if attempt == 6:
                raise
            time.sleep(.05 * 2 ** attempt)


def origin(value):
    p = urlsplit(value)
    if p.scheme != 'https' or not p.netloc or p.username or p.password or p.path not in ('', '/') or p.query or p.fragment:
        raise ValueError('Expected an HTTPS origin without a path or credentials')
    return value.rstrip('/')


def positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('Expected a positive numeric ID or size')
    return value


def local_file(folder, name):
    if not isinstance(name, str) or not name or '/' in name or '\\' in name or ':' in name or name in ('.', '..'):
        raise ValueError('Artifact must be a simple filename')
    p = (Path(folder) / name).resolve()
    if p.parent != Path(folder).resolve():
        raise ValueError('Artifact escapes package directory')
    return p


def check_model(data, suffix):
    if suffix == '.glb':
        if len(data) < 20 or data[:4] != b'glTF' or struct.unpack_from('<II', data, 4) != (2, len(data)):
            raise ValueError('Invalid GLB header')
        size, kind = struct.unpack_from('<II', data, 12)
        if kind != 0x4e4f534a or size > len(data) - 20:
            raise ValueError('Invalid GLB JSON chunk')
        doc = json.loads(data[20:20+size])
        if doc.get('extensionsUsed'):
            raise ValueError('Export an uncompressed GLB without extensions for the qualified baseline')
        for entry in doc.get('buffers', []) + doc.get('images', []):
            if 'uri' in entry:
                raise ValueError('GLB must embed all buffers and images without URI references')
        if sum(a.get('count', 0) for a in doc.get('accessors', [])) > 15000000:
            raise ValueError('GLB accessor budget exceeded')
    elif suffix == '.3mf':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 1000 or sum(i.file_size for i in infos) > 200 * 1024 * 1024:
                raise ValueError('3MF expanded archive budget exceeded')
            if not any(i.filename.lower().endswith('.model') for i in infos):
                raise ValueError('3MF has no model')
            for i in infos:
                if i.flag_bits & 1 or i.file_size / max(i.compress_size, 1) > 1000:
                    raise ValueError('3MF encrypted or excessive compression ratio')
                if i.filename.lower().endswith(('.rels', '.model')):
                    xml = archive.read(i)
                    if re.search(rb'<!DOCTYPE|<!ENTITY|TargetMode\s*=\s*[\"\x27]External|https?://(?!schemas\.|www\.w3\.org)', xml, re.I):
                        raise ValueError('3MF external reference or XML entity is not allowed')


def inspect_file(path, role):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in MIMES or not 0 < path.stat().st_size <= MAX_FILE:
        raise ValueError('Unsupported artifact type or file exceeds 50 MiB')
    data = path.read_bytes()
    if role == 'model':
        if suffix not in ('.glb', '.3mf'):
            raise ValueError('Preview must be a self-contained GLB or 3MF; convert STEP first')
        check_model(data, suffix)
    if suffix in ('.png', '.jpg', '.jpeg', '.gif'):
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 16777216:
                raise ValueError('Image exceeds 16 megapixels')
            expected = {'PNG': '.png', 'JPEG': '.jpg', 'GIF': '.gif'}.get(image.format)
            if expected != ('.jpg' if suffix == '.jpeg' else suffix):
                raise ValueError('Image encoding and extension differ')
            image.verify()
    return {'name': path.name, 'role': role, 'mime': MIMES[suffix], 'bytes': len(data), 'sha256': digest(data)}


def validate_manifest(m, binding=None, published=True):
    if m.get('schemaVersion') != 1 or m.get('status') != ('complete' if published else 'prepared'):
        raise ValueError('Unsupported or incomplete manifest')
    uuid.UUID(m['runId'])
    if published:
        from datetime import datetime
        stamp = datetime.fromisoformat(m['publishedAt'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError('Publication time must be UTC')
    if not re.fullmatch(r'[0-9a-f]{64}', m['sourceSha256']):
        raise ValueError('Missing source snapshot digest')
    b = m['binding']
    origin(b['jamaOrigin'])
    for key in ('projectId', 'itemId', 'summaryId'):
        positive(b[key])
    if binding and b != binding:
        raise ValueError('Manifest is bound to a different Jama item')
    if m['units'] not in ('mm', 'cm', 'm', 'in', 'ft') or m['upAxis'] not in ('Y', 'Z'):
        raise ValueError('Unsupported units or axis')
    if not 0 < len(m['assets']) <= 100:
        raise ValueError('Expected 1 to 100 artifacts')
    ids = set()
    names = set()
    for a in m['assets']:
        if a['name'] in names:
            raise ValueError('Duplicate filename')
        names.add(a['name'])
        local_file('.', a['name'])
        if a['role'] not in ('model', 'source', 'animation', 'poster', 'drawing', 'document'):
            raise ValueError('Unknown asset role')
        if Path(a['name']).suffix.lower() not in MIMES or a['mime'] != MIMES[Path(a['name']).suffix.lower()]:
            raise ValueError('Unsupported asset MIME type')
        if not re.fullmatch(r'[0-9a-f]{64}', a['sha256']) or not 0 < positive(a['bytes']) <= MAX_FILE:
            raise ValueError('Invalid artifact size or hash')
        if published:
            aid = positive(a['attachmentId'])
            positive(a['fileId'])
            if aid in ids:
                raise ValueError('Duplicate attachment ID')
            ids.add(aid)
            if a.get('storage'):
                storage = a['storage']
                if storage['encoding'] != 'zip' or storage['name'] != a['name'] + '.zip':
                    raise ValueError('Unsupported asset storage container')
                if not 0 < positive(storage['bytes']) <= MAX_FILE or not re.fullmatch(r'[0-9a-f]{64}', storage['sha256']):
                    raise ValueError('Invalid ZIP storage length or hash')
    if not 1 <= sum(a['role'] == 'model' for a in m['assets']) <= 20:
        raise ValueError('Expected 1 to 20 model previews')
    for a in m['assets']:
        if a['role'] == 'model' and Path(a['name']).suffix.lower() not in ('.glb', '.3mf'):
            raise ValueError('Unsupported model preview')
        if a['role'] == 'animation' and (a['mime'] != 'image/gif' or a.get('poster') not in names):
            raise ValueError('GIF requires a named poster')
        if a['role'] == 'animation' and not any(p['name'] == a['poster'] and p['role'] == 'poster' for p in m['assets']):
            raise ValueError('Animation poster must refer to a poster artifact')
        if a['role'] in ('poster', 'drawing') and a['mime'] not in ('image/png', 'image/jpeg'):
            raise ValueError('Drawing and poster previews must be PNG or JPEG')
    return m


def attachment_url(base, metadata):
    return f"{origin(base)}/attachment/{positive(metadata['fields']['attachment'])}/{quote(metadata['fileName'], safe='')}"
