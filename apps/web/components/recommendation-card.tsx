"use client";

import { BlockMath } from "react-katex";
import {
  formatMetricText,
  getMetricDisplay,
  metricLabel,
  SCORE_EXPLANATION,
  SCORE_FORMULAS,
} from "@/lib/metric-display";
import { formatValue, formatScore } from "@/lib/utils";
import type { Recommendation } from "@/types/api";

function MetricGrid({ values, columns }: { values: Record<string, number>; columns?: number }) {
  const entries = Object.entries(values);
  if (entries.length === 0) return <p className="text-xs text-gray-400">暂无数据</p>;

  return (
    <div
      className="grid gap-2"
      style={{ gridTemplateColumns: `repeat(${columns ?? 3}, minmax(0, 1fr))` }}
    >
      {entries.map(([key, value]) => (
        <div className="kv-cell" key={key}>
          <span className="kv-cell-label">{metricLabel(key)}</span>
          <strong className="kv-cell-value">{formatValue(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function FormulaMetricGrid({ values }: { values: Record<string, number> }) {
  const entries = Object.entries(values);
  if (entries.length === 0) return <p className="text-xs text-gray-400">暂无中间量</p>;

  return (
    <div className="grid grid-cols-2 gap-2">
      {entries.map(([key, value]) => {
        const metric = getMetricDisplay(key);
        return (
          <div className="formula-card" key={key}>
            <span className="block text-xs text-gray-500 truncate">{metricLabel(key)}</span>
            {metric.formula ? (
              <div className="mt-1.5 overflow-x-auto">
                <BlockMath
                  math={`${metric.formula} = ${(() => {
                    if (!Number.isFinite(value)) return String.raw`\text{不可用}`;
                    const abs = Math.abs(value);
                    if (abs !== 0 && (abs < 0.001 || abs >= 1_000_000)) {
                      const [m, e] = value.toExponential(3).split("e");
                      return String.raw`${m} \times 10^{${Number(e)}}`;
                    }
                    if (Number.isInteger(value)) return String(value);
                    return String(Number(value.toFixed(4)));
                  })()}`}
                  renderError={() => <code>{`${metric.formula} = ${formatValue(value)}`}</code>}
                />
              </div>
            ) : (
              <strong className="block mt-2 text-sm text-gray-900">{formatValue(value)}</strong>
            )}
            {metric.variables && (
              <p className="mt-2 text-[11px] text-gray-400 leading-relaxed">{metric.variables}</p>
            )}
            {metric.note && (
              <p className="mt-1 text-[11px] text-gray-400 leading-relaxed">{metric.note}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SimilarCases({ cases }: { cases: Recommendation["similar_cases"] }) {
  if (cases.length === 0) {
    return <p className="text-xs text-gray-400 py-4 text-center">暂无相似案例依据</p>;
  }

  return (
    <div className="space-y-3">
      {cases.map((item) => (
        <details key={item.case_id} className="group border border-gray-100 rounded-lg bg-gray-50/50">
          <summary className="flex items-center justify-between gap-2 px-3 py-2.5 cursor-pointer select-none">
            <span className="text-sm font-medium text-gray-700">{item.case_id}</span>
            <span className="text-xs text-primary font-mono">相似度 {formatScore(item.score)}</span>
          </summary>
          <div className="px-3 pb-3 space-y-3">
            <p className="text-xs text-gray-500">
              {item.material} · {item.source_file}
              {item.source_row ? ` :${item.source_row}` : ""}
            </p>
            <div>
              <h5 className="text-xs font-medium text-gray-600 mb-1.5">案例参数</h5>
              <MetricGrid values={item.parameters} />
            </div>
            <div>
              <h5 className="text-xs font-medium text-gray-600 mb-1.5">案例中间量</h5>
              <FormulaMetricGrid values={item.intermediate_metrics} />
            </div>
            <div>
              <h5 className="text-xs font-medium text-gray-600 mb-1.5">案例质量</h5>
              <MetricGrid values={item.quality} />
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

type Props = {
  recommendation: Recommendation;
  isSelected: boolean;
  onSelect: () => void;
};

export function RecommendationCard({ recommendation: rec, isSelected, onSelect }: Props) {
  const isML = rec.generation_method === "ml_regression_fit";
  const scorePercent = Math.round(rec.score * 100);

  return (
    <article
      className={`bg-white rounded-xl border-2 transition-colors overflow-hidden ${
        isSelected ? "border-primary shadow-md ring-1 ring-primary/20" : "border-gray-200 shadow-sm"
      }`}
    >
      {/* header */}
      <div className="px-5 py-4 flex items-start justify-between gap-3 border-b border-gray-100">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                isML
                  ? "bg-purple-50 text-purple-700 border border-purple-200"
                  : "bg-primary-50 text-primary border border-primary-100"
              }`}
            >
              {isML ? "机器学习拟合" : `推荐 #${rec.rank}`}
            </span>
            {isML && rec.model_name && (
              <span className="text-xs text-gray-400">{rec.model_name}</span>
            )}
          </div>
          <p className="text-xs text-gray-500 line-clamp-2">{rec.rationale}</p>
        </div>

        <button
          onClick={onSelect}
          className={`shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
            isSelected
              ? "bg-primary text-white shadow-sm"
              : "bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100"
          }`}
        >
          {isSelected ? "已选择" : "选择"}
        </button>
      </div>

      {/* score */}
      <div className="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">综合得分</span>
          <span className="text-sm font-bold text-primary font-mono">{formatScore(rec.score)}</span>
        </div>
        <div className="score-bar-bg">
          <div
            className="score-bar-fill bg-primary"
            style={{ width: `${Math.min(scorePercent, 100)}%` }}
          />
        </div>
        <details className="mt-3">
          <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-500 select-none">
            评分公式说明
          </summary>
          <div className="mt-3 space-y-1.5 text-xs">
            <div className="rounded-lg border border-gray-200 bg-white p-3 overflow-x-auto space-y-1">
              {SCORE_FORMULAS.map((formula) => (
                <BlockMath key={formula} math={formula} renderError={() => <code>{formula}</code>} />
              ))}
            </div>
            <p className="text-gray-500 leading-relaxed p-1">{SCORE_EXPLANATION}</p>
          </div>
        </details>
      </div>

      {/* metric tabs within card */}
      <div className="divide-y divide-gray-100">
        <details className="group" open>
          <summary className="px-5 py-3 cursor-pointer select-none flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            <span className="text-gray-400 group-open:rotate-90 transition-transform">▸</span>
            推荐参数
          </summary>
          <div className="px-5 pb-4">
            <MetricGrid values={rec.parameters} />
          </div>
        </details>

        <details className="group">
          <summary className="px-5 py-3 cursor-pointer select-none flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            <span className="text-gray-400 group-open:rotate-90 transition-transform">▸</span>
            中间量指标
          </summary>
          <div className="px-5 pb-4">
            <FormulaMetricGrid values={rec.intermediate_metrics} />
          </div>
        </details>

        <details className="group">
          <summary className="px-5 py-3 cursor-pointer select-none flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            <span className="text-gray-400 group-open:rotate-90 transition-transform">▸</span>
            预测质量
          </summary>
          <div className="px-5 pb-4">
            <MetricGrid values={rec.predicted_quality} />
          </div>
        </details>

        <details className="group">
          <summary className="px-5 py-3 cursor-pointer select-none flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            <span className="text-gray-400 group-open:rotate-90 transition-transform">▸</span>
            相似案例依据
            <span className="text-xs text-gray-400">({rec.similar_cases.length})</span>
          </summary>
          <div className="px-5 pb-4">
            <SimilarCases cases={rec.similar_cases} />
          </div>
        </details>
      </div>
    </article>
  );
}