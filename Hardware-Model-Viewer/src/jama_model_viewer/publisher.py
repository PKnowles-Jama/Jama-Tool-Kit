"""Separate resumable publication; final manifest association is the commit marker."""
import copy
import json
import shutil
import uuid
import io
from datetime import datetime, timezone
from pathlib import Path
from .core import (MANIFEST_PREFIX, digest, inspect_file, local_file, origin, positive,
                   read_json, save_json, validate_manifest, attachment_url, MAX_FILE)


def now():
    return datetime.now(timezone.utc).isoformat()


def completed_run(run):
    state = read_json(run / 'publish-state.json')
    plan = read_json(run / 'summary-plan.json')
    if state.get('complete') is not True or state.get('pending') is not None:
        raise ValueError('Summary publication is incomplete; finish step 6 first')
    return {'jamaOrigin': origin(plan['baseUrl']), 'projectId': positive(plan['project']),
            'itemId': positive(state['summaryId']), 'summaryId': positive(state['summaryId'])}


def prepare(args):
    run = args.run.resolve()
    binding = completed_run(run)
    folder = run / 'viewer'
    if (folder / 'manifest.prepared.json').exists():
        raise ValueError('Package already exists; validate or resume it rather than overwrite')
    models = args.model if isinstance(args.model, list) else [args.model]
    inputs = [(p, 'model') for p in models] + [(p, 'source') for p in args.source] + [(p, 'animation') for p in args.gif] + [(p, 'drawing') for p in args.drawing] + [(p, 'document') for p in args.document]
    names = [p.name.casefold() for p, _ in inputs]
    if len(set(names)) != len(names):
        raise ValueError('Artifact filenames must be unique')
    assets = [inspect_file(p, role) for p, role in inputs]
    folder.mkdir(parents=True, exist_ok=True)
    for (p, _), asset in zip(inputs, assets):
        target = local_file(folder, asset['name'])
        if p.resolve() != target:
            shutil.copyfile(p, target)
    from PIL import Image
    for a in list(assets):
        if a['role'] == 'animation':
            poster_name = a['name'] + '.poster.png'
            if poster_name.casefold() in names:
                raise ValueError('Generated poster filename conflicts with an input')
            with Image.open(folder / a['name']) as image:
                image.seek(0)
                image.convert('RGB').save(folder / poster_name)
            assets.append(inspect_file(folder / poster_name, 'poster'))
            a['poster'] = poster_name
    m = {'schemaVersion': 1, 'status': 'prepared', 'runId': str(uuid.uuid4()),
         'revision': args.revision, 'createdAt': now(), 'binding': binding,
         'sourceSha256': digest((run / 'coverage.json').read_bytes()),
         'units': args.units, 'upAxis': args.up_axis, 'projection': args.projection,
         'drawingKind': args.drawing_kind, 'assets': assets}
    validate_manifest(m, published=False)
    save_json(folder / 'manifest.prepared.json', m)
    print(f'Prepared {len(assets)} assets in {folder}')


def validate_package(run):
    folder = run / 'viewer'
    m = validate_manifest(read_json(folder / 'manifest.prepared.json'), completed_run(run), published=False)
    if digest((run / 'coverage.json').read_bytes()) != m['sourceSha256']:
        raise ValueError('Requirements snapshot changed since preparation')
    for a in m['assets']:
        actual = inspect_file(local_file(folder, a['name']), a['role'])
        if any(actual[k] != a[k] for k in actual):
            raise ValueError('Packaged artifact changed: ' + a['name'])
    return m


def verify_destination(jama, binding):
    if jama.base != binding['jamaOrigin']:
        raise ValueError('Jama connection differs from package origin')
    item = jama.get(f"/items/{binding['itemId']}")
    if item['project'] != binding['projectId']:
        raise ValueError('Destination is in a different project')
    return item


