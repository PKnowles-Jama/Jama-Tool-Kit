/* Local conversion helper shared with the Node CLI. occt-import-js stays separate. */
function makeGLB(result) {
  if (!result.success || !result.meshes?.length) throw Error('STEP import did not produce meshes.');
  const parts=[],views=[],accessors=[],meshes=[],materials=[];let length=0,triangles=0;
  function add(array,target,type,size){const data=new Uint8Array(array.buffer,array.byteOffset,array.byteLength);const aligned=(data.length+3)&~3;const block=new Uint8Array(aligned);block.set(data);parts.push(block);const view=views.length;views.push({buffer:0,byteOffset:length,byteLength:data.length,target});length+=aligned;const index=accessors.length;const accessor={bufferView:view,componentType:type,count:array.length/size,type:size===3?'VEC3':'SCALAR'};
    if(size===3){accessor.min=[Infinity,Infinity,Infinity];accessor.max=[-Infinity,-Infinity,-Infinity];for(let i=0;i<array.length;i++){const axis=i%3;accessor.min[axis]=Math.min(accessor.min[axis],array[i]);accessor.max[axis]=Math.max(accessor.max[axis],array[i]);}}
    accessors.push(accessor);return index;}
  for(const mesh of result.meshes){const pos=mesh.attributes.position.array,indices=mesh.index.array;triangles+=indices.length/3;if(triangles>1000000)throw Error('STEP exceeds one million preview triangles; simplify in CAD first.');if(pos.some(v=>!Number.isFinite(v)))throw Error('STEP contains invalid coordinates.');
    const attributes={POSITION:add(new Float32Array(pos),34962,5126,3)};
    if(mesh.attributes.normal)attributes.NORMAL=add(new Float32Array(mesh.attributes.normal.array),34962,5126,3);
    const material=materials.length;materials.push({pbrMetallicRoughness:{baseColorFactor:[...(mesh.color||[.55,.65,.72]),1],metallicFactor:.1,roughnessFactor:.7},doubleSided:true});meshes.push({name:mesh.name||'Part',primitives:[{attributes,indices:add(new Uint32Array(indices),34963,5125,1),material}]});}
  const doc={asset:{version:'2.0',generator:'Jama Hardware Model Viewer local STEP converter'},scene:0,scenes:[{nodes:meshes.map((_,i)=>i)}],nodes:meshes.map((_,i)=>({mesh:i})),meshes,materials,buffers:[{byteLength:length}],bufferViews:views,accessors};
  const json=new TextEncoder().encode(JSON.stringify(doc));const jsonSize=(json.length+3)&~3;const out=new Uint8Array(12+8+jsonSize+8+length);const v=new DataView(out.buffer);v.setUint32(0,0x46546c67,true);v.setUint32(4,2,true);v.setUint32(8,out.length,true);v.setUint32(12,jsonSize,true);v.setUint32(16,0x4e4f534a,true);out.fill(32,20,20+jsonSize);out.set(json,20);v.setUint32(20+jsonSize,length,true);v.setUint32(24+jsonSize,0x004e4942,true);let offset=28+jsonSize;for(const part of parts){out.set(part,offset);offset+=part.length;}return out;
}
module.exports={makeGLB};
