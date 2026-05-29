export type MaterialSummary = {
  material: string;
  sample_count: number;
  source_files: string[];
  parameter_columns: string[];
  quality_metrics: string[];
};

export type DatasetSummary = {
  total_samples: number;
  materials: MaterialSummary[];
  raw_files: string[];
  feedback_samples: number;
};

export type CaseMatch = {
  case_id: string;
  material: string;
  source_file: string;
  source_row: number | null;
  parameters: Record<string, number>;
  intermediate_metrics: Record<string, number>;
  quality: Record<string, number>;
  score: number;
};

export type ModelInfo = {
  model_name: string;
  model_version: string;
  model_type: string;
  training_scope: string;
  feature_columns: string[];
  target_columns: string[];
  extrapolation_policy: string;
};

export type Recommendation = {
  rank: number;
  generation_method: string;
  model_name: string | null;
  algorithm: string | null;
  parameters: Record<string, number>;
  intermediate_metrics: Record<string, number>;
  predicted_quality: Record<string, number>;
  uncertainty: Record<string, number>;
  score: number;
  rationale: string;
  material_explanation: string;
  similar_cases: CaseMatch[];
  feature_importance: Record<string, number> | null;
  error_metrics: Record<string, Record<string, number>> | null;
  training_info: Record<string, string | number> | null;
};

export type RecommendationResponse = {
  dataset_size: number;
  candidate_size: number;
  model_info: ModelInfo;
  recommendations: Recommendation[];
  notes: string[];
};

// 数据管理相关类型
export type ExperimentData = {
  case_id: string | null;
  material: string;
  pulse_width_fs: number | null;
  repetition_frequency_khz: number | null;
  scan_speed_mm_s: number | null;
  pulse_energy_mj: number | null;
  laser_energy_percent: number | null;
  defocus_amount_mm: number | null;
  marking_count: number | null;
  fill_spacing_um: number | null;
  scan_interval_um: number | null;
  processing_time_s: number | null;
  average_power_w: number | null;
  peak_power_kw: number | null;
  depth_um: number | null;
  diameter_um: number | null;
  roughness_um: number | null;
  is_active: boolean;
  data_source: string;
  note: string | null;
};

export type MaterialListResponse = {
  materials: string[];
};

export type ExperimentDataListResponse = {
  records: ExperimentData[];
};
