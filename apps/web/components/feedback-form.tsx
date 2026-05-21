"use client";

import { Save } from "lucide-react";
import type { RecommendationResponse } from "@/types/api";

type Props = {
  result: RecommendationResponse | null;
  selectedRank: number | null;
  notes: string;
  feedbackLoading: boolean;
  onNotesChange: (notes: string) => void;
  onSubmit: () => void;
};

export function FeedbackForm({
  result,
  selectedRank,
  notes,
  feedbackLoading,
  onNotesChange,
  onSubmit,
}: Props) {
  const selectedRec =
    result && selectedRank !== null
      ? result.recommendations.find((r) => r.rank === selectedRank) ?? null
      : null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mt-4">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-900">反馈录入</h2>
      </div>

      <div className="p-5 space-y-4">
        {selectedRec ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">已选择：</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary-50 text-primary border border-primary-100">
              {selectedRec.generation_method === "ml_regression_fit"
                ? "机器学习拟合"
                : `推荐 #${selectedRec.rank}`}
            </span>
          </div>
        ) : (
          <p className="text-xs text-gray-400">请先在推荐结果中选择一条推荐</p>
        )}

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">实验备注</label>
          <textarea
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            rows={3}
            placeholder="记录实验观察、偏差原因等..."
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors resize-y"
          />
        </div>

        <button
          onClick={onSubmit}
          disabled={!selectedRec || feedbackLoading}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <Save size={14} />
          {feedbackLoading ? "写入中..." : "追加反馈"}
        </button>
      </div>
    </div>
  );
}