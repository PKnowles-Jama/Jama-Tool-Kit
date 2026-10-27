import copy
import io
import json
import struct
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile
import http.client
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from jama_model_viewer.core import check_model, digest, local_file, read_json, save_json, validate_manifest
from jama_model_viewer.publisher import prepare, publish, validate_package
from jama_model_viewer.service import Reader, Rejected


class FakeJama:
    base = 'https://a-d-consulting.jamacloud.com'
    def __init__(self):
        self.objects = {}
        self.linked = []
        self.posts = 0
        self.lose_create = False
        self.lose_associate = False
    def get(self, path):
        if path == '/items/100':
            return {'id': 100, 'project': 53, 'fields': {'name': 'Summary'}}
        return self.objects[int(path.split('/')[2])]['meta']
    def paged(self, path, params=None):
        return [self.objects[i]['meta'] for i in self.linked]
    def request(self, method, path, **kw):
        if method == 'POST' and '/projects/' in path:
            self.posts += 1
            aid = self.posts
            self.objects[aid] = {'meta': {'id': aid, 'project': 53, 'fields': {**kw['json']['fields'], 'attachment': aid+1000}}}
            if self.lose_create:
                self.lose_create = False
                raise RuntimeError('Lost POST response')
            return {'meta': {'id': aid}}
        if method == 'PUT':
            aid = int(path.split('/')[2]);name, stream, mime = kw['files']['file'];data=stream.read()
            self.objects[aid]['data'] = data
            self.objects[aid]['meta'].update(fileName=name, fileSize=len(data), mimeType=mime)
            return {}
        if method == 'GET':
            url = kw['params']['url']
            aid = int(url.split('/attachment/')[1].split('/')[0])-1000
            return SimpleNamespace(content=self.objects[aid]['data'])
        if method == 'POST' and '/items/' in path:
            self.linked.append(kw['json']['attachment'])
            if self.lose_associate:
                self.lose_associate = False
                raise RuntimeError('Lost association response')
            return {}
        raise AssertionError((method,path))


class Packages(unittest.TestCase):
    def setUp(self):
        (ROOT / 'tests/output').mkdir(parents=True, exist_ok=True)
        self.run = (ROOT / 'tests/output' / ('run-' + str(uuid.uuid4()))).resolve()
        self.run.mkdir()
        save_json(self.run/'publish-state.json', {'summaryId':100,'complete':True,'pending':None})
        save_json(self.run/'summary-plan.json', {'baseUrl':FakeJama.base,'project':53})
        save_json(self.run/'coverage.json', {'source':'synthetic'})
        self.args = SimpleNamespace(run=self.run,model=ROOT/'frontend/demo/demo.glb',source=[],gif=[ROOT/'frontend/demo/motion.gif'],drawing=[ROOT/'frontend/demo/four-view.png'],document=[],revision='Test',units='m',up_axis='Y',projection='third-angle',drawing_kind='undimensioned-visualization',preflight=False)
        prepare(self.args)
    def tearDown(self):
        assert self.run.parent == (ROOT / 'tests/output').resolve()
        shutil.rmtree(self.run)
    def test_package_and_poster(self):
        m=validate_package(self.run)
        self.assertEqual(len(m['assets']),4)
        self.assertEqual(m['assets'][1]['poster'],'motion.gif.poster.png')
    def test_changed_artifact_stops_before_writes(self):
        (self.run/'viewer/demo.glb').write_bytes(b'changed')
        with self.assertRaises(ValueError):validate_package(self.run)
    def test_incomplete_summary(self):
        save_json(self.run/'publish-state.json',{'complete':False,'summaryId':100,'pending':None})
        with self.assertRaises(ValueError):validate_package(self.run)
    def test_source_snapshot_changed(self):
        save_json(self.run/'coverage.json', {'source':'changed'})
        with self.assertRaises(ValueError):validate_package(self.run)
    def test_publish_manifest_last_and_resume(self):
        jama=FakeJama();publish(self.args,jama)
        self.assertEqual(jama.posts,5)
        last=jama.objects[jama.linked[-1]]['meta']
        self.assertTrue(last['fields']['name'].startswith('JHMV manifest v1 '))
        publish(self.args,jama)
        self.assertEqual(jama.posts,5)
        self.assertEqual(len(jama.linked),5)
    def test_lost_create_does_not_duplicate(self):
        jama=FakeJama();jama.lose_create=True
        with self.assertRaises(RuntimeError):publish(self.args,jama)
        with self.assertRaises(ValueError):publish(self.args,jama)
        self.assertEqual(jama.posts,1)
        self.assertFalse(jama.linked)
    def test_lost_association_recovers_readback(self):
        jama=FakeJama();jama.lose_associate=True
        with self.assertRaises(RuntimeError):publish(self.args,jama)
        publish(self.args,jama)
        self.assertEqual(len(jama.linked),5)
        self.assertEqual(jama.posts,5)
    def test_preflight_has_no_writes(self):
        jama=FakeJama();self.args.preflight=True;publish(self.args,jama)
        self.assertEqual(jama.posts,0)
    def test_manifest_binding(self):
        m=read_json(ROOT/'frontend/demo/manifest.json')
        binding=copy.deepcopy(m['binding']);binding['itemId']=2
        with self.assertRaises(ValueError):validate_manifest(m,binding)
    def test_wrong_project_stops_publication(self):
        jama=FakeJama()
        with patch.object(jama,'get',return_value={'project':99}):
            with self.assertRaises(ValueError):publish(self.args,jama)
        self.assertEqual(jama.posts,0)


