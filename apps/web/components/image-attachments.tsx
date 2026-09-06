"use client";
import {useRef} from "react";

export type ChatImage={name:string;media_type:"image/jpeg"|"image/png"|"image/gif"|"image/webp";data:string};
const allowed=new Set<ChatImage["media_type"]>(["image/jpeg","image/png","image/gif","image/webp"]);

function read(file:File):Promise<ChatImage>{
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onerror=()=>reject(new Error(`无法读取图片：${file.name}`));
  reader.onload=()=>{
   const value=String(reader.result??"");
   const comma=value.indexOf(",");
   if(comma<0)return reject(new Error(`图片编码失败：${file.name}`));
   resolve({name:file.name,media_type:file.type as ChatImage["media_type"],data:value.slice(comma+1)});
  };
  reader.readAsDataURL(file);
 });
}

export default function ImageAttachments({enabled,value,onChange,onError}:{enabled:boolean;value:ChatImage[];onChange:(images:ChatImage[])=>void;onError:(message:string)=>void}){
 const input=useRef<HTMLInputElement>(null);
 if(!enabled)return null;
 return <div className="space-y-2">
  <label className="text-sm text-stone-600">图片输入（JPEG、PNG、GIF、WebP；最多 4 张，单张 10 MB、合计 20 MB）
   <input ref={input} className="block mt-2" type="file" accept="image/jpeg,image/png,image/gif,image/webp" multiple onChange={e=>{const files=Array.from(e.target.files??[]);e.target.value="";void (async()=>{
    if(value.length+files.length>4)return onError("最多上传 4 张图片");
    if(files.some(f=>!allowed.has(f.type as ChatImage["media_type"])))return onError("仅支持 JPEG、PNG、GIF 和 WebP 图片");
    if(files.some(f=>f.size>10*1024*1024))return onError("单张图片不能超过 10 MB");
    if(value.reduce((n,image)=>n+Math.floor(image.data.length*3/4),0)+files.reduce((n,file)=>n+file.size,0)>20*1024*1024)return onError("图片总大小不能超过 20 MB");
    try{onChange([...value,...await Promise.all(files.map(read))]);}catch(error){onError(error instanceof Error?error.message:"图片读取失败");}
   })();}}/>
  </label>
  {value.length>0&&<div className="flex flex-wrap gap-2">{value.map((image,index)=><span key={`${image.name}-${index}`} className="border rounded-lg px-3 py-2 text-sm">{image.name}<button type="button" className="ml-2 text-red-700" aria-label={`移除 ${image.name}`} onClick={()=>onChange(value.filter((_,i)=>i!==index))}>×</button></span>)}</div>}
 </div>;
}
