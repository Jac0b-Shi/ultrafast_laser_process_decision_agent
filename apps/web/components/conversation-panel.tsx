"use client";

import {KeyboardEvent, useEffect, useRef, useState} from "react";
import ImageAttachments, {ChatImage} from "@/components/image-attachments";
import AgentResultDetails from "@/components/agent-result-details";
import {DeviceConstraints} from "@/components/agent-fields";
import {metricLabel} from "@/lib/metric-display";
import {apiFetch} from "@/lib/api";

type Material={name:string;metrics:string[]};
type Model={id:string;name:string;default:boolean;supports_images:boolean;sale:Record<string,string>};
type Result={id:string;source:string;parameters:Record<string,number>;quality:Record<string,number>;match_score:number;similar_cases:{case_id:string}[];provider:{message:string};task:Record<string,unknown>};
type Turn={role?:string;text:string;assistant?:string;events?:{tool:string;summary:string;data?:Record<string,unknown>}[];task?:Task;recommendation?:Result;recommendation_id?:string;result?:Result};
type Task={material?:string;targets?:Record<string,{value?:number;tolerance?:number;operator?:string;unit?:string}>;algorithm?:string;constraints?:Record<string,unknown>};
const field="mt-1 w-full rounded-lg border bg-white p-2 text-sm";

