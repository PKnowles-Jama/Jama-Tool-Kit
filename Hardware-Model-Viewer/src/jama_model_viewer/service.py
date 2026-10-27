"""Read-only delegated access; no public file URLs or general purpose proxy."""
import json
import re
from urllib.parse import quote
import requests
from .core import MANIFEST_PREFIX, attachment_url, digest, origin, positive, validate_manifest


class Rejected(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Reader:
    def __init__(self, config, token):
        self.config = config
        self.base = config['jamaOrigin']
        self.token = token

    def request(self, path, params=None, limit=None):
        try:
            with requests.get(self.base + self.config['apiRoot'] + path, params=params,
                              headers={'Authorization': 'Bearer ' + self.token},
                              timeout=(10, 60), allow_redirects=False, stream=True) as response:
                if response.status_code in (401, 403):
                    raise Rejected(response.status_code, 'Jama access expired or was denied. Reopen the tool from Jama.')
                if response.status_code != 200:
                    raise Rejected(502, f'Jama read failed (HTTP {response.status_code})')
                bound = limit or self.config['maxManifestBytes']
                chunks, count = [], 0
                for chunk in response.iter_content(65536):
                    count += len(chunk)
                    if count > bound:
                        raise Rejected(413, 'Jama response exceeds configured size limit')
                    chunks.append(chunk)
                return b''.join(chunks)
        except requests.RequestException:
            raise Rejected(502, 'Jama connection failed') from None

    def get(self, path, params=None):
        return json.loads(self.request(path, params))['data']

    def attachments(self, item):
        rows, start = [], 0
        while True:
            payload = json.loads(self.request(f'/items/{item}/attachments', {'startAt': start, 'maxResults': 50}))
            batch = payload['data']
            if not isinstance(batch, list):
                raise ValueError('Expected an attachment list')
            rows.extend(batch)
            if len(rows) > self.config['maxAttachments']:
                raise ValueError('Attachment inventory exceeds configured bound')
            if not batch:
                return rows
            start += len(batch)
            page = payload.get('meta', {}).get('pageInfo', {})
            if int(page.get('startIndex', start-len(batch))) != start-len(batch):
                raise ValueError('Unexpected attachment page offset')
            if page.get('totalResults') is not None and start >= int(page['totalResults']):
                return rows

    def context(self, payload):
        item_id = positive(payload['itemId'])
        project = positive(payload['projectId'])
        if project not in self.config['allowedProjectIds']:
            raise Rejected(403, 'Project is not configured for this viewer')
        item = self.get(f'/items/{item_id}')
        if item.get('project') != project:
            raise Rejected(403, 'Jama item project does not match launch context')
        attachments = self.attachments(item_id)
        candidates = [a for a in attachments if a.get('fields', {}).get('name', '').startswith(MANIFEST_PREFIX)]
        if len(candidates) > 30:
            raise ValueError('More than 30 viewer runs; archive older manifest associations')
        manifests = []
        linked = {a['id'] for a in attachments}
        for candidate in candidates:
            meta = self.get(f"/attachments/{positive(candidate['id'])}")
            if meta['project'] != project:
                raise Rejected(403, 'Manifest project differs')
            data = self.file(meta, self.config['maxManifestBytes'])
            if meta['fileName'].endswith('.json.zip'):
                from .archive import unpack
                data = unpack(data, meta['fileName'][:-4], self.config['maxManifestBytes'])
            m = json.loads(data)
            validate_manifest(m, {'jamaOrigin': self.base, 'projectId': project, 'itemId': item_id, 'summaryId': item_id})
            if meta['fields']['name'] != MANIFEST_PREFIX + m['runId']:
                raise ValueError('Manifest title and run ID differ')
            if not {a['attachmentId'] for a in m['assets']} <= linked:
                raise ValueError('Manifest contains an unassociated artifact')
            manifests.append(m)
        manifests.sort(key=lambda m: (m['publishedAt'], m['runId']), reverse=True)
        return {'item': {'id': item_id, 'name': item['fields']['name'], 'documentKey': item.get('documentKey', str(item_id))},
                'runs': manifests}

    def file(self, metadata, limit):
        if metadata.get('fileSize', limit + 1) > limit:
            raise Rejected(413, 'Artifact exceeds size limit')
        return self.request('/files', {'url': attachment_url(self.base, metadata)}, limit)

    def asset(self, payload):
        context = self.context(payload)  # Revalidate live item access and association each time.
        selected = next((m for m in context['runs'] if m['runId'] == payload['runId']), None)
        asset = next((a for a in (selected or {}).get('assets', []) if a['name'] == payload['name']), None)
        if not asset:
            raise Rejected(404, 'Artifact is not part of the selected published run')
        meta = self.get(f"/attachments/{asset['attachmentId']}")
        storage = asset.get('storage')
        if (meta['project'] != payload['projectId'] or meta['fields'].get('attachment') != asset['fileId']
                or meta.get('fileName') != (storage['name'] if storage else asset['name'])):
            raise Rejected(403, 'Artifact binding differs')
        data = self.file(meta, min(storage['bytes'] if storage else asset['bytes'], self.config['maxFileBytes']))
        if storage:
            if len(data) != storage['bytes'] or digest(data) != storage['sha256']:
                raise ValueError('Published ZIP container has changed')
            from .archive import unpack
            data = unpack(data, asset['name'], self.config['maxFileBytes'], asset['bytes'])
        if len(data) != asset['bytes'] or digest(data) != asset['sha256']:
            raise ValueError('Published artifact has changed')
        return data, asset['mime']


def load_config(path):
    from .core import read_json
    config = read_json(path)
    config['jamaOrigin'] = origin(config['jamaOrigin'])
    config['publicOrigin'] = origin(config['publicOrigin'])
    if config['mode'] not in ('adapter', 'static') or config['apiRoot'] not in ('/rest/v1', '/rest/latest'):
        raise ValueError('Unsupported deployment mode or API root')
    if not config['allowedProjectIds']:
        raise ValueError('Configure at least one project')
    for value in config['allowedProjectIds']:
        positive(value)
    for key in ('maxFileBytes', 'maxTriangles', 'maxTexturePixels', 'maxExpandedBytes', 'maxAttachments', 'maxManifestBytes'):
        positive(config[key])
    if any(re.search('secret|token|password|credential', k, re.I) for k in config):
        raise ValueError('Viewer configuration must contain no credentials')
    return config
