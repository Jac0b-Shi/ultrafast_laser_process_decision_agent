"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { toNumber } from "@/lib/utils";
import { useQueryHistory } from "@/lib/use-query-history";
import type { DatasetSummary, ModelInfo, RecommendationResponse } from "@/types/api";
import type { HistoryEntry } from "@/lib/use-query-history";

import { TopBar } from "./top-bar";
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
  notes: string;
};

const initialForm: FormState = {
  material: "",
  targetDepth: "40",
  targetDiameter: "",
  maxRoughness: "",
  topK: "3",
  notes: "",
};

export function Workbench() {
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("results");

  const { history, addEntry, removeEntry, clearHistory } = useQueryHistory();

  async function loadSummary() {
    setError("");
    const [payload, model] = await Promise.all([
      apiFetch<DatasetSummary>("/api/datasets/summary"),
      apiFetch<ModelInfo>("/api/recommendations/model-info"),
    ]);
    setSummary(payload);
    setModelInfo(model);
    if (!form.material && payload.materials.length > 0) {
      setForm((c) => ({ ...c, material: payload.materials[0].material }));
    }
  }

  useEffect(() => {
    loadSummary().catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "数据概览加载失败")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  async function submitRecommendation() {
    setLoading(true);
    setError("");
    setMessage("");
    setSelectedRank(null);
    try {
      const payload = await apiFetch<RecommendationResponse>("/api/recommendations", {
        method: "POST",
        body: JSON.stringify({
          material: form.material || null,
          target_depth_um: toNumber(form.targetDepth),
          target_diameter_um: toNumber(form.targetDiameter),
          max_roughness_um: toNumber(form.maxRoughness),
          top_k: Number(form.topK) || 3,
          constraints: {},
        }),
      });
      setResult(payload);
      if (payload.recommendations[0]) {
        setSelectedRank(payload.recommendations[0].rank);
      }
      setActiveTab("results");
      // save to history
      addEntry(form, payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "推荐请求失败");
    } finally {
      setLoading(false);
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
      await loadSummary();
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
      <TopBar summary={summary} modelInfo={modelInfo} onRefresh={() => { loadSummary().catch(() => {}); }} />

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
              }}
              materials={summary?.materials ?? []}
              diameterAvailable={diameterAvailable}
              loading={loading}
              error={error}
              message={message}
              onChangeMaterial={updateMaterial}
              onChangeField={updateField}
              onSubmit={submitRecommendation}
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
