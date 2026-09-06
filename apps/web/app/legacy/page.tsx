"use client";
import Link from "next/link";
import {useCallback,useEffect,useState} from "react";
import {apiFetch} from "@/lib/api";
import {TopBar} from "@/components/top-bar";
import {Workbench} from "@/components/workbench";
import type {DatasetSummary,ModelInfo} from "@/types/api";

export default function LegacyPage(){const [summary,setSummary]=useState<DatasetSummary|null>(null),[modelInfo,setModelInfo]=useState<ModelInfo|null>(null),[error,setError]=useState("");const refresh=useCallback(async()=>{setError("");try{const [s,m]=await Promise.all([apiFetch<DatasetSummary>("/api/datasets/summary"),apiFetch<ModelInfo>("/api/recommendations/public/model-info")]);setSummary(s);setModelInfo(m);}catch(e){setError(e instanceof Error?e.message:"加载失败");}},[]);useEffect(()=>{void refresh();},[refresh]);return <div><TopBar summary={summary} modelInfo={modelInfo} onRefresh={()=>void refresh()} currentPage="workbench" onPageChange={()=>{}} showDataManagement={false}/><div className="bg-amber-50 border-b border-amber-200 px-5 py-3 text-sm text-amber-950"><div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-3"><span>免登录旧版推荐，仅使用公共数据，用于与新版智能体对比；不保存反馈或个人文件。</span><Link className="underline" href="/">返回新版登录</Link></div></div>{error&&<p role="alert" className="m-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}<Workbench summary={summary} modelInfo={modelInfo} onRefresh={()=>void refresh()} recommendationPath="/api/recommendations/public" allowFeedback={false}/></div>}
