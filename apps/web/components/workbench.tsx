"use client";

import { useEffect, useMemo, useState } from "react";
import { Database, FlaskConical, RefreshCcw, Save, Send } from "lucide-react";

import { apiFetch } from "@/lib/api";
import type { DatasetSummary, RecommendationResponse } from "@/types/api";

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

function toNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function MetricGrid({ values }: { values: Record<string, number> }) {
  const entries = Object.entries(values);
  if (entries.length === 0) {
    return <p className="muted">暂无可展示指标</p>;
  }

  return (
    <div className="kv-grid">
      {entries.map(([key, value]) => (
        <div className="kv" key={key}>
          <span>{key}</span>
          <strong>{formatValue(value)}</strong>
        </div>
      ))}
    </div>
  );
}

export function Workbench() {
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  async function loadSummary() {
    setError("");
    const payload = await apiFetch<DatasetSummary>("/api/datasets/summary");
    setSummary(payload);
    if (!form.material && payload.materials.length > 0) {
      setForm((current) => ({ ...current, material: payload.materials[0].material }));
    }
  }

  useEffect(() => {
    loadSummary().catch((err: unknown) => setError(err instanceof Error ? err.message : "数据概览加载失败"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedRecommendation = useMemo(() => {
    if (!result || selectedRank === null) return null;
    return result.recommendations.find((item) => item.rank === selectedRank) ?? null;
  }, [result, selectedRank]);

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

  return (
    <main className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <h1>超快激光工艺决策智能体</h1>
            <p>基于实验数据的相似案例检索、参数推荐与反馈闭环</p>
          </div>
          <div className="status-row">
            <span className="badge"><Database size={16} />{summary?.total_samples ?? "-"} 条样本</span>
            <span className="badge"><FlaskConical size={16} />{summary?.materials.length ?? "-"} 类材料</span>
          </div>
        </div>
      </header>

      <div className="main-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>任务输入</h2>
            <button className="button secondary" onClick={() => loadSummary()} title="刷新数据概览">
              <RefreshCcw size={16} />刷新
            </button>
          </div>
          <div className="panel-body">
            <div className="form-grid">
              <div className="field">
                <label htmlFor="material">材料</label>
                <select
                  id="material"
                  value={form.material}
                  onChange={(event) => setForm({ ...form, material: event.target.value })}
                >
                  {summary?.materials.map((item) => (
                    <option key={item.material} value={item.material}>
                      {item.material}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="depth">目标深度 um</label>
                <input id="depth" value={form.targetDepth} onChange={(event) => setForm({ ...form, targetDepth: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="diameter">目标直径 um</label>
                <input id="diameter" value={form.targetDiameter} onChange={(event) => setForm({ ...form, targetDiameter: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="roughness">粗糙度上限 um</label>
                <input id="roughness" value={form.maxRoughness} onChange={(event) => setForm({ ...form, maxRoughness: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="topK">推荐数量</label>
                <input id="topK" value={form.topK} onChange={(event) => setForm({ ...form, topK: event.target.value })} />
              </div>
              <div className="button-row">
                <button className="button primary" onClick={submitRecommendation} disabled={loading}>
                  <Send size={16} />{loading ? "计算中" : "生成推荐"}
                </button>
              </div>
              {error && <p className="error">{error}</p>}
              {message && <p className="muted">{message}</p>}
            </div>
          </div>
        </section>

        <section className="results">
          <div className="panel">
            <div className="panel-header">
              <h2>数据概览</h2>
              <span className="muted">反馈样本 {summary?.feedback_samples ?? 0}</span>
            </div>
            <div className="panel-body material-list">
              {summary?.materials.map((item) => (
                <div className="material-item" key={item.material}>
                  <div>
                    <strong>{item.material}</strong>
                    <div className="muted">{item.quality_metrics.join(", ") || "暂无质量指标"}</div>
                  </div>
                  <span className="badge">{item.sample_count} 条</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>推荐结果</h2>
              <span className="muted">{result ? `${result.candidate_size} 条候选` : "等待任务输入"}</span>
            </div>
            <div className="panel-body results">
              {result?.notes.map((note) => <p className="muted" key={note}>{note}</p>)}
              {result?.recommendations.map((item) => (
                <article className="recommendation" key={item.rank}>
                  <div className="recommendation-title">
                    <strong>推荐 #{item.rank}</strong>
                    <button className="button secondary" onClick={() => setSelectedRank(item.rank)}>
                      选择
                    </button>
                    <span className="score">得分 {item.score}</span>
                  </div>
                  <p className="muted">{item.rationale}</p>
                  <h3>参数</h3>
                  <MetricGrid values={item.parameters} />
                  <h3>预测质量</h3>
                  <MetricGrid values={item.predicted_quality} />
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>反馈录入</h2>
              <span className="muted">{selectedRecommendation ? `已选择 #${selectedRecommendation.rank}` : "未选择推荐"}</span>
            </div>
            <div className="panel-body form-grid">
              <div className="field">
                <label htmlFor="notes">实验备注</label>
                <textarea id="notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
              </div>
              <button className="button primary" onClick={submitFeedback} disabled={!selectedRecommendation || feedbackLoading}>
                <Save size={16} />{feedbackLoading ? "写入中" : "追加反馈"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
