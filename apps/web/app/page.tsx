"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import type { DatasetSummary, ModelInfo } from "@/types/api";

import { TopBar } from "@/components/top-bar";
import { Workbench } from "@/components/workbench";
import { DataManagement } from "@/components/data-management";

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<"workbench" | "data-management">("workbench");
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setError("");
    try {
      const [payload, model] = await Promise.all([
        apiFetch<DatasetSummary>("/api/datasets/summary"),
        apiFetch<ModelInfo>("/api/recommendations/model-info"),
      ]);
      setSummary(payload);
      setModelInfo(model);
    } catch (err) {
      setError(err instanceof Error ? err.message : "数据加载失败");
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = useCallback(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="min-h-screen bg-[#f7f8f5]">
      <TopBar
        summary={summary}
        modelInfo={modelInfo}
        onRefresh={handleRefresh}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
      />

      {error && (
        <div className="max-w-[1440px] mx-auto px-5 py-4">
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-700">
            <span>⚠</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {currentPage === "workbench" && (
        <Workbench summary={summary} modelInfo={modelInfo} onRefresh={handleRefresh} />
      )}
      {currentPage === "data-management" && <DataManagement />}
    </div>
  );
}