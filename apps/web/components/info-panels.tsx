"use client";

import { Cpu, Database, BarChart3, History } from "lucide-react";
import { metricLabel } from "@/lib/metric-display";
import type { DatasetSummary, ModelInfo } from "@/types/api";
import type { HistoryEntry } from "@/lib/use-query-history";
import { QueryHistoryPanel } from "./query-history-panel";

type Props = {
  summary: DatasetSummary | null;
  modelInfo: ModelInfo | null;
  activeTab: string;
  onTabChange: (tab: string) => void;
  resultCount: number;
  history: HistoryEntry[];
  onRestoreHistory: (entry: HistoryEntry) => void;
  onRemoveHistory: (id: string) => void;
  onClearHistory: () => void;
};

const TABS = [
  { id: "results", label: "推荐结果" },
  { id: "history", label: "历史记录" },
  { id: "data", label: "数据概览" },
  { id: "model", label: "模型信息" },
];

export function InfoPanels({
  summary,
  modelInfo,
  activeTab,
  onTabChange,
  resultCount,
  history,
  onRestoreHistory,
  onRemoveHistory,
  onClearHistory,
}: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* tabs */}
      <div className="flex border-b border-gray-100 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 min-w-[80px] px-4 py-3 text-sm font-medium transition-colors relative whitespace-nowrap ${
              activeTab === tab.id
                ? "text-primary"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
            {tab.id === "results" && resultCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-xs">
                {resultCount}
              </span>
            )}
            {tab.id === "history" && history.length > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded-full bg-gray-100 text-gray-600 text-xs">
                {history.length}
              </span>
            )}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* tab content */}
      <div className="p-5">
        {activeTab === "model" && (
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-50 text-primary">
                <Cpu size={16} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{modelInfo?.model_type ?? "未加载"}</p>
                <p className="text-xs text-gray-500">版本 {modelInfo?.model_version ?? "-"}</p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-3">
                <span className="block text-xs text-gray-400 mb-1">训练范围</span>
                <p className="text-sm text-gray-700">{modelInfo?.training_scope ?? "-"}</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-3">
                <span className="block text-xs text-gray-400 mb-1">外推策略</span>
                <p className="text-sm text-gray-700">{modelInfo?.extrapolation_policy ?? "-"}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "data" && (
          <div className="space-y-3">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-50 text-accent">
                <Database size={16} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  共 {summary?.total_samples ?? 0} 条样本
                </p>
                <p className="text-xs text-gray-500">
                  含 {summary?.feedback_samples ?? 0} 条反馈 · {summary?.materials.length ?? 0} 类材料
                </p>
              </div>
            </div>

            {summary?.materials.map((m) => (
              <div
                key={m.material}
                className="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50/50"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">{m.material}</p>
                  <p className="text-xs text-gray-400 truncate">
                    {m.quality_metrics.map(metricLabel).join(", ") || "暂无质量指标"}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-3">
                  <span className="text-sm font-semibold text-primary">{m.sample_count}</span>
                  <span className="text-xs text-gray-400">条</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "results" && resultCount === 0 && (
          <div className="py-12 text-center">
            <BarChart3 size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">尚未生成推荐</p>
            <p className="text-xs text-gray-400 mt-1">在左侧填写任务目标后点击"生成推荐"</p>
          </div>
        )}

        {activeTab === "history" && (
          <QueryHistoryPanel
            history={history}
            onRestore={onRestoreHistory}
            onRemove={onRemoveHistory}
            onClear={onClearHistory}
          />
        )}
      </div>
    </div>
  );
}
