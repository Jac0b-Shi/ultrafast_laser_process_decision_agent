from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from app.schemas import CaseMatch, ModelInfo, ParameterRecommendation, RecommendationRequest, RecommendationResponse
from app.services.data_loader import PARAMETER_COLUMNS, QUALITY_COLUMNS, load_dataset

INTERMEDIATE_METRIC_COLUMNS = [
    "line_pulse_density_pulses_mm",
    "pulse_spacing_um",
    "threshold_relative_density",
    "cumulative_pulse_density",
    "dose_index",
    "pulse_time_interaction",
    "duty_cycle",
    "power_chain_proxy_w",
    "marking_energy_proxy",
    "peak_power_kw",
]

MODEL_FEATURE_COLUMNS = PARAMETER_COLUMNS + [
    column for column in INTERMEDIATE_METRIC_COLUMNS if column not in PARAMETER_COLUMNS
]

MODEL_INFO = ModelInfo(
    model_name="range_guarded_random_forest_regressor",
    model_version="0.4.0",
    model_type="材料定制中间量 + 规则范围守卫 + 相似案例筛选 + 多算法回归拟合 (RandomForest / MLP / GBDT / Linear / SVR)",
    training_scope=(
        "每次请求先按材料和约束筛选历史样本，再按材料构造脉冲密度、剂量指数、"
        "功率链代理或经验交互项等中间量；回归模型使用适用原始参数和中间量拟合参数到质量指标的关系，"
        "候选参数仍在历史原始参数范围内生成。"
    ),
    feature_columns=MODEL_FEATURE_COLUMNS,
    target_columns=QUALITY_COLUMNS,
    extrapolation_policy="目标深度/直径缺少足够历史样本，或超出同材料历史观测范围并超过 10% 数据跨度缓冲时，直接返回 422，不做外推拟合。",
)

MIN_REGRESSION_SAMPLES = 6
RANDOM_STATE = 42

ALGORITHM_REGRESSORS: dict[str, dict[str, Any]] = {
    "random_forest": {
        "cls": RandomForestRegressor,
        "kwargs": {"n_estimators": 160, "min_samples_leaf": 2, "random_state": RANDOM_STATE},
        "label": "随机森林",
        "label_en": "RandomForestRegressor",
    },
    "neural_network": {
        "cls": MLPRegressor,
        "kwargs": {"hidden_layer_sizes": (100, 50), "max_iter": 2000, "random_state": RANDOM_STATE, "early_stopping": True},
        "label": "神经网络",
        "label_en": "MLPRegressor",
    },
    "gradient_boosting": {
        "cls": GradientBoostingRegressor,
        "kwargs": {"n_estimators": 100, "max_depth": 4, "random_state": RANDOM_STATE},
        "label": "梯度提升",
        "label_en": "GradientBoostingRegressor",
    },
    "linear_regression": {
        "cls": LinearRegression,
        "kwargs": {},
        "label": "线性回归",
        "label_en": "LinearRegression",
    },
    "svr": {
        "cls": SVR,
        "kwargs": {"kernel": "rbf"},
        "label": "支持向量机",
        "label_en": "SVR",
    },
}

MATERIAL_FEATURES = {
    "bf33": [
        "pulse_width_fs",
        "repetition_frequency_khz",
        "scan_speed_mm_s",
        "line_pulse_density_pulses_mm",
        "pulse_spacing_um",
    ],
    "sic": [
        "pulse_width_fs",
        "repetition_frequency_khz",
        "scan_speed_mm_s",
        "line_pulse_density_pulses_mm",
        "pulse_spacing_um",
        "threshold_relative_density",
    ],
    "diamond": [
        "pulse_width_fs",
        "repetition_frequency_khz",
        "scan_speed_mm_s",
        "fill_spacing_um",
        "marking_count",
        "line_pulse_density_pulses_mm",
        "pulse_spacing_um",
        "cumulative_pulse_density",
        "dose_index",
    ],
    "microcrystalline_glass": [
        "pulse_width_fs",
        "repetition_frequency_khz",
        "scan_speed_mm_s",
        "defocus_amount_mm",
        "scan_interval_um",
        "processing_time_s",
        "pulse_time_interaction",
    ],
    "superalloy": [
        "pulse_width_fs",
        "repetition_frequency_khz",
        "laser_energy_percent",
        "pulse_energy_mj",
        "defocus_amount_mm",
        "marking_count",
        "average_power_w",
        "peak_power_kw",
        "duty_cycle",
        "power_chain_proxy_w",
        "marking_energy_proxy",
    ],
}

