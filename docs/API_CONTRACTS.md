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

当目标深度或目标直径缺少足够历史样本，或明显超出同材料历史观测范围时，接口返回 `422`。`detail.violations` 会给出请求值、样本数量、历史最小值、历史最大值和允许范围。

响应中的 `model_info` 会说明当前推荐模型。MVP 当前使用的是范围守卫加相似案例检索，不是回归/GPR 拟合模型。

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
