"""Resumable, read-back-verified execution of the approved JCTK-TXT-5 plan.

One-off project documentation workflow; not a viewer runtime dependency.
"""
import argparse
import hashlib
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/jctk-2026-10-27'
sys.path.insert(0, str(ROOT / 'src'))
from jama_model_viewer.jama_rest import Jama
from jama_model_viewer.core import save_json

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

class Text(HTMLParser):
    def __init__(self, value):
        super().__init__(); self.parts = []; self.feed(value)
    def handle_data(self, data):
        self.parts.append(data)

def plain(value):
    return ' '.join(''.join(Text(value).parts).split())

def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')

class Execution:
    def __init__(self):
        self.plan = read('specification-plan.json')
        self.j = Jama(argparse.Namespace(base_url='https://a-d-consulting.jamacloud.com',
            credentials=ROOT.parents[1] / 'Requirements-to-Hardware/Scripts/info.json'))
        self.state = read('execution-ledger.json') if (OUT / 'execution-ledger.json').exists() else {
            'project': 56, 'approvedBy': 'User message: proceed', 'approvedAt': stamp(),
            'approvedPlanSHA256': hashlib.sha256((OUT / 'Implementation-Plan.md').read_bytes()).hexdigest(),
            'items': {}, 'relationships': {}, 'baselines': {}, 'pending': None}

    def save(self):
        save_json(OUT / 'execution-ledger.json', self.state)

    def preflight(self):
        assert hashlib.sha256((OUT / 'Implementation-Plan.md').read_bytes()).hexdigest() == self.state['approvedPlanSHA256']
        mismatches = [p for p, h in read('code-snapshot.json')['files'].items()
            if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
        assert not mismatches, f'Approved code snapshot changed: {mismatches}'
        project = self.j.get('/projects/56')
        assert project['id'] == 56
        items = self.j.paged('/items', {'project': 56})
        save_json(OUT / 'items-refreshed.json', items)
        schemas = {str(t): self.j.get(f'/itemtypes/{t}') for t in (31,32,132,24,133)}
        save_json(OUT / 'schemas-refreshed.json', schemas)
        rules = self.j.paged('/relationshiprulesets')
        options = self.j.paged('/picklists/63/options')
        assert any(x['id'] == 292 and x['name'].lower() == 'draft' for x in options)
        saved_rules = read('relationship-rule-sets.json')
        assert rules == saved_rules, 'Relationship model changed since approval'
        for t in schemas:
            before = read('schemas.json')[t]
            now = schemas[t]
            # Jama emits widgets in nondeterministic order; their definitions still must match.
            before = dict(before, widgets=sorted(before.get('widgets', []), key=lambda w:w['name']))
            now = dict(now, widgets=sorted(now.get('widgets', []), key=lambda w:w['name']))
            assert now == before, f'Schema changed: {t}'
        by_id = {i['id']: i for i in items}
        for field, set_id in self.plan['sets'].items():
            assert by_id[set_id]['itemType'] == 31
        original = read('items-before.json')
        inventory_delta = {'removedBeforeExecution':sorted(i['id'] for i in original if i['id'] not in by_id),
            'addedBeforeExecution':sorted(set(by_id)-{i['id'] for i in original})}
        for old in original:
            if old['id'] in by_id:
                assert old['fields'] == by_id[old['id']]['fields'], f'Existing item changed: {old["id"]}'
        if not self.state['items']:
            assert not inventory_delta['addedBeforeExecution'], 'New items require duplicate reconciliation'
            assert not any(i['itemType'] in (132,24) for i in items), 'Existing features or requirements require reconciliation'
        save_json(OUT / 'preflight.json', {'at': stamp(), 'project':project, 'items':items,
            'schemasMatch':True, 'rulesMatch':True, 'codeSnapshotMatch':True, 'inventoryDelta':inventory_delta})
        self.save()
        print(f'Preflight verified: {len(items)} project items; approved code, schemas and TIM match.', flush=True)

    def baseline(self, stage):
        if stage in self.state['baselines']:
            entry = self.state['baselines'][stage]
        else:
            pending = self.state['pending']
            if pending:
                assert pending['kind'] == 'baseline' and pending['stage'] == stage, 'Reconcile pending operation first'
                matches = [b for b in self.j.paged('/baselines', {'project':56}) if b['name'] == pending['body']['name']]
                if not matches and pending['body'].get('source') == 56:
                    rejected = read(f'baseline-{stage.lower()}-response.json')
                    assert rejected.get('meta', {}).get('status') == 'Not Found'
                    assert 'existing sourceId' in rejected.get('meta', {}).get('message','')
                    # Source is a baseline-source ID, not a project ID. The origin
                    # fields create the first source when source is omitted.
                    self.state.setdefault('rejectedBaselineRequests', []).append(pending)
                    self.state['pending'] = None
                    self.save()
                    return self.baseline(stage)
                assert len(matches) == 1, 'Pending baseline has unknown outcome; inspect before retry'
                entry = {'id':matches[0]['id'], 'name':matches[0]['name'], 'expectedIds':pending['expectedIds']}
            else:
                current = self.j.paged('/items', {'project':56})
                body = {'baselineOriginType':'PROJECT', 'baselineOriginId':56,
                    'name': f'{stage}-Generate Features and Requirements {datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}',
                    'description':'Full project 56 snapshot for approved JCTK-TXT-5 Hardware-Model-Viewer specification generation.'}
                self.state['pending'] = {'kind':'baseline', 'stage':stage, 'body':body,
                    'expectedIds':sorted(i['id'] for i in current), 'at':stamp()}
                self.save()
                # Labs is the live documented POST endpoint. No automatic POST retries.
                response = self.j.session.post(self.j.base + '/rest/labs/baselines', json=body,
                    timeout=60, allow_redirects=False)
                save_json(OUT / f'baseline-{stage.lower()}-response.json', response.json())
                if response.status_code != 201:
                    raise RuntimeError(f'Baseline creation HTTP {response.status_code}; inspect saved response and reconcile before retry')
                matches = [b for b in self.j.paged('/baselines', {'project':56}) if b['name'] == body['name']]
                assert len(matches) == 1, 'Baseline not yet visible; reconcile pending operation'
                entry = {'id':matches[0]['id'], 'name':body['name'], 'expectedIds':self.state['pending']['expectedIds']}
            self.state['baselines'][stage] = entry
            self.state['pending'] = None
            self.save()
        baseline = self.j.get(f'/baselines/{entry["id"]}')
        assert baseline['origin'].get('project') == 56 and not baseline['origin'].get('item'), 'Baseline is not project-root scoped'
        rows = self.j.paged(f'/baselines/{entry["id"]}/versioneditems')
        ids = {r['id'] for r in rows}
        assert ids == set(entry['expectedIds']), f'Baseline coverage mismatch: missing {set(entry["expectedIds"])-ids}, extra {ids-set(entry["expectedIds"])}'
        save_json(OUT / f'baseline-{stage.lower()}-verified.json', {'baseline':baseline, 'items':rows, 'verifiedAt':stamp()})
        entry['verifiedCount'] = len(rows)
        self.save()
        print(f'{stage} baseline {entry["id"]}: full project origin and all {len(rows)} items verified.', flush=True)

    def check_item(self, item, body):
        assert item['project'] == 56 and item['itemType'] == body['itemType']
        assert item['location']['parent']['item'] == body['location']['parent']['item']
        if 'childItemType' in body:
            assert item['childItemType'] == body['childItemType']
        for k, v in body['fields'].items():
            actual = item['fields'].get(k, '')
            assert (plain(actual) == plain(v) if k == 'description' else actual == v), f'Field mismatch: {item["id"]}/{k}'

    def ensure_item(self, key, item_type, parent, name, description, child_type=None):
        fields = {'name':name, 'description':description}
        if item_type in (132,24): fields['status'] = 292
        body = {'project':56, 'itemType':item_type, 'location':{'parent':{'item':parent}}, 'fields':fields}
        if child_type: body['childItemType'] = child_type
        if key in self.state['items']:
            item = self.j.get(f'/items/{self.state["items"][key]["id"]}')
        else:
            matches = [i for i in self.inventory if i['itemType'] == item_type
                and i.get('location',{}).get('parent',{}).get('item') == parent
                and i['fields'].get('name') == name]
            assert len(matches) <= 1, f'Duplicate candidates: {key}'
            if matches:
                item = self.j.get(f'/items/{matches[0]["id"]}')
                if self.state['pending']:
                    assert self.state['pending']['key'] == key
            else:
                assert self.state['pending'] is None, 'Reconcile pending write before creating anything'
                self.state['pending'] = {'kind':'item','key':key,'body':body,'at':stamp()}
                self.save()
                result = self.j.request('POST', '/items', json=body)
                item_id = result['meta']['id']
                # Store the returned ID before a read that might fail.
                self.state['items'][key] = {'id':item_id, 'body':body}
                self.state['pending'] = None
                self.save()
                item = self.j.get(f'/items/{item_id}')
                self.inventory.append(item)
        self.check_item(item, body)
        self.state['items'][key] = {'id':item['id'], 'documentKey':item['documentKey'],
            'name':name, 'body':body, 'verifiedAt':stamp()}
        if self.state['pending'] and self.state['pending'].get('key') == key:
            self.state['pending'] = None
        self.save()
        return item['id']

    def ensure_relationship(self, source, target, existing):
        key = f'{source}:{target}:4'
        matches = [r for r in existing if r['fromItem'] == source and r['toItem'] == target and r['relationshipType'] == 4]
        assert len(matches) <= 1, f'Duplicate relationship: {key}'
        if matches:
            row = matches[0]
            if self.state['pending']:
                assert self.state['pending'].get('key') == key
                self.state['pending'] = None
        else:
            assert self.state['pending'] is None, 'Reconcile pending operation first'
            body = {'fromItem':source, 'toItem':target, 'relationshipType':4}
            self.state['pending'] = {'kind':'relationship','key':key,'body':body,'at':stamp()}
            self.save()
            result = self.j.request('POST', '/relationships', json=body)
            self.state['relationships'][key] = {'id':result['meta']['id'], **body}
            self.state['pending'] = None
            self.save()
            row = self.j.get(f'/relationships/{result["meta"]["id"]}')
            assert all(row[k] == v for k,v in body.items())
            existing.append(row)
        self.state['relationships'][key] = {k:row[k] for k in ('id','fromItem','toItem','relationshipType')}
        self.save()

    def description(self, row):
        return '<p>' + html.escape(row['description']) + '</p><p>Implementation evidence: ' + html.escape(', '.join(row['evidence'])) + '. Generated from the approved JCTK-TXT-5 plan for Hardware-Model-Viewer; reference ' + row['key'] + '. Status reflects a code-derived Draft specification, not independent acceptance verification.</p>'

    def items(self):
        assert self.state['baselines'].get('Pre',{}).get('verifiedCount') is not None
        self.inventory = self.j.paged('/items', {'project':56})
        for label, typ in (('features',132),('requirements',24),('summaries',133)):
            self.ensure_item('folder:'+label,32,self.plan['sets'][label], 'Hardware-Model-Viewer',
                '<p>Hardware-Model-Viewer '+label+' generated under approved JCTK-TXT-5 on 2026-10-27.</p>',typ)
        for feature in self.plan['features']:
            fk = feature['key']
            rf = self.ensure_item('folder:'+fk,32,self.state['items']['folder:requirements']['id'],
                feature['name'], '<p>Requirements owned by the '+html.escape(feature['name'])+' feature of Hardware-Model-Viewer.</p>',24)
            fid = self.ensure_item(fk,132,self.state['items']['folder:features']['id'],feature['name'],self.description(feature))
            relationships = self.j.paged(f'/items/{fid}/downstreamrelationships')
            for requirement in feature['requirements']:
                rid = self.ensure_item(requirement['key'],24,rf,requirement['name'],self.description(requirement))
                self.ensure_relationship(fid,rid,relationships)
            print(f'{fk}: Draft feature, {len(feature["requirements"])} Draft requirements, folder and relationships verified.',flush=True)

    def verify(self):
        inventory = self.j.paged('/items', {'project':56})
        by_id = {i['id']:i for i in inventory}
        for entry in self.state['items'].values():
            self.check_item(by_id[entry['id']], entry['body'])
        feature_ids = {i['id'] for i in inventory if i['itemType'] == 132}
        count = 0
        for feature in self.plan['features']:
            fid = self.state['items'][feature['key']]['id']
            downstream = self.j.paged(f'/items/{fid}/downstreamrelationships')
            expected = {self.state['items'][r['key']]['id'] for r in feature['requirements']}
            actual = [r for r in downstream if r['toItem'] in expected and r['relationshipType'] == 4]
            assert len(actual) == len(expected) and {r['toItem'] for r in actual} == expected
            for requirement in feature['requirements']:
                rid = self.state['items'][requirement['key']]['id']
                upstream = self.j.paged(f'/items/{rid}/upstreamrelationships')
                owners = [r for r in upstream if r['fromItem'] in feature_ids]
                assert len(owners) == 1 and owners[0]['fromItem'] == fid and owners[0]['relationshipType'] == 4, f'Feature ownership mismatch: {rid}'
                count += 1
            print(f'{feature["key"]}: independent parent/status/content and one-feature ownership verification passed.',flush=True)
        summary = self.state['items'].get('summary')
        if summary:
            links = self.j.paged(f'/items/{summary["id"]}/downstreamrelationships')
            expected = {v['id'] for k,v in self.state['items'].items() if k.startswith('F')}
            assert len(links) == len(expected) and {r['toItem'] for r in links} == expected
            assert all(r['relationshipType'] == 4 for r in links)
        before = read('baseline-pre-verified.json')['items']
        for old in before:
            assert old['id'] in by_id and old['fields'] == by_id[old['id']]['fields'], f'Pre-existing item modified: {old["id"]}'
        expected_ids = {i['id'] for i in before} | {i['id'] for i in self.state['items'].values()}
        assert set(by_id) == expected_ids, 'Unexpected project inventory change'
        result = {'verifiedAt':stamp(),'features':12,'requirements':count,'folders':15,
            'summary':summary['id'] if summary else None, 'relationships':len(self.state['relationships']),
            'eachRequirementHasExactlyOneFeature':True,'allGeneratedSpecificationsDraft':True,
            'existingItemsUnchanged':True,'items':inventory}
        save_json(OUT / ('verification-final.json' if summary else 'verification-specifications.json'), result)
        self.state['verified'] = {k:v for k,v in result.items() if k != 'items'}
        self.save()
        print(f'Verified {len(inventory)} total project items, {count} requirement owners, {len(self.state["relationships"])} recorded relationships.',flush=True)

    def item_link(self, item_id):
        return f'{self.j.base}/perspective.req?projectId=56#/items/{item_id}'

    def publication_documents(self):
        """Freeze honest publication-time copies; the baseline follows this snapshot."""
        records = self.state['items']
        tasks = '\n'.join([
            '# Hardware Model Viewer Specification Tasks', '',
            'Publication snapshot: '+stamp()+'. The post-generation baseline is deliberately the next operation after the summary is saved.', '',
            '- [x] Review JCTK-TXT-5, current code and chat changes, schemas, Draft status, and mapped TIM.',
            '- [x] Obtain user approval of the complete 12-feature / 114-requirement Implementation-Plan.md (user: "proceed").',
            '- [x] Reconcile live project changes without restoring unrelated deleted items.',
            '- [x] Verify the approved source hashes and create a full-project pre-generation baseline (BASE-25, 7 items).',
            '- [x] Create 3 Hardware-Model-Viewer application folders and 12 feature-named requirement folders.',
            '- [x] Create and read back 12 Draft features and 114 Draft requirements with approved text and correct parents.',
            '- [x] Create and independently verify 114 Feature to Requirement Related to links and exactly one feature owner per requirement.',
            '- [x] Create the Implementation Summary and its 126 Related to links to all generated features and requirements.',
            '- [x] Verify 240 relationships, all generated item fields/statuses/locations, and preservation of pre-existing items.',
            '- [x] Copy the approved plan and these publication-time tasks/walkthrough into the summary.',
            '- [ ] Create and verify the full-project Post-Generate Features and Requirements baseline after the summary snapshot.', '',
            'The final baseline result is recorded in completion.json and completion.md after it exists. The copied documents describe the state at summary publication; they cannot truthfully claim that a later baseline already existed.', ''])
        lines = ['# Hardware Model Viewer Specification Walkthrough', '',
            'Publication snapshot: '+stamp()+'. All specification items and relationships below have passed read-back verification. The final project-root baseline follows this summary snapshot.', '',
            '## Scope and authorization', '',
            'Executed JCTK-TXT-5 (item 10686) in Jama Connect Tool Kit project 56 following user approval of Implementation-Plan.md. User-requested Hardware-Model-Viewer folders replace the prompt\'s stale TAF1APP destination references. The unavailable ad_jama transport was replaced with the existing REST client against the same authorized instance; Jamaland and JamOS were not used.', '',
            'The original planning inventory had 16 items. Unrelated items were removed externally before execution; the refreshed pre-generation snapshot contains the 7 then-current items. None was restored or modified by this execution.', '',
            '## Created structure', '',
            '| Set | Hardware-Model-Viewer folder |', '| --- | --- |']
        for label in ('features','requirements','summaries'):
            row = records['folder:'+label]
            lines.append(f'| {label.title()} | [{row["documentKey"]}]({self.item_link(row["id"])}) |')
        lines += ['', 'Features are directly under their application folder. Requirements are under their application folder and a subfolder matching the owning feature name. The summary is under the Implementation Summaries application folder.', '',
            '## Feature and requirement mapping', '',
            '| Plan | Feature | Requirement folder | Requirements |', '| --- | --- | --- | --- |']
        for feature in self.plan['features']:
            key = feature['key']; row = records[key]; folder = records['folder:'+key]
            reqs = [records[r['key']] for r in feature['requirements']]
            lines.append(f'| {key} | [{row["documentKey"]}: {row["name"]}]({self.item_link(row["id"])}) | [{folder["documentKey"]}]({self.item_link(folder["id"])}) | {len(reqs)}: '+', '.join(r['documentKey'] for r in reqs)+' |')
        summary = records['summary']
        lines += ['', f'Implementation Summary: [{summary["documentKey"]}]({self.item_link(summary["id"])}).', '',
            '## Verification and evidence', '',
            '- 12 features and 114 requirements use Draft option 292; names, descriptions, parent folders and item types match the approved plan.',
            '- All 114 requirements have exactly one upstream Feature through Related to (4). The summary also relates to each of the 126 generated specifications, giving 240 relationships total.',
            '- The 15 folders are confined to Features, Requirements, and Implementation Summaries. The 7 pre-existing items retain their original fields.',
            '- Pre-generation baseline BASE-25 was created with PROJECT origin 56. Its versioned-item IDs equal all 7 current project item IDs.',
            '- The approved working-tree source hashes still match code-snapshot.json. Existing 26-unit-test/browser checks and the two earlier live viewer-publication receipts are prior evidence; no new behavior was implemented or independently acceptance-tested in this documentation run.',
            '- execution-ledger.json records IDs, payloads, and resumable pending operations. verification-final.json records independent read-back results. Full-project post-baseline evidence is written after summary publication.', '',
            '## User-requested behavior reflected', '',
            'The generated specification covers the OSLC item launcher, delegated user session, collapsible model/GIF sections, direct single-item sections and nested multiple-item sections, free trackball plus independent X/Y/Z manipulation, published-run selection and downloads, ZIP-backed Jama assets, package validation and resumable publishing, attachment access safeguards, STEP preview conversion, offline deployment and legacy compatibility.', '',
            'The drawing UI and four-view export action remain removed. A logo present only as a Fusion decal is not recoverable from the geometry-only STEP export. MP4-to-GIF conversion was performed by external run tooling and is not claimed as a viewer feature. No arbitrary-format or unsaved CAD synchronization guarantee was added.', '',
            '## Limits and final operation', '',
            'These are code-derived Draft specifications. Verification/compliance fields were not populated as Passed. The mapped TIM also requires Requirement-to-Test-Case coverage; no Test Cases or Defects were generated, so full test coverage is not claimed.', '',
            'The local release builder can include deploy/Caddyfile.local in a native ZIP despite Git ignore rules. That existing packaging gap is recorded rather than silently changing application code. TLS trust and browser local-network permissions remain deployment prerequisites.', '',
            'The post-generation full-project baseline is created only after this summary and its copied documents are saved, as JCTK-TXT-5 requires. completion.json and completion.md record the resulting baseline ID and final outcome without modifying the captured Jama items afterward.', '']
        walkthrough = '\n'.join(lines)
        (OUT / 'tasks.md').write_text(tasks, encoding='utf-8')
        (OUT / 'walkthrough.md').write_text(walkthrough, encoding='utf-8')
        # Immutable local copies of exactly what the rich text contains.
        (OUT / 'summary-tasks.md').write_text(tasks, encoding='utf-8')
        (OUT / 'summary-walkthrough.md').write_text(walkthrough, encoding='utf-8')
        return tasks, walkthrough

    def summary(self):
        assert self.state.get('verified',{}).get('requirements') == 114
        self.inventory = self.j.paged('/items', {'project':56})
        # Make the summary concrete first so its IDs and relationships can be
        # verified before the final rich-text publication snapshot.
        initial = '<p>Hardware-Model-Viewer specification generation under approved JCTK-TXT-5: 12 Draft features and 114 Draft requirements. Publication documents are being finalized.</p>'
        if 'summary' not in self.state['items']:
            sid = self.ensure_item('summary',133,self.state['items']['folder:summaries']['id'],
                'Hardware-Model-Viewer Features and Requirements Generation 2026-10-27',initial)
        else:
            sid = self.state['items']['summary']['id']
        links = self.j.paged(f'/items/{sid}/downstreamrelationships')
        for feature in self.plan['features']:
            for row in [feature]+feature['requirements']:
                self.ensure_relationship(sid,self.state['items'][row['key']]['id'],links)
            print(f'Summary relationships verified for {feature["key"]}.',flush=True)
        self.verify()
        if self.state.get('summaryDocumentsVerified'):
            self.check_item(self.j.get(f'/items/{sid}'), self.state['items']['summary']['body'])
            return
        tasks, walkthrough = self.publication_documents()
        approved = (OUT / 'Implementation-Plan.md').read_text(encoding='utf-8')
        body = '<p>Generated under JCTK-TXT-5 following user approval: 12 Draft features, 114 Draft requirements, 15 folders, and 240 verified Related to relationships in project 56.</p><p>The following are verbatim publication-time copies. The approved plan retains its original planning language. The final project-root baseline follows this summary; its result is recorded separately in completion.json.</p>'
        for title, content in [('Approved Implementation Plan',approved),('Tasks at Summary Publication',tasks),('Walkthrough at Summary Publication',walkthrough)]:
            body += '<h2>'+title+'</h2><pre>'+html.escape(content)+'</pre>'
        desired = self.state['items']['summary']['body']
        desired['fields']['description'] = body
        current = self.j.get(f'/items/{sid}')
        if plain(current['fields']['description']) != plain(body):
            assert self.state['pending'] is None or self.state['pending'].get('key') == 'summary-description'
            self.state['pending'] = {'kind':'patch','key':'summary-description','item':sid,'descriptionSHA256':hashlib.sha256(body.encode()).hexdigest()}
            self.save()
            self.j.request('PATCH',f'/items/{sid}', json=[{'op':'replace','path':'/fields/description','value':body}])
        self.check_item(self.j.get(f'/items/{sid}'),desired)
        self.state['pending'] = None
        self.state['summaryDocumentsVerified'] = True
        self.save()
        save_json(OUT / 'summary-document-snapshot.json', {'item':sid, 'at':stamp(),
            'planSHA256':hashlib.sha256(approved.encode()).hexdigest(),
            'tasksSHA256':hashlib.sha256(tasks.encode()).hexdigest(),
            'walkthroughSHA256':hashlib.sha256(walkthrough.encode()).hexdigest()})
        self.verify()
        print(f'Summary {sid}: all three document copies and 126 links verified.',flush=True)

    def post(self):
        if self.state.get('status') == 'complete':
            print('Already complete; see completion.json for the verified receipt.',flush=True)
            return
        assert self.state.get('summaryDocumentsVerified'), 'Publish and verify the summary first'
        assert self.state['verified']['relationships'] == 240
        self.baseline('Post')
        bid = self.state['baselines']['Post']['id']
        baseline_rows = read('baseline-post-verified.json')['items']
        rows_by_id = {i['id']:i for i in baseline_rows}
        for entry in self.state['items'].values():
            saved = rows_by_id[entry['id']]
            assert saved['itemType'] == entry['body']['itemType']
            for field, value in entry['body']['fields'].items():
                actual = saved['fields'].get(field,'')
                assert (plain(actual) == plain(value) if field == 'description' else actual == value)
        frozen = []
        sources = [self.state['items'][f['key']]['id'] for f in self.plan['features']]
        sources.append(self.state['items']['summary']['id'])
        for source in sources:
            links = self.j.paged(f'/baselines/{bid}/versioneditems/{source}/versionedrelationships')
            expected = [r for r in self.state['relationships'].values() if r['fromItem'] == source]
            # Baseline references are [ID, version], including a versioned
            # relationship-type reference. Responses contain both directions.
            def ref(value):
                return value[0] if isinstance(value,list) else value
            actual = [r for r in links if ref(r['fromItem']) == source]
            assert {(ref(r['fromItem']),ref(r['toItem']),ref(r['relationshipType'])) for r in actual} == {
                (r['fromItem'],r['toItem'],r['relationshipType']) for r in expected}
            for row in actual:
                for field in ('fromItem','toItem'):
                    value = row[field]
                    if isinstance(value,list):
                        assert value[1] == rows_by_id[value[0]]['version'], 'Relationship points to the wrong frozen item version'
            frozen.extend(actual)
        assert len(frozen) == 240
        save_json(OUT / 'baseline-post-relationships.json', frozen)
        receipt = {'status':'complete', 'completedAt':stamp(),'project':56,'prompt':'JCTK-TXT-5',
            'features':12,'requirements':114,'folders':15,'summaries':1,'relationships':240,
            'eachRequirementHasExactlyOneFeature':True,'allSpecificationsDraft':True,
            'preBaseline':self.state['baselines']['Pre'],'postBaseline':self.state['baselines']['Post'],
            'postBaselineRelationshipCount':len(frozen),
            'summary':{k:v for k,v in self.state['items']['summary'].items() if k in ('id','documentKey','name')},
            'summaryUrl':self.item_link(self.state['items']['summary']['id']),
            'baselineApiUrls':{k:self.j.base+'/rest/latest/baselines/'+str(v['id']) for k,v in self.state['baselines'].items()},
            'applicationFolders':{k:self.item_link(self.state['items']['folder:'+k]['id']) for k in ('features','requirements','summaries')},
            'noPassedVerificationClaim':True,'fullTestCaseCoverageClaimed':False}
        save_json(OUT / 'completion.json',receipt)
        lines = ['# Hardware-Model-Viewer JCTK-TXT-5 Completion', '', 'Completed '+receipt['completedAt']+'.', '',
            f'Created and verified 12 Draft features, 114 Draft requirements, 15 folders, 1 Implementation Summary, and 240 Related to relationships in project 56. Each requirement has exactly one feature owner.', '',
            f'Implementation Summary: [{receipt["summary"]["documentKey"]}]({receipt["summaryUrl"]}).', '',
            f'Pre-generation baseline: BASE-{receipt["preBaseline"]["id"]}, all {receipt["preBaseline"]["verifiedCount"]} project items. Post-generation baseline: BASE-{bid}, all {receipt["postBaseline"]["verifiedCount"]} project items. Both have PROJECT origin 56. The final baseline also contains all 240 generated relationships and the exact saved item content.', '',
            '## Application folders', '']
        lines += [f'- [{k.title()}]({v})' for k,v in receipt['applicationFolders'].items()]
        lines += ['', '## Baseline API records', '']
        lines += [f'- [{k}-generation baseline]({v})' for k,v in receipt['baselineApiUrls'].items()]
        lines += ['', 'The summary contains the unchanged approved implementation plan and publication-time copies of tasks/walkthrough. summary-tasks.md and summary-walkthrough.md preserve those exact copies. This completion record and the final local task/walkthrough updates follow baseline creation; no Jama item was changed after the final snapshot.', '',
            'All generated specifications remain Draft. No compliance or acceptance verification fields were set to Passed, and no full test coverage claim was made.', '']
        (OUT / 'completion.md').write_text('\n'.join(lines),encoding='utf-8')
        tasks = (OUT / 'tasks.md').read_text(encoding='utf-8').replace(
            '- [ ] Create and verify the full-project Post-Generate Features and Requirements baseline after the summary snapshot.',
            f'- [x] Create and verify the full-project Post-Generate Features and Requirements baseline after the summary snapshot (BASE-{bid}, {len(baseline_rows)} items, 240 relationships).')
        tasks += '\nFinal completion: '+receipt['completedAt']+'. See completion.md. The verbatim Jama copy remains summary-tasks.md.\n'
        (OUT / 'tasks.md').write_text(tasks,encoding='utf-8')
        walkthrough = (OUT / 'walkthrough.md').read_text(encoding='utf-8')
        walkthrough += f'\n## Final completion after summary publication\n\nBASE-{bid} was created and verified at {receipt["completedAt"]}, capturing all {len(baseline_rows)} project items and all 240 generated relationships. No Jama items were modified afterward. See completion.md and completion.json. The verbatim Jama walkthrough remains summary-walkthrough.md.\n'
        (OUT / 'walkthrough.md').write_text(walkthrough,encoding='utf-8')
        self.state['status'] = 'complete'
        self.state['completedAt'] = receipt['completedAt']
        self.save()
        print(json.dumps({k:v for k,v in receipt.items() if k not in ('preBaseline','postBaseline')},indent=2),flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['preflight','pre','items','verify','summary','post'])
    args = p.parse_args()
    e = Execution()
    if args.stage == 'preflight': e.preflight()
    elif args.stage == 'pre': e.baseline('Pre')
    elif args.stage == 'post': e.post()
    else: getattr(e, args.stage)()

if __name__ == '__main__':
    main()