MATERIAL_EXPLANATIONS = {
    "bf33": "BF33 在报告中表现为重叠/累积主导型，深度和粗糙度相对单独频率或速度更受线脉冲密度与脉冲间距影响。",
    "sic": "4H 碳化硅存在接近零去除的阈值区，推荐逻辑使用线脉冲密度、脉冲间距和相对阈值密度刻画阈值后的累积去除。",
    "diamond": "金刚石的深度和粗糙度对剂量指数最敏感，因此用频率、速度、加工次数和填充间距构造累积脉冲密度与剂量指数。",
    "microcrystalline_glass": "微晶玻璃的数据更像经验参数主导系统，剂量代理未明显优于原始参数，因此重点保留脉宽、加工时间、离焦量和脉宽-时间交互项。",
    "superalloy": "高温合金表内已有功率链变量，直径更接近平均功率控制，深度和粗糙度更受标记频率影响，因此推荐逻辑使用功率代理、占空比和标记能量代理。",
    "generic": "当前候选集未落入已知单一材料类型，系统使用可用原始参数和可计算中间量进行保守推荐。",
}


class OutOfRangeError(ValueError):
    def __init__(self, message: str, details: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def _finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _to_float(value: Any) -> float | None:
    if not _finite(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(denominator) <= 1e-12:
        return None
    return numerator / denominator


def _number_dict(row: pd.Series, columns: list[str]) -> dict[str, float]:
    output: dict[str, float] = {}
    for column in columns:
        value = _to_float(row.get(column))
        if value is not None:
            output[column] = value
    return output


def _material_family(material: Any) -> str:
    text = str(material or "").casefold()
    if "bf33" in text:
        return "bf33"
    if "碳化硅" in text or "sic" in text or "4h" in text:
        return "sic"
    if "金刚石" in text or "diamond" in text:
        return "diamond"
    if "微晶" in text:
        return "microcrystalline_glass"
    if "高温合金" in text or "superalloy" in text:
        return "superalloy"
    return "generic"


def _dominant_material(frame: pd.DataFrame, requested_material: str | None = None) -> str:
    if requested_material:
        return requested_material
    if "material" not in frame or frame.empty:
        return ""
    values = [str(value) for value in frame["material"].dropna().unique()]
    return values[0] if len(values) == 1 else ""


def _dominant_family(frame: pd.DataFrame, requested_material: str | None = None) -> str:
    requested_family = _material_family(requested_material)
    if requested_family != "generic":
        return requested_family
    if "material" not in frame or frame.empty:
        return "generic"
    families = {_material_family(value) for value in frame["material"].dropna().unique()}
    families.discard("generic")
    return next(iter(families)) if len(families) == 1 else "generic"


def _line_pulse_density(row: pd.Series) -> float | None:
    frequency = _to_float(row.get("repetition_frequency_khz"))
    speed = _to_float(row.get("scan_speed_mm_s"))
    return _safe_divide(1000.0 * frequency if frequency is not None else None, speed)


def _pulse_spacing(row: pd.Series) -> float | None:
    frequency = _to_float(row.get("repetition_frequency_khz"))
    speed = _to_float(row.get("scan_speed_mm_s"))
    return _safe_divide(1000.0 * speed if speed is not None else None, frequency)


def _threshold_density_by_family(frame: pd.DataFrame, material: str | None = None) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    if frame.empty:
        return thresholds

    densities: dict[str, list[float]] = {}
    for _, row in frame.iterrows():
        row_material = row.get("material") if "material" in row else material
        family = _material_family(row_material)
        if family != "sic":
            continue
        depth = _to_float(row.get("depth_um"))
        density = _line_pulse_density(row)
        if depth is not None and depth > 0 and density is not None and density > 0:
            densities.setdefault(family, []).append(density)

    for family, values in densities.items():
        thresholds[family] = min(values)
    return thresholds


def _intermediate_metrics(row: pd.Series, material: Any, threshold_density: float | None = None) -> dict[str, float]:
    family = _material_family(material)
    metrics: dict[str, float] = {}
    line_density = _line_pulse_density(row)
    pulse_spacing = _pulse_spacing(row)

    def add(name: str, value: float | None) -> None:
        if value is not None and math.isfinite(value):
            metrics[name] = value

    if family in {"bf33", "sic", "diamond"}:
        add("line_pulse_density_pulses_mm", line_density)
        add("pulse_spacing_um", pulse_spacing)

    if family == "sic":
        add("threshold_relative_density", _safe_divide(line_density, threshold_density))

    if family == "diamond":
        marking_count = _to_float(row.get("marking_count"))
        fill_spacing = _to_float(row.get("fill_spacing_um"))
        cumulative_density = line_density * marking_count if line_density is not None and marking_count is not None else None
        add("cumulative_pulse_density", cumulative_density)
        add("dose_index", _safe_divide(cumulative_density, fill_spacing))

    if family == "microcrystalline_glass":
        pulse_width = _to_float(row.get("pulse_width_fs"))
        processing_time = _to_float(row.get("processing_time_s"))
        interaction = pulse_width * processing_time if pulse_width is not None and processing_time is not None else None
        add("pulse_time_interaction", interaction)

    if family == "superalloy":
        pulse_width = _to_float(row.get("pulse_width_fs"))
        frequency = _to_float(row.get("repetition_frequency_khz"))
        pulse_energy = _to_float(row.get("pulse_energy_mj"))
        average_power = _to_float(row.get("average_power_w"))
        marking_count = _to_float(row.get("marking_count"))
        peak_power = _to_float(row.get("peak_power_kw"))
        fallback_power = pulse_energy * frequency if pulse_energy is not None and frequency is not None else None
        add("duty_cycle", pulse_width * frequency * 1e-12 if pulse_width is not None and frequency is not None else None)
        add("power_chain_proxy_w", average_power if average_power is not None else fallback_power)
        add("marking_energy_proxy", _safe_divide(average_power, marking_count))
        add("peak_power_kw", peak_power)

    return metrics


def _add_intermediate_columns(
    frame: pd.DataFrame,
    reference_frame: pd.DataFrame | None = None,
    material: str | None = None,
) -> pd.DataFrame:
    output = frame.copy()
    for column in INTERMEDIATE_METRIC_COLUMNS:
        if column not in output:
            output[column] = np.nan

    reference = reference_frame if reference_frame is not None else output
    thresholds = _threshold_density_by_family(reference, material)
    for index, row in output.iterrows():
        row_material = row.get("material") if "material" in output else material
        if not row_material:
            row_material = material or _dominant_material(reference)
        family = _material_family(row_material)
        metrics = _intermediate_metrics(row, row_material, thresholds.get(family))
        for column, value in metrics.items():
            output.at[index, column] = value
    return output


def _material_explanation(material: Any) -> str:
    return MATERIAL_EXPLANATIONS.get(_material_family(material), MATERIAL_EXPLANATIONS["generic"])


def _scale(frame: pd.DataFrame, column: str) -> float:
    values = frame[column].dropna()
    if len(values) < 2:
        return 1.0
    std = float(values.std())
    return std if std > 0 else max(abs(float(values.mean())), 1.0)


def _apply_constraints(frame: pd.DataFrame, constraints: dict[str, Any]) -> pd.DataFrame:
    filtered = frame
    for column, rule in constraints.items():
        if column not in PARAMETER_COLUMNS or column not in filtered:
            continue
        if isinstance(rule, dict):
            minimum = rule.get("min", rule.get("gte"))
            maximum = rule.get("max", rule.get("lte"))
            if minimum is not None:
                filtered = filtered[filtered[column].notna() & (filtered[column] >= float(minimum))]
            if maximum is not None:
                filtered = filtered[filtered[column].notna() & (filtered[column] <= float(maximum))]
        elif rule is not None:
            filtered = filtered[filtered[column].notna() & (filtered[column] == float(rule))]
    return filtered


def _score_row(row: pd.Series, frame: pd.DataFrame, request: RecommendationRequest) -> float:
    return _score_quality(_number_dict(row, QUALITY_COLUMNS), frame, request)


def _score_quality(quality: dict[str, float], frame: pd.DataFrame, request: RecommendationRequest) -> float:
    score = 0.0
    terms = 0

    targets = [
        ("depth_um", request.target_depth_um),
        ("diameter_um", request.target_diameter_um),
    ]
    for column, target in targets:
        if target is None:
            continue
        terms += 1
        value = quality.get(column)
        if not _finite(value):
            score += 2.0
            continue
        score += abs(float(value) - target) / _scale(frame, column)

    if request.max_roughness_um is not None:
        terms += 1
        value = quality.get("roughness_um")
        if not _finite(value):
            score += 1.5
        elif float(value) <= request.max_roughness_um:
            score += 0.2 * (float(value) / max(request.max_roughness_um, 1e-9))
        else:
            score += 1.0 + (float(value) - request.max_roughness_um) / max(request.max_roughness_um, 1e-9)

    if terms == 0:
        roughness = quality.get("roughness_um")
        depth = quality.get("depth_um")
        score += float(roughness) if _finite(roughness) else 1.0
        score -= 0.05 * float(depth) if _finite(depth) else 0.0

    missing_quality = sum(1 for column in QUALITY_COLUMNS if not _finite(quality.get(column)))
    return score + 0.05 * missing_quality


def _case_match(row: pd.Series, score: float) -> CaseMatch:
    return CaseMatch(
        case_id=str(row["case_id"]),
        material=str(row["material"]),
        source_file=str(row["source_file"]),
        source_row=int(row["source_row"]) if _finite(row.get("source_row")) else None,
        parameters=_number_dict(row, PARAMETER_COLUMNS),
        intermediate_metrics=_number_dict(row, INTERMEDIATE_METRIC_COLUMNS),
        quality=_number_dict(row, QUALITY_COLUMNS),
        score=round(1.0 / (1.0 + max(score, 0.0)), 4),
    )


def _uncertainty(frame: pd.DataFrame) -> dict[str, float]:
    output: dict[str, float] = {}
    for column in QUALITY_COLUMNS:
        values = frame[column].dropna()
        if len(values) >= 2:
            output[column] = round(float(values.std()), 4)
    return output


def _range_summary(values: pd.Series) -> tuple[float, float, float]:
    minimum = float(values.min())
    maximum = float(values.max())
    span = maximum - minimum
    buffer = max(span * 0.10, 1e-9)
    return minimum, maximum, buffer


def _validate_observed_target_ranges(frame: pd.DataFrame, request: RecommendationRequest) -> None:
    checks = [
        ("target_depth_um", "depth_um", request.target_depth_um, "目标深度"),
        ("target_diameter_um", "diameter_um", request.target_diameter_um, "目标直径"),
    ]
    violations: list[dict[str, Any]] = []

    for request_field, column, target, label in checks:
        if target is None or column not in frame:
            continue
        values = frame[column].dropna()
        if len(values) < 3:
            violations.append(
                {
                    "field": request_field,
                    "metric": column,
                    "label": label,
                    "requested": target,
                    "reason": "insufficient_observations",
                    "sample_count": int(len(values)),
                }
            )
            continue
        minimum, maximum, buffer = _range_summary(values)
        if target < minimum - buffer or target > maximum + buffer:
            violations.append(
                {
                    "field": request_field,
                    "metric": column,
                    "label": label,
                    "requested": target,
                    "observed_min": round(minimum, 6),
                    "observed_max": round(maximum, 6),
                    "allowed_min": round(minimum - buffer, 6),
                    "allowed_max": round(maximum + buffer, 6),
                    "sample_count": int(len(values)),
                }
            )

    if violations:
        material = request.material or "当前候选集"
        messages: list[str] = []
        for item in violations:
            if item.get("reason") == "insufficient_observations":
                messages.append(
                    f"{material} 缺少足够的 {item['label']} 历史样本，"
                    f"当前只有 {item['sample_count']} 条可用观测"
                )
            else:
                messages.append(
                    f"{item['label']} {item['requested']} 超出 {material} 历史观测范围 "
                    f"{item['observed_min']} - {item['observed_max']}"
                )
        readable = "; ".join(messages)
        raise OutOfRangeError(f"{readable}，系统已拒绝外推拟合。", violations)


def _regression_targets(frame: pd.DataFrame, request: RecommendationRequest) -> list[str]:
    requested_targets = [
        ("depth_um", request.target_depth_um is not None),
        ("diameter_um", request.target_diameter_um is not None),
        ("roughness_um", request.max_roughness_um is not None),
    ]
    targets = [
        column
        for column, requested in requested_targets
        if requested and column in frame and frame[column].dropna().shape[0] >= MIN_REGRESSION_SAMPLES
    ]
    if targets:
        return targets
    return [
        column
        for column in QUALITY_COLUMNS
        if column in frame and frame[column].dropna().shape[0] >= MIN_REGRESSION_SAMPLES
    ]


def _regression_features(frame: pd.DataFrame, family: str) -> list[str]:
    candidates = MATERIAL_FEATURES.get(family, MODEL_FEATURE_COLUMNS)
    features: list[str] = []
    for column in candidates:
        if column not in frame:
            continue
        values = frame[column].dropna()
        if len(values) >= MIN_REGRESSION_SAMPLES and values.nunique() >= 2:
            features.append(column)
    return features


def _fit_regression_models(
    frame: pd.DataFrame,
    feature_columns: list[str],
    target_columns: list[str],
    algorithm: str = "random_forest",
) -> tuple[dict[str, Pipeline], list[str], dict[str, Any]]:
    models: dict[str, Pipeline] = {}
    skipped: list[str] = []
    cv_r2_scores: dict[str, float] = {}
    feature_ready = frame[feature_columns].notna().any(axis=1)
    total_samples: int | None = None
    t_start = time.perf_counter()

    algo = ALGORITHM_REGRESSORS.get(algorithm, ALGORITHM_REGRESSORS["random_forest"])

    for target in target_columns:
        train = frame[feature_ready & frame[target].notna()]
        if len(train) < MIN_REGRESSION_SAMPLES:
            skipped.append(target)
            continue
        total_samples = max(total_samples or 0, int(len(train)))
        regressor = algo["cls"](**algo["kwargs"])
        model = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("regressor", regressor),
            ]
        )
        model.fit(train[feature_columns], train[target])
        models[target] = model

        # holdout R² on a subset for a rough generalization estimate
        if len(train) >= 10:
            try:
                train_sub, test_sub = train_test_split(
                    train, test_size=0.2, random_state=RANDOM_STATE,
                )
                if len(test_sub) >= 2:
                    cv_regressor = algo["cls"](**algo["kwargs"])
                    cv_model = Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                            ("regressor", cv_regressor),
                        ]
                    )
                    cv_model.fit(train_sub[feature_columns], train_sub[target])
                    y_pred = cv_model.predict(test_sub[feature_columns])
                    cv_r2_scores[target] = round(float(r2_score(test_sub[target], y_pred)), 4)
            except Exception:
                pass

    t_end = time.perf_counter()
    training_info: dict[str, Any] = {
        "algorithm": algo["label"],
        "algorithm_key": algorithm,
        "training_samples": total_samples,
        "training_time_ms": round((t_end - t_start) * 1000, 2),
    }
    if cv_r2_scores:
        training_info["holdout_r2"] = cv_r2_scores
        r2_values = list(cv_r2_scores.values())
        training_info["holdout_r2_mean"] = round(sum(r2_values) / len(r2_values), 4)
    return models, skipped, training_info


