"""Read-only discovery of the Jama Connect Tool Kit execution prompt."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODING = ROOT.parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from jama_model_viewer.jama_rest import Jama
from jama_model_viewer.core import save_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--project', type=int)
p.add_argument('--item', type=int)
p.add_argument('--schemas', action='store_true')
args = p.parse_args()
jama = Jama(argparse.Namespace(base_url='https://a-d-consulting.jamacloud.com',
    credentials=CODING / 'Requirements-to-Hardware/Scripts/info.json'))
output = ROOT / 'docs/jctk-2026-10-27'
output.mkdir(parents=True, exist_ok=True)
if args.schemas:
    schemas = {str(t): jama.get(f'/itemtypes/{t}') for t in (31, 32, 132, 24, 133)}
    rules = jama.paged('/relationshiprulesets')
    relationship_types = jama.paged('/relationshiptypes')
    project = jama.get('/projects/56')
    save_json(output / 'schemas.json', schemas)
    save_json(output / 'relationship-rule-sets.json', rules)
    save_json(output / 'relationship-types.json', relationship_types)
    options = jama.paged('/picklists/63/options')
    save_json(output / 'status-options.json', options)
    print(json.dumps({'statusOptions': options, 'ruleSets': rules}, indent=2))
elif args.item:
    item = jama.get(f'/items/{args.item}')
    save_json(output / f'item-{args.item}.json', item)
    print(json.dumps(item, indent=2))
elif args.project:
    project = jama.get(f'/projects/{args.project}')
    items = jama.paged('/items', {'project': args.project})
    save_json(output / 'project.json', project)
    save_json(output / 'items-before.json', items)
    print(json.dumps({'project': project, 'items': [
        {k: item.get(k) for k in ('id', 'documentKey', 'itemType', 'childItemType', 'location')} |
        {'name': item.get('fields', {}).get('name')} for item in items]}, indent=2))
else:
    projects = jama.paged('/projects')
    print(json.dumps([{'id': row['id'], 'name': row.get('fields', {}).get('name', row.get('name')), 'key': row.get('projectKey')}
        for row in projects if any(t in json.dumps(row).lower() for t in ('tool kit', 'toolkit', 'jctk', 'tool-kit'))], indent=2))
