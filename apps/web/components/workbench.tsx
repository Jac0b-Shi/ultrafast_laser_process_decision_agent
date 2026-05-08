"use client";

import { useEffect, useMemo, useState } from "react";
import { Database, FlaskConical, RefreshCcw, Save, Send } from "lucide-react";
import { BlockMath } from "react-katex";

import { apiFetch } from "@/lib/api";
import {
  formatMetricText,
  getMetricDisplay,
  metricLabel,
  SCORE_EXPLANATION,
  SCORE_FORMULAS,
} from "@/lib/metric-display";
import type { DatasetSummary, ModelInfo, Recommendation, RecommendationResponse } from "@/types/api";

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
  if (!Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  if (abs !== 0 && abs < 0.001) return value.toExponential(3);
  if (abs >= 10000) {
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
  }
  if (Number.isInteger(value)) return String(value);
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 4 }).format(value);
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(4) : "-";
}

function formatMathValue(value: number): string {
  if (!Number.isFinite(value)) return String.raw`\text{不可用}`;
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.001 || abs >= 1_000_000)) {
    const [mantissa, exponent] = value.toExponential(3).split("e");
    return String.raw`${mantissa} \times 10^{${Number(exponent)}}`;
  }
  if (Number.isInteger(value)) return String(value);
  return String(Number(value.toFixed(4)));
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
          <span>{metricLabel(key)}</span>
          <strong>{formatValue(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function ScoreFormulaNote() {
  return (
    <div className="score-note">
      <div className="score-formula-list">
        {SCORE_FORMULAS.map((formula) => (
          <BlockMath
            key={formula}
            math={formula}
            renderError={() => <code>{formula}</code>}
          />
        ))}
      </div>
      <p>{SCORE_EXPLANATION}</p>
    </div>
  );
}

function FormulaMetricGrid({ values }: { values: Record<string, number> }) {
  const entries = Object.entries(values);
  if (entries.length === 0) {
    return <p className="muted">暂无可展示指标</p>;
  }

  return (
    <div className="formula-grid">
      {entries.map(([key, value]) => {
        const metric = getMetricDisplay(key);
        return (
          <div className="formula-card" key={key}>
            <div className="formula-card-header">
              <span>{metricLabel(key)}</span>
            </div>
            {metric.formula && (
              <div className="formula-expression">
                <BlockMath
                  math={`${metric.formula} = ${formatMathValue(value)}`}
                  renderError={() => <code>{`${metric.formula} = ${formatValue(value)}`}</code>}
                />
              </div>
            )}
            {!metric.formula && <strong className="formula-value">{formatValue(value)}</strong>}
            {metric.variables && <p className="formula-note">{metric.variables}</p>}
            {metric.note && <p className="formula-note">{metric.note}</p>}
          </div>
        );
      })}
    </div>
  );
}

function SimilarCases({ cases }: { cases: Recommendation["similar_cases"] }) {
  if (cases.length === 0) {
    return <p className="muted">暂无相似案例依据</p>;
  }

  return (
    <div className="case-list">
      {cases.map((item) => (
        <div className="case-item" key={item.case_id}>
          <div className="case-title">
            <strong>{item.case_id}</strong>
            <span className="score">相似度 {formatScore(item.score)}</span>
          </div>
          <p className="muted">
            {item.material} · {item.source_file}
            {item.source_row ? `:${item.source_row}` : ""}
          </p>
          <h4>案例参数</h4>
          <MetricGrid values={item.parameters} />
          <h4>案例中间量</h4>
          <FormulaMetricGrid values={item.intermediate_metrics} />
          <h4>案例质量</h4>
          <MetricGrid values={item.quality} />
        </div>
      ))}
    </div>
  );
}

export function Workbench() {
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  async function loadSummary() {
    setError("");
    const [payload, model] = await Promise.all([
      apiFetch<DatasetSummary>("/api/datasets/summary"),
      apiFetch<ModelInfo>("/api/recommendations/model-info"),
    ]);
    setSummary(payload);
    setModelInfo(model);
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

  const selectedMaterial = useMemo(
    () => summary?.materials.find((item) => item.material === form.material) ?? null,
    [form.material, summary],
  );
  const diameterAvailable = selectedMaterial?.quality_metrics.includes("diameter_um") ?? false;

  function updateMaterial(material: string) {
    const nextMaterial = summary?.materials.find((item) => item.material === material) ?? null;
    setForm((current) => ({
      ...current,
      material,
      targetDiameter: nextMaterial?.quality_metrics.includes("diameter_um") ? current.targetDiameter : "",
    }));
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
            <span className="badge">模型 {modelInfo?.model_version ?? "-"}</span>
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
                  onChange={(event) => updateMaterial(event.target.value)}
                >
                  {summary?.materials.map((item) => (
                    <option key={item.material} value={item.material}>
                      {item.material}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="depth">目标深度 (μm)</label>
                <input id="depth" value={form.targetDepth} onChange={(event) => setForm({ ...form, targetDepth: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="diameter">目标直径 (μm)</label>
                <input
                  id="diameter"
                  value={form.targetDiameter}
                  disabled={!diameterAvailable}
                  placeholder={diameterAvailable ? "" : "当前材料暂无直径指标"}
                  onChange={(event) => setForm({ ...form, targetDiameter: event.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="roughness">粗糙度上限 (μm)</label>
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
              <h2>模型状态</h2>
              <span className="muted">版本 {modelInfo?.model_version ?? "-"}</span>
            </div>
            <div className="panel-body">
              <div className="model-box">
                <strong>{modelInfo?.model_type ?? "暂未加载"}</strong>
                <p className="muted">{modelInfo?.training_scope}</p>
                <p className="muted">{modelInfo?.extrapolation_policy}</p>
              </div>
            </div>
          </div>

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
                    <div className="muted">{item.quality_metrics.map(metricLabel).join(", ") || "暂无质量指标"}</div>
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
              {result?.notes.map((note) => <p className="muted" key={note}>{formatMetricText(note)}</p>)}
              {result?.model_info && (
                <p className="muted">
                  本次使用：{result.model_info.model_type}，版本 {result.model_info.model_version}
                </p>
              )}
              {result?.recommendations.map((item) => (
                <article className="recommendation" key={`${item.generation_method}-${item.rank}`}>
                  <div className="recommendation-title">
                    <strong>{item.generation_method === "ml_regression_fit" ? "回归模型推荐" : `推荐 #${item.rank}`}</strong>
                    <button className="button secondary" onClick={() => setSelectedRank(item.rank)}>
                      选择
                    </button>
                    <span className="score">得分 {formatScore(item.score)}</span>
                  </div>
                  <ScoreFormulaNote />
                  <span className="badge">
                    {item.generation_method === "ml_regression_fit" ? "机器学习拟合" : "历史相似案例"}
                  </span>
                  <p className="muted">{item.rationale}</p>
                  <p className="muted">{item.material_explanation}</p>
                  <h3>参数</h3>
                  <MetricGrid values={item.parameters} />
                  <h3>中间量</h3>
                  <FormulaMetricGrid values={item.intermediate_metrics} />
                  <h3>预测质量</h3>
                  <MetricGrid values={item.predicted_quality} />
                  <h3>相似案例依据</h3>
                  <SimilarCases cases={item.similar_cases} />
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>反馈录入</h2>
              <span className="muted">
                {selectedRecommendation
                  ? selectedRecommendation.generation_method === "ml_regression_fit"
                    ? "已选择回归模型推荐"
                    : `已选择 #${selectedRecommendation.rank}`
                  : "未选择推荐"}
              </span>
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