def _filled_feature_row(row: pd.Series, columns: list[str], medians: pd.Series) -> dict[str, float]:
    output: dict[str, float] = {}
    for column in columns:
        value = _to_float(row.get(column))
        if value is None:
            value = _to_float(medians.get(column))
        if value is not None:
            output[column] = value
    return output


def _generate_regression_candidates(
    frame: pd.DataFrame,
    feature_columns: list[str],
    scored_rows: list[tuple[Any, float]],
    request: RecommendationRequest,
) -> pd.DataFrame:
    parameter_columns = [column for column in feature_columns if column in PARAMETER_COLUMNS]
    if not parameter_columns:
        return pd.DataFrame()

    feature_frame = frame[parameter_columns].copy()
    medians = feature_frame.median(numeric_only=True)
    minimums = feature_frame.min(numeric_only=True)
    maximums = feature_frame.max(numeric_only=True)
    rng = np.random.default_rng(RANDOM_STATE)

    rows: list[dict[str, float]] = []
    for _, row in feature_frame.dropna(how="all").iterrows():
        rows.append(_filled_feature_row(row, parameter_columns, medians))

    top_indices = [index for index, _ in scored_rows[: min(12, len(scored_rows))]]
    if top_indices:
        all_feature_rows = feature_frame.dropna(how="all").reset_index(drop=True)
        for index in top_indices:
            base = frame.loc[index, parameter_columns].fillna(medians)
            for _ in range(12):
                if all_feature_rows.empty:
                    other = base
                else:
                    other = all_feature_rows.iloc[int(rng.integers(0, len(all_feature_rows)))].fillna(medians)
                alpha = float(rng.uniform(0.55, 0.9))
                blended = alpha * base + (1.0 - alpha) * other
                candidate: dict[str, float] = {}
                for column in parameter_columns:
                    span = float(maximums[column] - minimums[column])
                    jitter = float(rng.normal(0, span * 0.025)) if span > 0 else 0.0
                    value = float(blended[column] + jitter)
                    value = min(max(value, float(minimums[column])), float(maximums[column]))
                    candidate[column] = value
                rows.append(candidate)

    generated = pd.DataFrame(rows).drop_duplicates()
    if generated.empty:
        return generated

    generated = _apply_constraints(generated, request.constraints)
    if generated.empty:
        return generated

    material = _dominant_material(frame, request.material)
    if material:
        generated["material"] = material
    generated = _add_intermediate_columns(generated, reference_frame=frame, material=material)
    return generated.dropna(how="all", subset=[column for column in feature_columns if column in generated])


