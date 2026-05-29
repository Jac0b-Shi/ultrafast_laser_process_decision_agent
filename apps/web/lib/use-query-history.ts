"use client";

import { useCallback, useEffect, useState } from "react";
import type { RecommendationResponse } from "@/types/api";

const STORAGE_KEY = "ultrafast_laser_query_history";
const MAX_HISTORY = 50;

export type HistoryEntry = {
  id: string;
  timestamp: number;
  query: {
    material: string;
    targetDepth: string;
    targetDiameter: string;
    maxRoughness: string;
    topK: string;
    notes: string;
    algorithm?: string;
  };
  result: {
    datasetSize: number;
    candidateSize: number;
    recommendationCount: number;
    topScore: number | null;
    topMethod: string | null;
    notes: string[];
  };
};

function summarizeResult(resp: RecommendationResponse): HistoryEntry["result"] {
  const top = resp.recommendations[0] ?? null;
  return {
    datasetSize: resp.dataset_size,
    candidateSize: resp.candidate_size,
    recommendationCount: resp.recommendations.length,
    topScore: top ? top.score : null,
    topMethod: top ? top.generation_method : null,
    notes: resp.notes,
  };
}

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed as HistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // ignore quota errors
  }
}

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // load from localStorage on mount
  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const addEntry = useCallback(
    (
      query: HistoryEntry["query"],
      resp: RecommendationResponse
    ) => {
      const entry: HistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        timestamp: Date.now(),
        query,
        result: summarizeResult(resp),
      };
      setHistory((prev) => {
        const next = [entry, ...prev].slice(0, MAX_HISTORY);
        saveHistory(next);
        return next;
      });
    },
    []
  );

  const removeEntry = useCallback((id: string) => {
    setHistory((prev) => {
      const next = prev.filter((e) => e.id !== id);
      saveHistory(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  return { history, addEntry, removeEntry, clearHistory };
}