def publish_one(jama, binding, file, asset, title, state, ledger):
    entry = state.setdefault('uploads', {}).setdefault(asset['name'], {'sha256': asset['sha256'], 'pending': None})
    if entry['sha256'] != asset['sha256']:
        raise ValueError('Ledger content differs from package')
    storage = entry.get('storage')
    upload_data = file.read_bytes()
    # ZIP is a supported attachment format on Cloud, while GLB/STEP/JSON may not be.
    # Already-confirmed direct uploads retain their original representation.
    if storage or (not entry.get('uploaded') and file.suffix.lower() in ('.glb', '.3mf', '.step', '.stp', '.json')):
        from .archive import pack
        upload_data = pack(upload_data, asset['name'])
        proposed = {'encoding': 'zip', 'name': asset['name'] + '.zip',
                    'bytes': len(upload_data), 'sha256': digest(upload_data)}
        if storage and storage != proposed:
            raise ValueError('ZIP representation differs from the publication ledger')
        storage = proposed
    upload_name = storage['name'] if storage else asset['name']
    upload_mime = 'application/zip' if storage else asset['mime']
    if len(upload_data) > MAX_FILE:
        raise ValueError('Stored artifact including ZIP overhead exceeds 50 MiB')
    if not entry.get('attachmentId'):
        if entry['pending']:
            raise ValueError('Attachment creation unresolved: reconcile by exact title and ID; see README')
        entry['pending'] = 'create'
        save_json(ledger, state)
        response = jama.request('POST', f"/projects/{binding['projectId']}/attachments",
                                json={'fields': {'name': title, 'description': 'Hardware Model Viewer artifact'}})
        entry.update(attachmentId=positive(int(response['meta']['id'])), pending=None)
        save_json(ledger, state)
    aid = entry['attachmentId']
    metadata = jama.get(f'/attachments/{aid}')
    if metadata['project'] != binding['projectId'] or metadata['fields']['name'] != title:
        raise ValueError('Attachment ledger identity does not match')
    if not entry.get('uploaded'):
        entry['pending'] = 'upload'
        save_json(ledger, state)
        jama.request('PUT', f'/attachments/{aid}/file', files={'file': (upload_name, io.BytesIO(upload_data), upload_mime)})
        metadata = jama.get(f'/attachments/{aid}')
    if metadata.get('fileName') != upload_name or metadata.get('fileSize') != len(upload_data):
        raise ValueError('Uploaded attachment metadata differs')
    url = attachment_url(jama.base, metadata)
    data = jama.request('GET', '/files', params={'url': url}, raw=True).content
    if digest(data) != digest(upload_data):
        raise ValueError('Uploaded attachment bytes differ')
    entry.update(uploaded=True, fileId=metadata['fields']['attachment'])
    if storage:
        entry['storage'] = storage
    if entry['pending'] != 'associate':
        entry['pending'] = None
    save_json(ledger, state)
    linked = {a['id'] for a in jama.paged(f"/items/{binding['itemId']}/attachments")}
    if aid not in linked:
        if entry['pending'] == 'associate':
            raise ValueError('Association unresolved; confirm absence before clearing pending')
        entry['pending'] = 'associate'
        save_json(ledger, state)
        jama.request('POST', f"/items/{binding['itemId']}/attachments", json={'attachment': aid})
        if aid not in {a['id'] for a in jama.paged(f"/items/{binding['itemId']}/attachments")}:
            raise RuntimeError('Attachment association could not be verified')
    entry['pending'] = None
    save_json(ledger, state)
    result = {**asset, 'attachmentId': aid, 'fileId': entry['fileId']}
    if storage:
        result['storage'] = storage
    return result


def publish(args, jama):
    run = args.run.resolve()
    manifest = validate_package(run)
    verify_destination(jama, manifest['binding'])
    # Read-only metadata access does not establish upload permission; actual writes
    # remain enforced by Jama and resumable individually.
    jama.paged(f"/items/{manifest['binding']['itemId']}/attachments")
    if args.preflight:
        print('Read-only preflight passed; upload permissions and binary MIME support require live qualification.')
        return
    ledger = run / 'viewer-publish-state.json'
    package_hash = digest(json.dumps(manifest, sort_keys=True).encode())
    state = read_json(ledger) if ledger.exists() else {'packageSha256': package_hash, 'publishedAt': now(), 'complete': False}
    if state['packageSha256'] != package_hash:
        raise ValueError('Publication ledger belongs to a different package')
    folder = run / 'viewer'
    result = copy.deepcopy(manifest)
    result['assets'] = [publish_one(jama, manifest['binding'], folder / a['name'], a,
                        f"JHMV asset {manifest['runId']} {a['sha256']}", state, ledger) for a in manifest['assets']]
    result.update(status='complete', publishedAt=state['publishedAt'])
    validate_manifest(result)
    name = f"jhmv-{manifest['runId']}.json"
    save_json(folder / name, result)
    data = (folder / name).read_bytes()
    asset = {'name': name, 'mime': 'application/json', 'bytes': len(data), 'sha256': digest(data)}
    # The final association publishes the complete immutable run atomically to readers.
    publish_one(jama, manifest['binding'], folder / name, asset,
                MANIFEST_PREFIX + manifest['runId'], state, ledger)
    state['complete'] = True
    save_json(ledger, state)
    print(f"Viewer published: {jama.base}/perspective.req#/items/{manifest['binding']['itemId']}")