def _predict_quality_and_uncertainty(
    models: dict[str, Pipeline],
    feature_columns: list[str],
    feature_row: pd.Series,
) -> tuple[dict[str, float], dict[str, float]]:
    input_frame = pd.DataFrame([feature_row[feature_columns].to_dict()], columns=feature_columns)
    predicted: dict[str, float] = {}
    uncertainty: dict[str, float] = {}

    for target, model in models.items():
        prediction = float(model.predict(input_frame)[0])
        predicted[target] = round(prediction, 4)
        regressor = model.named_steps["regressor"]
        try:
            transformed = model.named_steps["imputer"].transform(input_frame)
            tree_predictions = [float(tree.predict(transformed)[0]) for tree in regressor.estimators_]
            uncertainty[target] = round(float(np.std(tree_predictions)), 4)
        except AttributeError:
            uncertainty[target] = 0.0

    return predicted, uncertainty


def _extract_feature_importance(
    models: dict[str, Pipeline],
    feature_columns: list[str],
) -> dict[str, float] | None:
    importances: dict[str, list[float]] = {}
    for model in models.values():
        regressor = model.named_steps["regressor"]
        try:
            fi = regressor.feature_importances_
        except AttributeError:
            continue
        for col, val in zip(feature_columns, fi):
            if col not in importances:
                importances[col] = []
            importances[col].append(float(val))
    if not importances:
        return None
    return {col: round(sum(vals) / len(vals), 4) for col, vals in importances.items()}


