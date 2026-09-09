"use client";
import {useEffect, useState} from "react";
import {apiFetch} from "@/lib/api";
import AuthScreen from "@/components/auth-screen";
import AuthenticatedSidebar from "@/components/authenticated-sidebar";
import ConversationPanel from "@/components/conversation-panel";
import FeedbackRecord from "@/components/feedback-record";
import AdminConsole from "@/components/admin-console";
import AccountPanel from "@/components/account-panel";
import ProcessAnalysis from "@/components/process-analysis";

type User={id:string;username:string;admin:boolean;email?:string|null;avatar_url?:string|null};
type Material={name:string;metrics:string[]}; type Model={id:string;name:string;default:boolean;supports_images:boolean;sale:Record<string,string>};
type Item={id:string;name?:string;title?:string;scope?:string;material?:string;quality?:Record<string,number>;deleted_at?:string};
type Turn={role?:string;text:string;assistant?:string;events?:{tool:string;summary:string;data?:Record<string,unknown>}[];task?:Record<string,unknown>;recommendation?:any;result?:any};
const post=(body:unknown)=>({method:"POST",body:JSON.stringify(body)});

export default function AgentHome(){
 const [user,setUser]=useState<User|null>(null),[page,setPage]=useState("chat"),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [materials,setMaterials]=useState<Material[]>([]),[models,setModels]=useState<Model[]>([]),[history,setHistory]=useState<Item[]>([]),[items,setItems]=useState<Item[]>([]),[conversation,setConversation]=useState(""),[turns,setTurns]=useState<Turn[]>([]);
 async function run(action:()=>Promise<void>){setBusy(true);setError("");try{await action();}catch(e){setError(e instanceof Error?e.message:"操作失败");}finally{setBusy(false);}}
 async function refresh(){const [m,h,modelList]=await Promise.all([apiFetch<Material[]>("/api/agent/materials"),apiFetch<Item[]>("/api/agent/conversations"),apiFetch<Model[]>("/api/agent/models")]);setMaterials(m);setHistory(h);setModels(modelList);}
 useEffect(()=>{apiFetch<User>("/api/agent/me").then(setUser).catch(()=>{});},[]);
 useEffect(()=>{if(user)void run(refresh);},[user]); // eslint-disable-line react-hooks/exhaustive-deps
 async function open(pageName:string){setPage(pageName);if(pageName==="data"||pageName==="trash")setItems(await apiFetch(`/api/agent/feedback?trash=${pageName==="trash"}`));if(pageName==="knowledge")setItems(await apiFetch("/api/agent/knowledge"));}
 async function openHistory(id:string){const item=await apiFetch<{messages:Turn[]}>(`/api/agent/conversations/${id}`);setConversation(id);setTurns(item.messages);setPage("chat");}
 if(!user)return <AuthScreen onLogin={setUser}/>;
 return <div className="min-h-screen bg-[#fafaf8] text-stone-800 md:flex"><AuthenticatedSidebar user={user} busy={busy} page={page} history={history} onNewTask={()=>{setConversation("");setTurns([]);setPage("chat");setError("");setNotice("");}} onOpen={next=>void run(()=>open(next))} onOpenHistory={id=>void run(()=>openHistory(id))} onLogout={()=>void run(async()=>{await apiFetch("/api/agent/logout",post({}));setUser(null);setConversation("");setTurns([]);})}/><main className="mx-auto w-full max-w-5xl flex-1 px-5 py-6 md:ml-64 md:px-12">{error&&<p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}{notice&&<p role="status" className="mb-4 rounded-xl bg-teal-50 p-4">{notice}</p>}
 {page==="chat"&&<ConversationPanel materials={materials} models={models} conversation={conversation} onConversation={setConversation} initial={turns} onRefresh={refresh} busy={busy} setBusy={setBusy} setError={setError}/>}
 {page==="analysis"&&<ProcessAnalysis materials={materials} busy={busy} setBusy={setBusy} setError={setError}/>}
 {(page==="data"||page==="trash")&&<section><h2 className="mb-4 text-2xl font-semibold">{page==="trash"?"回收站":"我的加工反馈"}</h2><p className="mb-6 text-stone-500">反馈仅以追加事件保存；删除后退出推荐数据，30 天内可恢复。</p>{!items.length&&<p>暂无记录</p>}{items.map(item=><FeedbackRecord key={item.id} record={item} trash={page==="trash"} busy={busy} run={run} refresh={()=>open(page)}/>)}</section>}
 {page==="knowledge"&&<section className="space-y-5"><h2 className="text-2xl font-semibold">知识文件</h2><p className="text-stone-500">文件只用作检索资料，不能执行代码或扩展工具权限。</p><input aria-label="上传知识文件" type="file" accept=".pdf,.docx,.md,.txt" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void run(async()=>{const form=new FormData();form.append("file",file);const response=await fetch("/api/agent/knowledge",{method:"POST",body:form});if(!response.ok)throw new Error((await response.json()).detail);await open("knowledge");});}}/>{items.map(item=><div key={item.id} className="flex justify-between rounded-xl border bg-white p-4"><a href={`/api/agent/knowledge/${item.id}/download`}>{item.name}</a><span>{item.scope==="public"?"公共":"个人"}</span></div>)}</section>}
 {page==="admin"&&user.admin&&<AdminConsole materials={materials.map(m=>m.name)}/>} {(page==="wallet"||page==="profile")&&<AccountPanel page={page} user={user} onUpdate={async()=>setUser(await apiFetch<User>("/api/agent/me"))}/>}</main></div>;
}
