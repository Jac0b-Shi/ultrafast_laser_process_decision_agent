"use client";
import {useEffect,useState} from "react";
import {apiFetch} from "@/lib/api";
type Legacy={legacy_id:string;payload:Record<string,unknown>};
export default function LegacyClaims(){
 const [items,setItems]=useState<Legacy[]>([]),[username,setUsername]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false);
 const refresh=async()=>setItems(await apiFetch<Legacy[]>("/api/agent/legacy-feedback"));
 useEffect(()=>{void refresh().catch(e=>setNotice(String(e)));},[]);
 return <section className="mt-10 space-y-4"><h3 className="text-xl font-semibold">旧反馈待认领</h3><p className="text-sm text-stone-500">无归属的旧记录仅管理员可见，核对后分配给原始提交者。</p><input aria-label="认领账号" className="border rounded-xl p-3" placeholder="目标用户名" value={username} onChange={e=>setUsername(e.target.value)}/>{notice&&<p role="status">{notice}</p>}{!items.length&&<p className="text-sm">暂无待认领记录</p>}{items.map(item=><article key={item.legacy_id} className="border bg-white rounded-xl p-4"><details><summary>查看原始反馈</summary><pre className="text-xs whitespace-pre-wrap">{JSON.stringify(item.payload,null,2)}</pre></details><button className="mt-3 text-teal-800" disabled={busy||!username.trim()} onClick={async()=>{setBusy(true);try{await apiFetch(`/api/agent/legacy-feedback/${item.legacy_id}/claim`,{method:"POST",body:JSON.stringify({username})});await refresh();setNotice("已分配，原始文件保留。");}catch(e){setNotice(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}}>分配给此账号</button></article>)}</section>;
}