export default function ConversationPanel({materials,models,conversation,onConversation,initial,onRefresh,busy,setBusy,setError}:{materials:Material[];models:Model[];conversation:string;onConversation:(id:string)=>void;initial:Turn[];onRefresh:()=>Promise<void>;busy:boolean;setBusy:(value:boolean)=>void;setError:(value:string)=>void}) {
 const [turns,setTurns]=useState<Turn[]>(initial),[message,setMessage]=useState(""),[images,setImages]=useState<ChatImage[]>([]),[modelId,setModelId]=useState(""),[task,setTask]=useState<Task>({targets:{},algorithm:"auto",constraints:{}}),[composing,setComposing]=useState(false);
 const end=useRef<HTMLDivElement>(null);
 const active=models.find(model=>modelId?model.id===modelId:model.default);
 useEffect(()=>{setTurns(initial);const last=[...initial].reverse().find(turn=>turn.task);if(last?.task)setTask(last.task);},[initial]);
 useEffect(()=>{if(!active?.supports_images)setImages([]);},[active?.supports_images]);
 useEffect(()=>end.current?.scrollIntoView({block:"end"}),[turns,busy]);
 function updateTarget(key:string, update:Record<string,unknown>){setTask(old=>({...old,targets:{...(old.targets??{}),[key]:{...(old.targets??{})[key],...update,unit:"um",operator:"eq"}}}));}
 function primary(){return Object.keys(task.targets??{})[0]??"depth_um";}
 async function send(forceRecommendation=false){
  if(!message.trim()&&!images.length&&!forceRecommendation)return;
  setBusy(true);setError("");
  try {
   let id=conversation;
   if(!id){id=(await apiFetch<{id:string}>("/api/agent/conversations",{method:"POST",body:"{}"})).id;onConversation(id);}
   const text=forceRecommendation ? (message.trim() || "请根据当前目标推荐一组加工参数") : message;
   const response=await apiFetch<{reply:string;task:Task;events:Turn["events"];recommendation?:Result}>(`/api/agent/conversations/${id}/turns`,{method:"POST",body:JSON.stringify({message:text,target_update:task,model_id:modelId||null,images,request_key:crypto.randomUUID()})});
   const turn:Turn={role:"user",text,assistant:response.reply,task:response.task,events:response.events,recommendation:response.recommendation};
   setTurns(old=>[...old,turn]);setTask(response.task);setMessage("");setImages([]);await onRefresh();
  } catch(error) {setError(error instanceof Error?error.message:"发送失败，草稿已保留。");}
  finally {setBusy(false);}
 }
 function keydown(event:KeyboardEvent<HTMLTextAreaElement>){if(event.key==="Enter"&&!event.shiftKey&&!composing){event.preventDefault();void send();}}
 const selected=primary(); const target=(task.targets??{})[selected]??{};
 return <section className="flex min-h-[calc(100vh-7rem)] flex-col">
  <header className="py-7"><p className="text-sm text-teal-800">超快激光加工工艺数据库智能体系统</p><h2 className="mt-2 text-3xl font-semibold">今天，想先讨论什么？</h2><p className="mt-3 text-stone-500">可以提问、补充加工目标或上传图片；需要数值参数时，我会调用案例与推荐工具。</p></header>
  <div className="flex-1 space-y-5 pb-52">{!turns.length&&<div className="rounded-2xl border bg-white p-6 text-stone-600">例如：“飞秒激光和皮秒激光有什么差别？”或“为 CFRP 加工深度 15 μm、容差 1 μm 推荐参数”。</div>}
  {turns.map((turn,index)=><article key={index} className="space-y-3"><div className="ml-auto max-w-3xl rounded-2xl bg-teal-800 px-5 py-3 text-white whitespace-pre-wrap">{turn.text}</div>{turn.assistant&&<div className="max-w-3xl rounded-2xl border bg-white p-5 whitespace-pre-wrap">{turn.assistant}</div>}{turn.events?.length?<details className="max-w-3xl rounded-xl border bg-stone-50 p-3 text-sm"><summary className="cursor-pointer text-teal-800">本轮工具与依据</summary><div className="mt-3 space-y-2">{turn.events.map((event,i)=><div key={i}><b>{event.tool}</b>：{event.summary}</div>)}</div></details>:null}{turn.recommendation&&<Recommendation result={turn.recommendation}/>}</article>)}</div>
  <div className="sticky bottom-3 z-10 rounded-2xl border bg-white p-4 shadow-lg"><details className="mb-3"><summary className="cursor-pointer text-sm text-teal-800">加工目标（可编辑）</summary><div className="mt-3 grid gap-3 md:grid-cols-5"><label className="text-xs">材料<select className={field} value={task.material??""} onChange={e=>setTask(old=>({...old,material:e.target.value,targets:{}}))}><option value="">选择材料</option>{materials.map(m=><option key={m.name}>{m.name}</option>)}</select></label><label className="text-xs">指标<select className={field} value={selected} onChange={e=>updateTarget(e.target.value,{})}>{(materials.find(m=>m.name===task.material)?.metrics??["depth_um"]).map(key=><option key={key} value={key}>{metricLabel(key)}</option>)}</select></label><label className="text-xs">目标 / μm<input className={field} type="number" min="0" value={target.value??""} onChange={e=>updateTarget(selected,{value:Number(e.target.value)})}/></label><label className="text-xs">容差 / μm<input className={field} type="number" min="0" value={target.tolerance??""} onChange={e=>updateTarget(selected,{tolerance:Number(e.target.value)})}/></label><label className="text-xs">算法<select className={field} value={task.algorithm??"auto"} onChange={e=>setTask(old=>({...old,algorithm:e.target.value}))}><option value="auto">自动选择</option></select></label></div><details className="mt-3"><summary className="text-sm text-stone-500">设备约束</summary><DeviceConstraints value={JSON.stringify(task.constraints??{})} onChange={value=>setTask(old=>({...old,constraints:JSON.parse(value)}))}/></details></details>
  <div className="flex items-end gap-3"><div className="flex-1"><textarea aria-label="对话输入" className="min-h-20 w-full resize-none outline-none" placeholder="输入问题或加工需求…（Enter 发送，Shift+Enter 换行）" value={message} onChange={e=>setMessage(e.target.value)} onCompositionStart={()=>setComposing(true)} onCompositionEnd={()=>setComposing(false)} onKeyDown={keydown}/><div className="mt-2 flex flex-wrap items-center gap-3"><select aria-label="AI 模型" className="rounded-lg border p-2 text-sm" value={modelId} onChange={e=>setModelId(e.target.value)}><option value="local">免费 · 本地确定性模式</option>{models.map(model=><option key={model.id} value={model.id}>{model.name}</option>)}</select>{active?.supports_images&&<ImageAttachments enabled value={images} onChange={setImages} onError={setError}/>} {active&&<details className="text-xs text-stone-500"><summary>模型费用说明</summary>输入 {active.sale.uncached}／百万 token，输出 {active.sale.output}／百万 token</details>}</div></div><div className="flex flex-col gap-2"><button className="rounded-xl border px-4 py-2 text-sm text-teal-800" disabled={busy} onClick={()=>void send(true)}>生成参数</button><button className="rounded-xl bg-teal-800 px-5 py-3 text-white disabled:opacity-40" disabled={busy||(!message.trim()&&!images.length)} onClick={()=>void send()}>{busy?"处理中…":"发送"}</button></div></div></div><div ref={end}/>
 </section>;
}

function Recommendation({result}:{result:Result}){return <article className="max-w-3xl space-y-4 rounded-2xl border bg-white p-5"><h3 className="font-semibold">{result.source==="historical"?"历史案例参数":"推荐参数"}<span className="float-right text-sm text-teal-800">匹配 {(result.match_score*100).toFixed(1)}%</span></h3><dl className="grid grid-cols-2 gap-2 md:grid-cols-3">{Object.entries(result.parameters).map(([key,value])=><div key={key} className="rounded-lg bg-stone-50 p-2"><dt className="text-xs text-stone-500">{metricLabel(key)}</dt><dd>{Number(value.toPrecision(6))}</dd></div>)}</dl><p className="text-sm text-stone-500">案例依据：{result.similar_cases.length} 条同材料实测记录</p><details><summary className="cursor-pointer text-sm text-teal-800">推荐逻辑、公式、训练信息与依据</summary><AgentResultDetails result={result}/></details></article>}
