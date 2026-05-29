"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { toNumber } from "@/lib/utils";
import { useQueryHistory } from "@/lib/use-query-history";
import type { DatasetSummary, ModelInfo, RecommendationResponse } from "@/types/api";
import type { HistoryEntry } from "@/lib/use-query-history";

import { TaskInput } from "./task-input";
import { InfoPanels } from "./info-panels";
import { RecommendationCard } from "./recommendation-card";
import { FeedbackForm } from "./feedback-form";

type FormState = {
  material: string;
  targetDepth: string;
  targetDiameter: string;
  maxRoughness: string;
  topK: string;
  algorithm: string;
  notes: string;
};

const ALGORITHM_LABELS: Record<string, string> = {
  random_forest: "随机森林",
  neural_network: "神经网络",
  gradient_boosting: "梯度提升",
  linear_regression: "线性回归",
  svr: "支持向量机",
};

const initialForm: FormState = {
  material: "",
  targetDepth: "40",
  targetDiameter: "",
  maxRoughness: "",
  topK: "3",
  algorithm: "random_forest",
  notes: "",
};

export function Workbench({
  summary,
  modelInfo,
  onRefresh,
}: {
  summary: DatasetSummary | null;
  modelInfo: ModelInfo | null;
  onRefresh: () => void;
}) {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [algoResults, setAlgoResults] = useState<Map<string, RecommendationResponse>>(new Map());
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("results");
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { history, addEntry, removeEntry, clearHistory } = useQueryHistory();

  useEffect(() => {
    if (!form.material && summary?.materials && summary.materials.length > 0) {
      setForm((c) => ({ ...c, material: summary.materials[0].material }));
    }
  }, [summary]);

  const selectedRecommendation = useMemo(() => {
    if (!result || selectedRank === null) return null;
    return result.recommendations.find((r) => r.rank === selectedRank) ?? null;
  }, [result, selectedRank]);

  const selectedMaterial = useMemo(
    () => summary?.materials.find((m) => m.material === form.material) ?? null,
    [form.material, summary]
  );
  const diameterAvailable = selectedMaterial?.quality_metrics.includes("diameter_um") ?? false;

  function updateMaterial(material: string) {
    const next = summary?.materials.find((m) => m.material === material) ?? null;
    setForm((c) => ({
      ...c,
      material,
      targetDiameter: next?.quality_metrics.includes("diameter_um") ? c.targetDiameter : "",
    }));
  }

  function updateField(field: keyof FormState, value: string) {
    setForm((c) => ({ ...c, [field]: value }));
  }

  function handleAlgorithmChange(algorithm: string) {
    if (result && !loading) {
      // debounce: 300ms 内重复点击只执行最后一次
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        submitRecommendation(algorithm);
      }, 300);
    }
  }

  async function submitRecommendation(algorithmOverride?: string) {
    const algorithm = algorithmOverride ?? form.algorithm ?? "random_forest";
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    setMessage("");
    if (!algorithmOverride) {
      setSelectedRank(null);
    }
    try {
      const payload = await apiFetch<RecommendationResponse>("/api/recommendations", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          material: form.material || null,
          target_depth_um: toNumber(form.targetDepth),
          target_diameter_um: toNumber(form.targetDiameter),
          max_roughness_um: toNumber(form.maxRoughness),
          top_k: Number(form.topK) || 3,
          algorithm,
          constraints: {},
        }),
      });
      setResult(payload);
      if (payload.recommendations[0]) {
        setSelectedRank(payload.recommendations[0].rank);
      }
      setAlgoResults((prev) => {
        const next = new Map(prev);
        next.set(algorithm, payload);
        return next;
      });
      setActiveTab("results");
      // save to history
      addEntry(form, payload);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "推荐请求失败");
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  async function submitFeedback() {
    if (!selectedRecommendation) return;
    setFeedbackLoading(true);
    setError("");
    setMessage("");
    try {
      await apiFetch("/api/feedback", {
        method: "POST",
        body: JSON.stringify({
          task: {
            material: form.material || null,
            target_depth_um: toNumber(form.targetDepth),
            target_diameter_um: toNumber(form.targetDiameter),
            max_roughness_um: toNumber(form.maxRoughness),
            algorithm: form.algorithm || "random_forest",
            constraints: {},
            top_k: Number(form.topK) || 3,
          },
          selected_parameters: selectedRecommendation.parameters,
          measured_quality: selectedRecommendation.predicted_quality,
          operator: "web-mvp",
          notes: form.notes || "基于推荐结果录入的反馈样本",
        }),
      });
      setMessage("反馈已追加写入，刷新后会进入后续推荐候选集。");
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "反馈写入失败");
    } finally {
      setFeedbackLoading(false);
    }
  }

  function restoreFromHistory(entry: HistoryEntry) {
    setForm(entry.query);
    setResult(null);
    setSelectedRank(null);
    setMessage("");
    setError("");
    setActiveTab("results");
  }

  return (
    <div className="min-h-screen bg-[#f7f8f5]">

      <div className="max-w-[1440px] mx-auto px-5 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(340px,400px)_1fr] gap-6">
          {/* left column — task input + feedback */}
          <div className="space-y-4 lg:sticky lg:top-20 self-start">
            <TaskInput
              form={{
                material: form.material,
                targetDepth: form.targetDepth,
                targetDiameter: form.targetDiameter,
                maxRoughness: form.maxRoughness,
                topK: form.topK,
                algorithm: form.algorithm,
              }}
              materials={summary?.materials ?? []}
              diameterAvailable={diameterAvailable}
              loading={loading}
              error={error}
              message={message}
              onChangeMaterial={updateMaterial}
              onChangeField={updateField}
              onSubmit={submitRecommendation}
              onAlgorithmChange={handleAlgorithmChange}
            />
            <FeedbackForm
              result={result}
              selectedRank={selectedRank}
              notes={form.notes}
              feedbackLoading={feedbackLoading}
              onNotesChange={(v) => updateField("notes", v)}
              onSubmit={submitFeedback}
            />
          </div>

          {/* right column — info tabs + recommendation list */}
          <div className="space-y-4">
            <InfoPanels
              summary={summary}
              modelInfo={modelInfo}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              resultCount={result?.recommendations.length ?? 0}
              history={history}
              onRestoreHistory={restoreFromHistory}
              onRemoveHistory={removeEntry}
              onClearHistory={clearHistory}
            />

            {activeTab === "results" && result && result.recommendations.length > 0 && (
              <div className="space-y-3">
                {/* notes */}
                {result.notes.map((note, i) => (
                  <div key={i} className="flex items-start gap-2 px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-100 text-sm text-amber-800">
                    <span className="shrink-0 mt-0.5">⚠</span>
                    <span>{note}</span>
                  </div>
                ))}

                {/* recommendation cards */}
                {result.recommendations.map((rec) => (
                  <RecommendationCard
                    key={`${rec.generation_method}-${rec.rank}`}
                    recommendation={rec}
                    isSelected={selectedRank === rec.rank}
                    onSelect={() => setSelectedRank(rec.rank)}
                  />
                ))}

                {/* algorithm comparison — show other algorithms' results */}
                {algoResults.size > 1 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <span className="w-1 h-4 bg-primary rounded-full" />
                      算法结果对比 ({algoResults.size} 个算法)
                    </h3>
                    <div className="space-y-3">
                      {Array.from(algoResults.entries())
                        .filter(([key]) => key !== (form.algorithm || "random_forest"))
                        .map(([key, algoResult]) => (
                          <details key={key} className="group border border-gray-200 rounded-xl bg-white overflow-hidden">
                            <summary className="px-4 py-3 cursor-pointer select-none flex items-center justify-between gap-3 hover:bg-gray-50">
                              <span className="text-sm font-medium text-gray-700">
                                {ALGORITHM_LABELS[key] || key}
                              </span>
                              <div className="flex items-center gap-3 text-xs text-gray-400">
                                {algoResult.recommendations[0] && (
                                  <span className="font-mono">
                                    得分 {algoResult.recommendations[0].score.toFixed(4)}
                                  </span>
                                )}
                                <span className="text-gray-400 group-open:rotate-90 transition-transform">▸</span>
                              </div>
                            </summary>
                            <div className="px-4 pb-4">
                              {algoResult.recommendations.map((rec) => (
                                <div key={`${key}-${rec.rank}`} className="mt-2">
                                  <RecommendationCard
                                    key={`${key}-${rec.rank}`}
                                    recommendation={rec}
                                    isSelected={false}
                                    onSelect={() => {}}
                                  />
                                </div>
                              ))}
                            </div>
                          </details>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