def _ml_recommendations(
    frame: pd.DataFrame,
    scored_rows: list[tuple[Any, float]],
    similar_cases: list[CaseMatch],
    request: RecommendationRequest,
) -> tuple[list[ParameterRecommendation], list[str]]:
    notes: list[str] = []
    family = _dominant_family(frame, request.material)
    feature_columns = _regression_features(frame, family)
    target_columns = _regression_targets(frame, request)
    algorithm = getattr(request, "algorithm", "random_forest") or "random_forest"
    algo = ALGORITHM_REGRESSORS.get(algorithm, ALGORITHM_REGRESSORS["random_forest"])
    algo_label = algo["label"]

    if not feature_columns:
        return [], ["可用参数列不足，已回退到历史相似案例推荐。"]
    if not target_columns:
        return [], ["可用质量指标样本不足，已回退到历史相似案例推荐。"]

    models, skipped, training_info = _fit_regression_models(frame, feature_columns, target_columns, algorithm)
    if not models:
        return [], ["回归模型训练样本不足，已回退到历史相似案例推荐。"]
    if skipped:
        notes.append(f"以下质量指标样本不足，未训练回归模型：{', '.join(skipped)}。")

    training_info["feature_count"] = len(feature_columns)

    # feature importance
    feature_importance = _extract_feature_importance(models, feature_columns)

    generated = _generate_regression_candidates(frame, feature_columns, scored_rows, request)
    if generated.empty:
        return [], ["拟合候选参数生成失败，已回退到历史相似案例推荐。"]

    ranked: list[tuple[float, pd.Series, dict[str, float], dict[str, float]]] = []
    for _, feature_row in generated.iterrows():
        if any(column not in feature_row or not _finite(feature_row.get(column)) for column in feature_columns):
            continue
        predicted, uncertainty = _predict_quality_and_uncertainty(models, feature_columns, feature_row)
        if not predicted:
            continue
        raw_score = _score_quality(predicted, frame, request)
        ranked.append((raw_score, feature_row.copy(), predicted, uncertainty))

    ranked.sort(key=lambda item: item[0])
    recommendations: list[ParameterRecommendation] = []
    material = _dominant_material(frame, request.material)

    # error metrics for the best candidate
    best_error_metrics: dict[str, dict[str, float]] | None = None
    if ranked:
        _, best_row, best_pred, _ = ranked[0]
        error_metrics: dict[str, dict[str, float]] = {}
        for target in target_columns:
            if target in best_pred and target in frame:
                actuals = frame[target].dropna()
                if len(actuals) > 0:
                    pred_val = best_pred[target]
                    # MAE against historical mean as proxy
                    mean_actual = float(actuals.mean())
                    error_metrics[target] = {
                        "deviation_from_historical_mean": round(abs(pred_val - mean_actual), 4),
                        "predicted": round(pred_val, 4),
                        "historical_mean": round(mean_actual, 4),
                        "historical_std": round(float(actuals.std()), 4) if len(actuals) > 1 else 0.0,
                    }
        if error_metrics:
            best_error_metrics = error_metrics

    for rank, (raw_score, feature_row, predicted, uncertainty) in enumerate(ranked[:1], start=0):
        score = round(1.0 / (1.0 + max(raw_score, 0.0)), 4)
        recommendations.append(
            ParameterRecommendation(
                rank=rank,
                generation_method="ml_regression_fit",
                model_name=MODEL_INFO.model_name,
                algorithm=algo_label,
                parameters=_number_dict(feature_row, PARAMETER_COLUMNS),
                intermediate_metrics=_number_dict(feature_row, INTERMEDIATE_METRIC_COLUMNS),
                predicted_quality=predicted,
                uncertainty=uncertainty,
                score=score,
                rationale=(
                    "先按材料和目标质量检索相似历史案例，再按材料构造中间量，"
                    f"用 {algo_label} 在 {len(frame)} 条候选样本上拟合并生成该候选。"
                ),
                material_explanation=_material_explanation(material),
                similar_cases=similar_cases,
                feature_importance=feature_importance,
                error_metrics=best_error_metrics,
                training_info=training_info,
            )
        )

    if recommendations:
        notes.append(
            f"已训练 {len(models)} 个{algo_label}回归模型，输入特征：{', '.join(feature_columns)}；"
            f"拟合目标：{', '.join(models.keys())}。"
        )
    return recommendations, notes


