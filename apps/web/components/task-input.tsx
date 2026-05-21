"use client";

import { Send, AlertCircle, CheckCircle2 } from "lucide-react";
import type { MaterialSummary } from "@/types/api";

type FormState = {
  material: string;
  targetDepth: string;
  targetDiameter: string;
  maxRoughness: string;
  topK: string;
};

type Props = {
  form: FormState;
  materials: MaterialSummary[];
  diameterAvailable: boolean;
  loading: boolean;
  error: string;
  message: string;
  onChangeMaterial: (material: string) => void;
  onChangeField: (field: keyof FormState, value: string) => void;
  onSubmit: () => void;
};

export function TaskInput({
  form,
  materials,
  diameterAvailable,
  loading,
  error,
  message,
  onChangeMaterial,
  onChangeField,
  onSubmit,
}: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-900">任务输入</h2>
        <p className="text-xs text-gray-500 mt-0.5">填写工艺目标，生成参数推荐</p>
      </div>

      {/* form */}
      <div className="p-5 space-y-4">
        {/* material */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">加工材料</label>
          <select
            value={form.material}
            onChange={(e) => onChangeMaterial(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          >
            {materials.map((m) => (
              <option key={m.material} value={m.material}>
                {m.material}
              </option>
            ))}
          </select>
        </div>

        {/* depth */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            目标深度 <span className="text-gray-400">(μm)</span>
          </label>
          <input
            type="number"
            step="any"
            value={form.targetDepth}
            onChange={(e) => onChangeField("targetDepth", e.target.value)}
            placeholder="例如 40"
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          />
        </div>

        {/* diameter */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            目标直径 <span className="text-gray-400">(μm)</span>
          </label>
          <input
            type="number"
            step="any"
            value={form.targetDiameter}
            disabled={!diameterAvailable}
            placeholder={diameterAvailable ? "例如 100" : "当前材料暂无直径指标"}
            onChange={(e) => onChangeField("targetDiameter", e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed"
          />
        </div>

        {/* roughness */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            粗糙度上限 <span className="text-gray-400">(μm)</span>
          </label>
          <input
            type="number"
            step="any"
            value={form.maxRoughness}
            onChange={(e) => onChangeField("maxRoughness", e.target.value)}
            placeholder="留空则不限制"
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          />
        </div>

        {/* topK */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">推荐数量 Top K</label>
          <div className="flex gap-2">
            {[1, 3, 5].map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => onChangeField("topK", String(k))}
                className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                  form.topK === String(k)
                    ? "border-primary bg-primary-50 text-primary font-semibold"
                    : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                {k}
              </button>
            ))}
          </div>
        </div>

        {/* submit */}
        <button
          onClick={onSubmit}
          disabled={loading || !form.material}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <Send size={14} />
          {loading ? "计算中..." : "生成推荐"}
        </button>

        {/* messages */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-700">
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {message && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 border border-green-100 text-sm text-green-700">
            <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
            <span>{message}</span>
          </div>
        )}
      </div>
    </div>
  );
}