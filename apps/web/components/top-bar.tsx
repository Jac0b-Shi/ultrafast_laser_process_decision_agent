"use client";

import { Database, FlaskConical, RefreshCcw, Settings } from "lucide-react";
import type { DatasetSummary, ModelInfo } from "@/types/api";

type Props = {
  summary: DatasetSummary | null;
  modelInfo: ModelInfo | null;
  onRefresh: () => void;
  currentPage: "workbench" | "data-management";
  onPageChange: (page: "workbench" | "data-management") => void;
};

export function TopBar({ summary, modelInfo, onRefresh, currentPage, onPageChange }: Props) {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-[1440px] mx-auto px-5 flex items-center justify-between gap-4 h-16">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-white shrink-0">
            <FlaskConical size={18} />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-gray-900 truncate">
              超快激光工艺决策智能体
            </h1>
            <p className="text-xs text-gray-500 truncate">
              基于实验数据的参数推荐与反馈闭环
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* page navigation */}
          <div className="flex items-center bg-gray-50 rounded-lg p-1 mr-2">
            <button
              onClick={() => onPageChange("workbench")}
              className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                currentPage === "workbench"
                  ? "bg-white text-primary font-medium shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              参数推荐
            </button>
            <button
              onClick={() => onPageChange("data-management")}
              className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                currentPage === "data-management"
                  ? "bg-white text-primary font-medium shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <span className="flex items-center gap-1">
                <Settings size={12} />
                数据管理
              </span>
            </button>
          </div>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-gray-50 text-gray-600 border border-gray-200">
            <Database size={12} />
            {summary?.total_samples ?? "-"} 条样本
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-primary-50 text-primary border border-primary-100">
            <FlaskConical size={12} />
            {summary?.materials.length ?? "-"} 类材料
          </span>
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-gray-50 text-gray-600 border border-gray-200">
            v{modelInfo?.model_version ?? "-"}
          </span>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            title="刷新数据"
          >
            <RefreshCcw size={12} />
            <span className="hidden sm:inline">刷新</span>
          </button>
        </div>
      </div>
    </header>
  );
}