def recommend_parameters(request: RecommendationRequest) -> RecommendationResponse:
    dataset = load_dataset()
    notes: list[str] = []
    if dataset.empty:
        return RecommendationResponse(
            dataset_size=0,
            candidate_size=0,
            model_info=MODEL_INFO,
            recommendations=[],
            notes=["未找到原始数据。"],
        )

    candidates = dataset
    if request.material:
        exact = candidates[candidates["material"] == request.material]
        if exact.empty:
            fuzzy = candidates[candidates["material"].str.contains(request.material, case=False, na=False)]
            candidates = fuzzy if not fuzzy.empty else candidates
            if fuzzy.empty:
                notes.append(f"未找到材料 {request.material} 的样本，已回退到全量数据。")
        else:
            candidates = exact

    _validate_observed_target_ranges(candidates, request)

    constrained = _apply_constraints(candidates, request.constraints)
    if constrained.empty:
        notes.append("参数约束过滤后无样本，已忽略约束并使用材料候选集。")
    else:
        candidates = constrained

    candidates = _add_intermediate_columns(candidates, material=request.material)

    scored_rows = [
        (index, _score_row(row, candidates, request))
        for index, row in candidates.iterrows()
    ]
    scored_rows.sort(key=lambda item: item[1])
    top = scored_rows[: request.top_k]
    similar_rows = scored_rows[: min(3, len(scored_rows))]
    similar_cases = [_case_match(candidates.loc[index], score) for index, score in similar_rows]
    uncertainty = _uncertainty(candidates)

    recommendations, ml_notes = _ml_recommendations(candidates, scored_rows, similar_cases, request)
    notes.extend(ml_notes)

    for rank, (index, raw_score) in enumerate(top[: request.top_k], start=1):
        row = candidates.loc[index]
        quality = _number_dict(row, QUALITY_COLUMNS)
        score = round(1.0 / (1.0 + max(raw_score, 0.0)), 4)
        rationale = (
            f"基于 {row['material']} 的历史案例 {row['case_id']}，"
            f"该参数组合在目标质量约束下的相似度得分为 {score}。"
        )
        recommendations.append(
            ParameterRecommendation(
                rank=rank,
                generation_method="historical_similarity",
                model_name=None,
                parameters=_number_dict(row, PARAMETER_COLUMNS),
                intermediate_metrics=_number_dict(row, INTERMEDIATE_METRIC_COLUMNS),
                predicted_quality=quality,
                uncertainty=uncertainty,
                score=score,
                rationale=rationale,
                material_explanation=_material_explanation(row.get("material")),
                similar_cases=similar_cases,
            )
        )

    return RecommendationResponse(
        dataset_size=int(len(dataset)),
        candidate_size=int(len(candidates)),
        model_info=MODEL_INFO,
        recommendations=recommendations,
        notes=notes,
    )
