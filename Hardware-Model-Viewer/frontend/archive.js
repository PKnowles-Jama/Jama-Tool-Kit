import {unzipSync} from './vendor/three/examples/jsm/libs/fflate.module.js';
export function unpack(data,name,limit,expectedBytes){
  const view=new DataView(data.buffer,data.byteOffset,data.byteLength);let end=-1;
  for(let i=data.length-22;i>=Math.max(0,data.length-65557);i--)if(view.getUint32(i,true)===0x06054b50){end=i;break;}
  if(end<0||view.getUint16(end+10,true)!==1)throw Error('Expected one ZIP artifact.');
  const off=view.getUint32(end+16,true);
  if(off+46>data.length||view.getUint32(off,true)!==0x02014b50||view.getUint16(off+8,true)&1)throw Error('Invalid ZIP container.');
  const size=view.getUint32(off+24,true);if(size<1||size>limit||expectedBytes!==undefined&&size!==expectedBytes)throw Error('ZIP expanded length exceeds its budget or differs from manifest.');
  const files=unzipSync(data),names=Object.keys(files);if(names.length!==1||names[0]!==name)throw Error('ZIP does not contain exactly the expected artifact.');
  return files[name];
}
