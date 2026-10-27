// Usage: node scripts/convert-step.cjs source.step preview.glb
const fs=require('node:fs');const path=require('node:path');
const occt=require('../frontend/vendor/occt/occt-import-js.js');
const {makeGLB}=require('../frontend/step-to-glb.cjs');
async function main(){const [, ,input,output]=process.argv;if(!input||!output||! /\.st(e)?p$/i.test(input)||! /\.glb$/i.test(output))throw Error('Usage: node scripts/convert-step.cjs source.step preview.glb');
  if(fs.statSync(input).size>50*1024*1024)throw Error('STEP exceeds 50 MiB');if(fs.existsSync(output))throw Error('Output exists; choose another filename.');
  const instance=await occt({locateFile:name=>path.join(__dirname,'../frontend/vendor/occt',name)});
  // Output meters and Y-up for GLB. OCCT preserves source component locations in meshes.
  const imported=instance.ReadStepFile(new Uint8Array(fs.readFileSync(input)),{linearUnit:'meter',linearDeflectionType:'bounding_box_ratio',linearDeflection:.001,angularDeflection:.5});
  for(const mesh of imported.meshes||[]){for(const kind of ['position','normal']){const a=mesh.attributes[kind]?.array;if(a)for(let i=0;i<a.length;i+=3){const y=a[i+1];a[i+1]=a[i+2];a[i+2]=-y;}}}
  const bytes=makeGLB(imported);fs.writeFileSync(output,bytes,{flag:'wx'});fs.writeFileSync(output+'.conversion.json',JSON.stringify({source:path.basename(input),output:path.basename(output),units:'m',upAxis:'Y',linearDeflection:.001,angularDeflection:.5,converter:'occt-import-js 0.0.23',warning:'Mesh visualization; verify dimensions, colors, placement and orientation against CAD.'},null,2));console.log('Created local GLB preview and conversion record.');}
const timer=setTimeout(()=>{console.error('STEP conversion exceeded 120 seconds.');process.exit(1);},120000);
main().then(()=>clearTimeout(timer)).catch(e=>{clearTimeout(timer);console.error(e.message);process.exitCode=1;});
