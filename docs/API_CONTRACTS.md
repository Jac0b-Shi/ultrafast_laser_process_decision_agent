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

响应包含 `recommendations`、`dataset_size`、`candidate_size`、`model_info` 和 `notes`。

当目标深度或目标直径缺少足够历史样本，或明显超出同材料历史观测范围时，接口返回 `422`。`detail.violations` 会给出请求值、样本数量、历史最小值、历史最大值和允许范围。

响应中的 `model_info` 会说明当前推荐模型。当前使用的是材料定制中间量、范围守卫、相似案例筛选与 `RandomForestRegressor` 回归拟合的混合推荐。每条推荐的 `generation_method` 会标明它是 `ml_regression_fit` 还是 `historical_similarity`。

每条推荐包含：

- `parameters`：可控原始工艺参数。
- `intermediate_metrics`：按材料即时计算的中间量，例如线脉冲密度、剂量指数、脉宽-时间交互项或功率链代理。
- `material_explanation`：本材料采用对应中间量的简短依据说明。
- `similar_cases`：相似历史案例，每个案例同样包含参数、质量指标和中间量。

API 字段名保持机器可读的 snake_case；网页端会映射为中英对照名称、真实单位符号和 KaTeX 公式。

`score` 是由质量目标偏差换算得到的相似度分数，保留四位小数：

```text
score = round(1 / (1 + max(L, 0)), 4)
L = depth_loss + diameter_loss + roughness_loss + 0.05 * missing_quality_count
```

- 深度和直径目标已填写时，损失项为 `abs(measured - target) / scale`；`scale` 使用同材料候选集该质量指标的历史标准差，标准差不可用时回退为均值绝对值或 `1.0`。
- 已填写目标但候选质量值缺失时，深度或直径损失按 `2.0` 计；粗糙度约束缺失按 `1.5` 计。
- 粗糙度上限已填写时，低于上限按 `0.2 * roughness / max_roughness` 计，超过上限按 `1 + (roughness - max_roughness) / max_roughness` 计。
- 深度、直径和粗糙度目标都未填写时，使用默认偏好分支：`L = roughness_or_1 - 0.05 * depth + 0.05 * missing_quality_count`。

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
