"""Library estimators with fold-local mechanism transforms and grouped selection."""
from __future__ import annotations

import time
import warnings
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, ElasticNet, BayesianRidge, HuberRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.services.data_loader import PARAMETER_COLUMNS
from app.services.recommender import _add_intermediate_columns

REGISTRY = {
    "linear_regression": ("OLS", "Linear", lambda: LinearRegression()),
    "ridge": ("Ridge", "Linear", lambda: Ridge(alpha=10)),
    "elasticnet": ("ElasticNet", "Linear", lambda: ElasticNet(alpha=.1, l1_ratio=.5, max_iter=5000)),
    "bayesian_ridge": ("Bayesian Ridge", "Linear", lambda: BayesianRidge()),
    "huber": ("Huber", "Linear", lambda: HuberRegressor(max_iter=500)),
    "knn": ("KNN", "Local", lambda: KNeighborsRegressor(n_neighbors=3)),
    "svr": ("SVR", "Kernel", lambda: SVR()),
    "decision_tree": ("Decision Tree", "Tree", lambda: DecisionTreeRegressor(max_depth=4, min_samples_leaf=2, random_state=42)),
    "random_forest": ("Random Forest", "Ensemble", lambda: RandomForestRegressor(n_estimators=80, min_samples_leaf=2, random_state=42, n_jobs=1)),
    "extra_trees": ("Extra Trees", "Ensemble", lambda: ExtraTreesRegressor(n_estimators=80, min_samples_leaf=2, random_state=42, n_jobs=1)),
    "gradient_boosting": ("Gradient Boosting", "Ensemble", lambda: GradientBoostingRegressor(n_estimators=80, max_depth=2, random_state=42)),
    "hist_gradient_boosting": ("Histogram Gradient Boosting", "Ensemble", lambda: HistGradientBoostingRegressor(max_iter=80, max_leaf_nodes=7, random_state=42)),
    "gaussian_process": ("Gaussian Process", "Kernel", lambda: GaussianProcessRegressor(kernel=Matern()+WhiteKernel(), normalize_y=True, optimizer=None)),
    "neural_network": ("MLP", "Neural", lambda: MLPRegressor(hidden_layer_sizes=(32,), max_iter=400, random_state=42)),
}
DEFAULT_MODELS = ["ridge", "elasticnet", "bayesian_ridge", "random_forest", "extra_trees", "svr"]


def groups(frame):
    # All recorded process inputs, not the selected feature subset, define a group.
    columns = [c for c in ["material", *PARAMETER_COLUMNS] if c in frame]
    return pd.util.hash_pandas_object(frame[columns].fillna("missing"), index=False).astype(str).to_numpy()


class MechanismFeatures(BaseEstimator, TransformerMixin):
    def __init__(self, mode="fusion"):
        self.mode = mode

    def fit(self, X, y=None):
        from app.services.agent_formulas import approved
        self.formulas_ = approved()
        self.reference_ = X.copy()
        if y is not None:
            # A response-derived threshold is fitted only inside the training fold.
            self.reference_["depth_um"] = np.asarray(y) if getattr(y, "name", None) == "depth_um" else np.nan
        transformed = self._transform(X)
        self.columns_ = [c for c in transformed if transformed[c].notna().any()]
        return self

    def _transform(self, X):
        raw = [c for c in PARAMETER_COLUMNS if c in X]
        if self.mode == "raw":
            return X[raw].apply(pd.to_numeric, errors="coerce")
        # Remove all response columns before feature construction.
        safe = X[[c for c in ["material", *PARAMETER_COLUMNS] if c in X]].copy()
        from app.services.agent_formulas import calculate
        enriched = calculate(_add_intermediate_columns(safe, reference_frame=self.reference_), self.formulas_)
        additional = [c for c in enriched if c not in safe]
        if self.mode == "geometry":
            additional = [c for c in additional if c in {"line_pulse_density_pulses_mm", "pulse_spacing_um", "cumulative_pulse_density", "dose_index"}]
        elif self.mode == "thermal":
            additional = [c for c in additional if c in {"pulse_time_interaction", "duty_cycle", "power_chain_proxy_w", "marking_energy_proxy"}]
        return enriched[raw+additional].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)

    def transform(self, X):
        return self._transform(X).reindex(columns=self.columns_)


def pipeline(key, mode="fusion"):
    return Pipeline([("mechanism", MechanismFeatures(mode)), ("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("regressor", REGISTRY[key][2]())])


def select_model(frame, target, candidates=None, mode="fusion", budget_seconds=30):
    train = frame.loc[frame[target].notna()].copy()
    train = train.loc[train[target] >= 0]
    grouped = groups(train)
    count = len(set(grouped))
    if len(train) < 8 or count < 3:
        raise ValueError(f"{target} 至少需要 8 条有效测量和 3 个独立参数组")
    splits = list(GroupKFold(n_splits=min(3, count)).split(train, groups=grouped))
    audit, best = [], None
    started = time.monotonic()
    for key in (candidates or DEFAULT_MODELS):
        if key not in REGISTRY:
            continue
        if audit and time.monotonic()-started > budget_seconds:
            audit.append({"algorithm": key, "status": "budget_skipped"})
            continue
        try:
            model = pipeline(key, mode)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pred = cross_val_predict(model, train, train[target], cv=splits, n_jobs=1)
            error = float(mean_squared_error(train[target], pred)**.5)
            audit.append({"algorithm": key, "status": "evaluated", "rmse": error, "mae": float(mean_absolute_error(train[target], pred)), "r2": float(r2_score(train[target], pred))})
            if best is None or error < best[0]-1e-10:
                best = error, key, model
        except (ValueError, FloatingPointError) as exc:
            audit.append({"algorithm": key, "status": "failed", "reason": str(exc)[:200]})
    if best is None:
        raise ValueError("候选模型均未通过分组验证，请补充有效数据")
    error, key, model = best
    model.fit(train, train[target])
    return model, {"selected": key, "validation_rmse": error, "groups": count, "samples": len(train), "candidates": audit, "reason": "Minimum development-set grouped validation RMSE"}
