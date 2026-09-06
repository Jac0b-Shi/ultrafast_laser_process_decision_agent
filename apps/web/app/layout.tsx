import type { Metadata } from "next";
import type { ReactNode } from "react";
import "katex/dist/katex.min.css";
import "./globals.css";
import SiteFooter from "@/components/site-footer";

export const metadata: Metadata = {
  title: "超快激光加工工艺数据库智能体",
  description: "超快激光加工参数推荐与反馈闭环 MVP",
  formatDetection: {
    telephone: false,
    date: false,
    address: false,
    email: false,
    url: false,
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body suppressHydrationWarning><div className="min-h-screen flex flex-col"><div className="flex-1">{children}</div><SiteFooter/></div></body>
    </html>
  );
}
