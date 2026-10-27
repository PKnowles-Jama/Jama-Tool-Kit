"""Offline orthographic illustration from baseline GLB; never a CAD drawing."""
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageDraw
from .core import check_model, MAX_FILE


def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):
    length=math.sqrt(dot(a,a))
    return tuple(x/length for x in a)


def illustrate(model, output, up_axis='Y', projection='third-angle'):
    model,output=Path(model),Path(output)
    if output.exists():raise ValueError('Drawing output already exists')
    if model.stat().st_size>MAX_FILE:raise ValueError('Model exceeds drawing size budget')
    data=model.read_bytes();check_model(data,'.glb')
    size=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+size])
    offset=20+size
    if len(data)<offset+8 or struct.unpack_from('<I',data,offset+4)[0]!=0x004e4942:raise ValueError('GLB needs an embedded binary chunk')
    binary=data[offset+8:]
    def accessor(index):
        a=doc['accessors'][index]
        if 'sparse' in a or a.get('normalized'):raise ValueError('Sparse/normalized accessors require CAD drawing export')
        view=doc['bufferViews'][a['bufferView']]
        if view.get('buffer',0)!=0:raise ValueError('Unexpected GLB buffer')
        types={5126:('f',4),5125:('I',4),5123:('H',2),5121:('B',1)}
        kind,width=types[a['componentType']];count={'VEC3':3,'SCALAR':1}[a['type']]
        stride=view.get('byteStride',count*width);start=view.get('byteOffset',0)+a.get('byteOffset',0)
        return [struct.unpack_from('<'+kind*count,binary,start+i*stride) for i in range(a['count'])]
    identity=[[1 if i==j else 0 for j in range(4)] for i in range(4)]
    def multiply(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    def transform(node):
        if 'matrix'in node:
            m=node['matrix'];return [[m[j*4+i] for j in range(4)] for i in range(4)]
        x,y,z,w=node.get('rotation',[0,0,0,1]);s=node.get('scale',[1,1,1]);t=node.get('translation',[0,0,0])
        r=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w], [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w], [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
        return [[r[i][j]*s[j] if j<3 else t[i] for j in range(4)] if i<3 else [0,0,0,1] for i in range(4)]
    faces=[];visited=0
    def walk(index,parent,chain):
        nonlocal visited
        if index in chain or len(chain)>100:raise ValueError('Cyclic or excessively deep GLB nodes')
        visited+=1
        if visited>10000:raise ValueError('Too many GLB nodes')
        n=doc['nodes'][index];world=multiply(parent,transform(n))
        if 'mesh'in n:
            for p in doc['meshes'][n['mesh']]['primitives']:
                if p.get('mode',4)!=4:raise ValueError('Drawing requires triangle primitives')
                if 'JOINTS_0'in p['attributes'] or p.get('targets'):raise ValueError('Deformed meshes require a CAD drawing export')
                positions=accessor(p['attributes']['POSITION']);vertices=[]
                for v in positions:
                    xyz=tuple(dot(row,(*v,1)) for row in world[:3])
                    if up_axis=='Z':xyz=(xyz[0],xyz[2],-xyz[1])
                    if not all(math.isfinite(x) for x in xyz):raise ValueError('Nonfinite geometry')
                    vertices.append(xyz)
                indices=[a[0] for a in accessor(p['indices'])] if 'indices'in p else list(range(len(vertices)))
                material=doc['materials'][p['material']] if 'material' in p else {}
                color=material.get('pbrMetallicRoughness',{}).get('baseColorFactor',[.35,.6,.65,1])
                for i in range(0,len(indices),3):
                    faces.append(([vertices[indices[i+j]] for j in range(3)],color))
                    if len(faces)>100000:raise ValueError('Drawing exceeds 100,000 triangles; simplify or export a CAD drawing')
        for child in n.get('children',[]):walk(child,world,chain|{index})
    for index in doc['scenes'][doc.get('scene',0)]['nodes']:walk(index,identity,set())
    if not faces:raise ValueError('No visible triangles for drawing')
    image=Image.new('RGB',(1800,1420),'white');draw=ImageDraw.Draw(image)
    draw.text((30,20),'UNDIMENSIONED VISUALIZATION - '+model.name,fill='#193043')
    draw.text((30,42),'Orthographic views; no manufacturing dimensions or tolerances. Projection: '+projection,fill='#516879')
    for slot,(label,direction) in enumerate([('ISOMETRIC',(3,2,3)),('FRONT',(0,0,1)),('TOP',(0,1,0)),('RIGHT',(1,0,0))]):
        forward=norm(direction);up=(0,0,-1) if label=='TOP' else (0,1,0);right=norm(cross(up,forward));vertical=cross(forward,right)
        projected=[([(dot(v,right),dot(v,vertical),dot(v,forward)) for v in face],color) for face,color in faces]
        xs=[p[0] for f,_ in projected for p in f];ys=[p[1] for f,_ in projected for p in f]
        minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys);scale=min(760/max(maxx-minx,1e-8),510/max(maxy-miny,1e-8))
        x0=30+(slot%2)*900;y0=95+(slot//2)*650
        draw.rectangle((x0,y0,x0+840,y0+610),outline='#cbd7df',width=2);draw.text((x0+15,y0+12),label,fill='#193043')
        cx=x0+420;cy=y0+325
        for face,color in sorted(projected,key=lambda f:sum(v[2] for v in f[0])):
            points=[(cx+(v[0]-(minx+maxx)/2)*scale,cy-(v[1]-(miny+maxy)/2)*scale) for v in face]
            a,b,c=face
            normal=cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))
            length=math.sqrt(dot(normal,normal))
            shade=.5+.5*abs(normal[2])/max(length,1e-12)
            fill=tuple(max(0,min(255,int(value*255*shade))) for value in color[:3])
            draw.polygon(points,fill=fill)
    draw.text((30,1390),'Four independent views; view labels define orientation. Original CAD remains the engineering source.',fill='#516879')
    image.save(output,'PNG')
