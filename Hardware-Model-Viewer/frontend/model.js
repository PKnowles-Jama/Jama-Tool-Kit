import * as THREE from './vendor/three/build/three.module.js';
import {OrbitControls} from './vendor/three/examples/jsm/controls/OrbitControls.js';
import {GLTFLoader} from './vendor/three/examples/jsm/loaders/GLTFLoader.js';
import {ThreeMFLoader} from './vendor/three/examples/jsm/loaders/3MFLoader.js';

export class ModelView {
  constructor(canvas,wrap,config){
    this.wrap=wrap;this.config=config;this.active=true;this.disposed=false;
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#e7eef3');
    this.camera=new THREE.PerspectiveCamera(38,1,.01,1000);this.controls=new OrbitControls(this.camera,canvas);this.controls.enableDamping=false;
    this.scene.add(new THREE.HemisphereLight(0xffffff,0x607080,2.5));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,5,4);this.scene.add(light);
    this.controls.addEventListener('change',()=>this.render());this.resize=new ResizeObserver(()=>this.render());this.resize.observe(wrap);
  }
  async load(bytes,asset,run){
    const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(url.startsWith('blob:'))return url;throw Error('External model resources are not permitted.');});
    let object;if(/\.glb$/i.test(asset.name)){
      const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);if(bytes.length<20||view.getUint32(0,true)!==0x46546c67||view.getUint32(4,true)!==2||view.getUint32(8,true)!==bytes.length)throw Error('Invalid GLB.');
      const size=view.getUint32(12,true);if(size>bytes.length-20)throw Error('Invalid GLB JSON chunk.');const doc=JSON.parse(new TextDecoder().decode(bytes.slice(20,20+size)));
      if(doc.extensionsUsed?.length||[...(doc.buffers||[]),...(doc.images||[])].some(e=>'uri'in e))throw Error('Export a self-contained uncompressed GLB without extensions.');
      object=(await new GLTFLoader(manager).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
    }else{
      const {unzipSync}=await import('./vendor/three/examples/jsm/libs/fflate.module.js');
      // Validate central directory sizes before decompression to bound ZIP allocation.
      const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let end=-1;for(let i=bytes.length-22;i>=Math.max(0,bytes.length-65557);i--)if(v.getUint32(i,true)===0x06054b50){end=i;break;}
      if(end<0)throw Error('Invalid 3MF archive.');const count=v.getUint16(end+10,true);let off=v.getUint32(end+16,true),expanded=0;if(count>1000)throw Error('3MF has too many entries.');
      for(let n=0;n<count;n++){if(off+46>bytes.length||v.getUint32(off,true)!==0x02014b50)throw Error('Invalid 3MF directory.');const compressed=v.getUint32(off+20,true),size=v.getUint32(off+24,true);expanded+=size;if(expanded>this.config.maxExpandedBytes||size/Math.max(1,compressed)>1000)throw Error('3MF expansion limit exceeded.');off+=46+v.getUint16(off+28,true)+v.getUint16(off+30,true)+v.getUint16(off+32,true);}
      const files=unzipSync(bytes);for(const [name,data] of Object.entries(files))if(/\.(model|rels)$/i.test(name)&&/<!DOCTYPE|<!ENTITY|TargetMode\s*=\s*["']External/i.test(new TextDecoder().decode(data)))throw Error('3MF external references are not permitted.');
      object=new ThreeMFLoader(manager).parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
    }
    if(this.disposed){disposeObject(object);return;}
    let triangles=0;object.traverse(node=>{if(node.isMesh){triangles+=(node.geometry.index?.count||node.geometry.attributes.position?.count||0)/3;for(const mat of Array.isArray(node.material)?node.material:[node.material])for(const value of Object.values(mat))if(value?.isTexture){const image=value.image;if(image&&image.width*image.height>this.config.maxTexturePixels)throw Error('Texture budget exceeded.');}}});
    if(triangles>this.config.maxTriangles){disposeObject(object);throw Error('Triangle budget exceeded; publish a simplified preview.');}
    // Normalize display extents only; original units remain explicit in the manifest.
    if(run.upAxis==='Z')object.rotation.x=-Math.PI/2;
    object.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(object),size=box.getSize(new THREE.Vector3()),extent=Math.max(size.x,size.y,size.z);
    if(!Number.isFinite(extent)||extent<=0){disposeObject(object);throw Error('Model has no visible geometry.');}
    const center=box.getCenter(new THREE.Vector3());object.position.sub(center);object.scale.multiplyScalar(2/extent);object.position.multiplyScalar(2/extent);this.scene.add(object);this.object=object;this.view('iso');
  }
  view(name){const directions={iso:[3,2.2,3],front:[0,0,4],top:[0,4,.001],right:[4,0,0],fit:[3,2.2,3]};this.camera.up.set(0,1,0);this.camera.position.set(...directions[name]);this.controls.target.set(0,0,0);this.controls.update();this.render();}
  render(){if(!this.active||this.disposed||document.hidden)return;const w=this.wrap.clientWidth,h=this.wrap.clientHeight;if(!w||!h)return;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.render(this.scene,this.camera);}
  sheet(){const sheet=document.createElement('canvas');sheet.width=1600;sheet.height=1240;const ctx=sheet.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,1600,1240);ctx.fillStyle='#193043';ctx.font='24px sans-serif';ctx.fillText('Undimensioned visualization · Isometric / Front / Top / Right',24,36);const old=this.camera.position.clone();let n=0;for(const name of ['iso','front','top','right']){this.view(name);const x=(n%2)*800,y=Math.floor(n/2)*580+60;ctx.drawImage(this.renderer.domElement,x,y,800,530);ctx.fillStyle='#193043';ctx.fillText(name.toUpperCase(),x+20,y+560);n++;}this.camera.position.copy(old);this.controls.update();this.render();return new Promise(resolve=>sheet.toBlob(resolve,'image/png'));}
  dispose(){this.disposed=true;this.resize.disconnect();this.controls.dispose();if(this.object)disposeObject(this.object);this.renderer.dispose();}
}
function disposeObject(object){object.traverse(n=>{n.geometry?.dispose();for(const m of Array.isArray(n.material)?n.material:(n.material?[n.material]:[])){for(const value of Object.values(m))if(value?.isTexture){value.image?.close?.();value.dispose();}m.dispose();}});}
