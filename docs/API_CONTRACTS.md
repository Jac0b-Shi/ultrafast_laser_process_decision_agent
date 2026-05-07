# API 契约

## `GET /health`

返回服务状态。

```json
{"status":"ok","service":"laser-process-decision-api"}
```

## `GET /api/datasets/summary`

返回材料、样本量、参数列和质量指标概览。

## `POST /api/recommendations`

请求：

```json
{
  "material": "高温合金",
  "target_depth_um": 40,
  "target_diameter_um": 500,
  "max_roughness_um": 8.5,
  "constraints": {
    "pulse_width_fs": {"min": 60, "max": 500}
  },
  "top_k": 3
}
```

响应包含 `recommendations`、`dataset_size`、`candidate_size` 和 `notes`。

## `POST /api/feedback`

请求：

```json
{
  "task": {"material": "高温合金", "target_depth_um": 40},
  "selected_parameters": {"pulse_width_fs": 240, "repetition_frequency_khz": 260},
  "measured_quality": {"depth_um": 41.091, "diameter_um": 500.48, "roughness_um": 8.122},
  "operator": "student",
  "notes": "首件实验结果"
}
```

反馈只能追加写入。
