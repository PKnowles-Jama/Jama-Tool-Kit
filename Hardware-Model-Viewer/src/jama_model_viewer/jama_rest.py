"""Small Jama REST client; credentials and raw responses never go to stdout."""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse
import requests


def connection_arguments(parser: argparse.ArgumentParser):
    parser.add_argument('--base-url', default=os.getenv('JAMA_BASE_URL', 'https://a-d-consulting.jamacloud.com'))
    parser.add_argument('--credentials', type=Path, help='Valid JSON with client_id and client_secret; alternatively use JAMA_CLIENT_ID/JAMA_CLIENT_SECRET')


class Jama:
    def __init__(self, args):
        self.base = args.base_url.rstrip('/')
        parsed = urlparse(self.base)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
            raise ValueError('base-url must be an HTTPS Jama origin without credentials, query or fragment')
        credentials = {}
        if args.credentials:
            try:
                credentials = json.loads(args.credentials.read_text(encoding='utf-8-sig'))
            except (ValueError, OSError):
                raise ValueError('Cannot read credentials JSON. Check syntax and file access.') from None
        self.client_id = credentials.get('client_id') or os.getenv('JAMA_CLIENT_ID')
        self.secret = credentials.get('client_secret') or os.getenv('JAMA_CLIENT_SECRET')
        if not self.client_id or not self.secret:
            raise ValueError('Provide OAuth credentials via --credentials or environment variables')
        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        self.authenticate()

    def authenticate(self):
        try:
            response = self.session.post(self.base + '/rest/oauth/token',
                auth=(self.client_id, self.secret), data={'grant_type': 'client_credentials'}, timeout=30, allow_redirects=False)
        except requests.RequestException:
            raise RuntimeError('OAuth connection failed') from None
        if response.status_code != 200:
            raise RuntimeError(f'OAuth rejected (HTTP {response.status_code})')
        self.session.headers['Authorization'] = 'Bearer ' + response.json()['access_token']

    def request(self, method, path, raw=False, **kwargs):
        # Only reads are retried. A timed-out POST can already have committed.
        for attempt in range(4 if method == 'GET' else 1):
            try:
                response = self.session.request(method, self.base + '/rest/latest' + path,
                    timeout=60, allow_redirects=False, **kwargs)
            except requests.RequestException:
                if method == 'GET' and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f'{method} {path}: connection failed; reconcile any pending write before retrying') from None
            if method == 'GET' and response.status_code == 401 and attempt < 3:
                self.authenticate()
                continue
            if method == 'GET' and response.status_code in (429, 502, 503, 504) and attempt < 3:
                delay = response.headers.get('Retry-After', '')
                time.sleep(min(int(delay), 30) if delay.isdigit() else 2 ** attempt)
                continue
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f'{method} {path}: HTTP {response.status_code}')
            return response if raw else response.json() if response.content else {}
        raise RuntimeError(f'{method} {path}: retry limit reached')

    def get(self, path, params=None):
        return self.request('GET', path, params=params).get('data')

    def paged(self, path, params=None):
        query = dict(params or {})
        rows, start = [], 0
        while True:
            payload = self.request('GET', path, params={**query, 'startAt': start, 'maxResults': 50})
            batch = payload.get('data')
            if not isinstance(batch, list):
                raise RuntimeError(f'{path}: expected paginated array')
            page = payload.get('meta', {}).get('pageInfo', {})
            if batch and int(page.get('startIndex', start)) != start:
                raise RuntimeError(f'{path}: server returned an unexpected page offset')
            rows.extend(batch)
            if not batch:
                return rows
            start += len(batch)
            total = page.get('totalResults')
            if total is not None and start >= int(total):
                return rows
            # Without a count, continue until an empty page; do not guess from page length.


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def run(main):
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        raise SystemExit(str(error)) from None
