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
  parameters: Record<string, number>;
  predicted_quality: Record<string, number>;
  uncertainty: Record<string, number>;
  score: number;
  rationale: string;
  similar_cases: CaseMatch[];
};

export type RecommendationResponse = {
  dataset_size: number;
  candidate_size: number;
  model_info: ModelInfo;
  recommendations: Recommendation[];
  notes: string[];
};
