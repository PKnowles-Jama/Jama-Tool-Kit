"""Generate explicit synthetic fixtures without publishing them to Jama."""
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jama_model_viewer.core import save_json

ROOT = Path(__file__).resolve().parents[1] / 'frontend' / 'demo'
ROOT.mkdir(parents=True, exist_ok=True)
# A box is deliberately synthetic; it makes no claim of CAD requirement compliance.
vertices=[-.8,-.2,-.5, .8,-.2,-.5, .8,.2,-.5, -.8,.2,-.5, -.8,-.2,.5, .8,-.2,.5, .8,.2,.5, -.8,.2,.5]
indices=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,1,2,6,1,6,5,0,4,7,0,7,3]
binary=struct.pack('<24f',*vertices)+struct.pack('<36I',*indices)
doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],
 'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0}]}],
 'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[.05,.6,.65,1],'metallicFactor':.1,'roughnessFactor':.7},'doubleSided':True}],
 'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':96,'target':34962},{'buffer':0,'byteOffset':96,'byteLength':144,'target':34963}],
 'accessors':[{'bufferView':0,'componentType':5126,'count':8,'type':'VEC3','min':[-.8,-.2,-.5],'max':[.8,.2,.5]},{'bufferView':1,'componentType':5125,'count':36,'type':'SCALAR'}]}
text=json.dumps(doc).encode();text+=b' '*((-len(text))%4)
glb=struct.pack('<III',0x46546c67,2,28+len(text)+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary
(ROOT/'demo.glb').write_bytes(glb)
with zipfile.ZipFile(ROOT/'demo.3mf','w',zipfile.ZIP_DEFLATED) as archive:
    vertex_xml=''.join(f'<vertex x="{vertices[i]*1000}" y="{vertices[i+1]*1000}" z="{vertices[i+2]*1000}"/>' for i in range(0,len(vertices),3))
    triangle_xml=''.join(f'<triangle v1="{indices[i]}" v2="{indices[i+1]}" v3="{indices[i+2]}"/>' for i in range(0,len(indices),3))
    archive.writestr('3D/3dmodel.model','<?xml version="1.0"?><model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model"><mesh><vertices>'+vertex_xml+'</vertices><triangles>'+triangle_xml+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    archive.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/></Relationships>')
    archive.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
frames=[]
for x in (20,60,100,140,180):
    image=Image.new('RGB',(320,160),'#e7eef3');draw=ImageDraw.Draw(image);draw.text((12,10),'SYNTHETIC motion example',fill='#193043');draw.rectangle((x,60,x+70,110),fill='#098c96');frames.append(image)
frames[0].save(ROOT/'motion.gif',save_all=True,append_images=frames[1:],duration=200,loop=0)
frames[0].save(ROOT/'poster.png')
image=Image.new('RGB',(1000,760),'white');draw=ImageDraw.Draw(image);draw.text((20,15),'SYNTHETIC undimensioned four-view illustration',fill='black')
for label,x,y in [('ISOMETRIC',30,70),('FRONT',530,70),('TOP',30,420),('RIGHT',530,420)]:
    draw.text((x,y),label,fill='black');draw.rectangle((x+40,y+40,x+360,y+220),outline='#098c96',width=4)
image.save(ROOT/'four-view.png')
assets=[]
for name,role,mime in [('demo.glb','model','model/gltf-binary'),('motion.gif','animation','image/gif'),('poster.png','poster','image/png'),('four-view.png','drawing','image/png')]:
    data=(ROOT/name).read_bytes();assets.append({'name':name,'role':role,'mime':mime,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'attachmentId':len(assets)+1,'fileId':len(assets)+1})
assets[1]['poster']='poster.png'
save_json(ROOT/'manifest.json',{'schemaVersion':1,'status':'complete','runId':'00000000-0000-4000-8000-000000000001','revision':'Synthetic demo','publishedAt':'2026-10-27T12:00:00Z','createdAt':'2026-10-27T12:00:00Z','sourceSha256':'0'*64,'binding':{'jamaOrigin':'https://a-d-consulting.jamacloud.com','projectId':53,'itemId':1,'summaryId':1},'units':'m','upAxis':'Y','projection':'third-angle','drawingKind':'undimensioned-visualization','assets':assets})
print('Synthetic local demonstration generated.')
