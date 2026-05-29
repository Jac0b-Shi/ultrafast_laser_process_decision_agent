"use client";

import { History, Trash2, RotateCcw, Clock, ChevronRight } from "lucide-react";
import { formatScore } from "@/lib/utils";
import { metricLabel } from "@/lib/metric-display";
import type { HistoryEntry } from "@/lib/use-query-history";

type Props = {
  history: HistoryEntry[];
  onRestore: (entry: HistoryEntry) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();

  const time = d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  if (isToday) return `今天 ${time}`;

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();
  if (isYesterday) return `昨天 ${time}`;

  return `${d.getMonth() + 1}/${d.getDate()} ${time}`;
}

function methodLabel(method: string | null): string {
  if (!method) return "-";
  if (method === "ml_regression_fit") return "ML拟合";
  return "相似案例";
}

function QuerySummaryBadge({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-[11px]">
      <span className="text-gray-400">{label}</span>
      {value}
    </span>
  );
}

export function QueryHistoryPanel({ history, onRestore, onRemove, onClear }: Props) {
  if (history.length === 0) {
    return (
      <div className="py-12 text-center">
        <History size={32} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">暂无历史记录</p>
        <p className="text-xs text-gray-400 mt-1">每次生成推荐后将自动保存</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* header row */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">共 {history.length} 条记录（最近 50 条）</p>
        <button
          onClick={onClear}
          className="flex items-center gap-1 text-xs text-red-400 hover:text-red-600 transition-colors"
        >
          <Trash2 size={11} />
          清空
        </button>
      </div>

      {/* list */}
      <div className="space-y-2">
        {history.map((entry) => (
          <div
            key={entry.id}
            className="group relative rounded-lg border border-gray-100 bg-gray-50/50 hover:border-primary/30 hover:bg-primary-50/30 transition-colors"
          >
            <div className="px-3 py-2.5">
              {/* time + method */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
                  <Clock size={10} />
                  <span>{formatTime(entry.timestamp)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {entry.result.topScore !== null && (
                    <span className="text-[11px] font-mono font-semibold text-primary">
                      {formatScore(entry.result.topScore)}
                    </span>
                  )}
                  <span className="text-[11px] text-gray-400">
                    {methodLabel(entry.result.topMethod)}
                  </span>
                </div>
              </div>

              {/* material + query params */}
              <div className="flex flex-wrap gap-1 mb-2">
                <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-primary-50 text-primary text-[11px] font-medium border border-primary-100">
                  {entry.query.material || "未指定材料"}
                </span>
                <QuerySummaryBadge label="深度 " value={entry.query.targetDepth ? `${entry.query.targetDepth}μm` : ""} />
                <QuerySummaryBadge label="直径 " value={entry.query.targetDiameter ? `${entry.query.targetDiameter}μm` : ""} />
                <QuerySummaryBadge label="粗糙度≤" value={entry.query.maxRoughness ? `${entry.query.maxRoughness}μm` : ""} />
                <QuerySummaryBadge label="Top " value={entry.query.topK} />
              </div>

              {/* result stats */}
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] text-gray-400">
                  共 {entry.result.recommendationCount} 条推荐 · 数据集 {entry.result.datasetSize} 条
                </p>

                {/* action buttons */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => onRemove(entry.id)}
                    className="p-1 rounded text-gray-300 hover:text-red-400 transition-colors"
                    aria-label="删除此记录"
                  >
                    <Trash2 size={11} aria-hidden="true" />
                  </button>
                  <button
                    onClick={() => onRestore(entry)}
                    className="flex items-center gap-0.5 px-2 py-1 rounded bg-primary text-white text-[11px] font-medium hover:bg-primary-800 transition-colors"
                    aria-label="恢复此查询"
                  >
                    <RotateCcw size={10} aria-hidden="true" />
                    恢复
                  </button>
                </div>
              </div>

              {/* warning notes from result */}
              {entry.result.notes.length > 0 && (
                <details className="mt-2 group">
                  <summary className="flex items-center gap-1 text-[11px] text-amber-600 cursor-pointer select-none">
                    <ChevronRight size={10} className="transition-transform group-open:rotate-90" />
                    {entry.result.notes.length} 条提示
                  </summary>
                  <ul className="mt-1 space-y-0.5 pl-3">
                    {entry.result.notes.map((note, i) => (
                      <li key={i} className="text-[11px] text-amber-700 leading-relaxed">
                        ⚠ {note}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
