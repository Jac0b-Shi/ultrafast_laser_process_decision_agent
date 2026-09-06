"use client";
import {useEffect,useState} from "react";
import {apiFetch} from "@/lib/api";
type SiteConfig={icp_number:string;icp_url:string;police_number:string;police_url:string};
export default function SiteFooter(){const [config,setConfig]=useState<SiteConfig|null>(null);useEffect(()=>{apiFetch<SiteConfig>("/api/site-config").then(setConfig).catch(()=>{});},[]);if(!config?.icp_number&&!config?.police_number)return null;return <footer className="border-t bg-white px-5 py-4 text-center text-xs text-stone-500">{config.icp_number&&<a className="hover:text-teal-800" href={config.icp_url} target="_blank" rel="noreferrer">{config.icp_number}</a>}{config.icp_number&&config.police_number&&<span className="mx-2">·</span>}{config.police_number&&<a className="hover:text-teal-800" href={config.police_url} target="_blank" rel="noreferrer">{config.police_number}</a>}</footer>}