class Bounds(unittest.TestCase):
    def test_counted_attachment_pagination(self):
        r=Reader({'jamaOrigin':FakeJama.base,'maxAttachments':500},'test')
        payload=json.dumps({'data':[{'id':1}],'meta':{'pageInfo':{'startIndex':0,'totalResults':1}}}).encode()
        with patch.object(r,'request',return_value=payload) as request:
            self.assertEqual(r.attachments(100),[{'id':1}])
            self.assertEqual(request.call_count,1)
    def test_four_view_illustration(self):
        from jama_model_viewer.drawing import illustrate
        from PIL import Image
        (ROOT/'tests/output').mkdir(parents=True,exist_ok=True)
        output=ROOT/'tests/output'/('drawing-'+str(uuid.uuid4())+'.png')
        illustrate(ROOT/'frontend/demo/demo.glb',output)
        with Image.open(output) as image:
            self.assertEqual(image.size,(1800,1420))
            self.assertGreater(len(image.getcolors(100000) or []),3)
        output.unlink()
    def test_path_traversal(self):
        for name in ('../secret','C:secret','..','dir/file','dir\\file'):
            with self.assertRaises(ValueError):local_file('.',name)
    def test_external_glb(self):
        doc=json.dumps({'buffers':[{'uri':'https://untrusted.invalid/model.bin'}]}).encode();doc+=b' '*((-len(doc))%4)
        data=struct.pack('<IIIII',0x46546c67,2,20+len(doc),len(doc),0x4e4f534a)+doc
        with self.assertRaises(ValueError):check_model(data,'.glb')
    def test_3mf_xml_entities(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('3D/model.model','<!DOCTYPE a><model/>')
        with self.assertRaises(ValueError):check_model(data.getvalue(),'.3mf')
    def test_bad_glb(self):
        with self.assertRaises(ValueError):check_model(b'invalid','.glb')
    def test_asset_not_in_current_manifest(self):
        r=Reader({'jamaOrigin':FakeJama.base},'test')
        with patch.object(r,'context',return_value={'runs':[]}):
            with self.assertRaises(Rejected):r.asset({'runId':str(uuid.uuid4()),'name':'secret'})
    def test_item_project_mismatch(self):
        r=Reader({'jamaOrigin':FakeJama.base,'allowedProjectIds':[53]},'test')
        with patch.object(r,'get',return_value={'project':99}):
            with self.assertRaises(Rejected):r.context({'itemId':100,'projectId':53})


class AdapterHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from jama_model_viewer.server import handler
        from jama_model_viewer.service import load_config
        config=load_config(ROOT/'config/viewer.example.json')
        cls.origin=config['publicOrigin']
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler(config))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request('POST',path,json.dumps({'projectId':53,'itemId':100}),headers or {})
        response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read());connection.close();return result
    def test_rejects_wrong_origin(self):
        self.assertEqual(self.request('/api/context',{'Origin':'https://untrusted.invalid','Content-Type':'application/json','Authorization':'Bearer fake'})[0],403)
    def test_rejects_missing_token(self):
        self.assertEqual(self.request('/api/context',{'Origin':self.origin,'Content-Type':'application/json'})[0],401)
    def test_authenticated_read_and_headers(self):
        with patch.object(Reader,'context',return_value={'item':{'id':100},'runs':[]}):
            status,headers,data=self.request('/api/context',{'Origin':self.origin,'Content-Type':'application/json','Authorization':'Bearer synthetic'})
        self.assertEqual(status,200)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
        self.assertEqual(json.loads(data)['runs'],[])
    def test_not_a_general_proxy(self):
        self.assertEqual(self.request('/api/https://untrusted.invalid')[0],404)

if __name__=='__main__':unittest.main()
