"""
Prediction service for CatBoost v3 focus models.

Extracted from scripts/predict_catboost_v3_focus.py for use by the FastAPI backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from catboost import Pool

MODEL_REGISTRY = {
    "v3_focus_c": {
        "model": "models/tuned_catboost_v3_focus_c.joblib",
        "features": "reports/tuned_catboost_features_v3_focus_c.json",
    },
    "v3_focus_e": {
        "model": "models/tuned_catboost_v3_focus_e.joblib",
        "features": "reports/tuned_catboost_features_v3_focus_e.json",
    },
}


def get_base_dir() -> Path:
    """Project root - used for resolving model/report paths."""
    return Path(__file__).resolve().parent.parent


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same feature engineering used during training."""
    out = df.copy()

    if "epc_date" in out.columns:
        epc_date = pd.to_datetime(out["epc_date"], errors="coerce")
        out["epc_year"] = epc_date.dt.year
        out["epc_month"] = epc_date.dt.month
        out["epc_quarter"] = epc_date.dt.quarter

    if "CURRENT_ENERGY_EFFICIENCY" in out.columns and "POTENTIAL_ENERGY_EFFICIENCY" in out.columns:
        curr = pd.to_numeric(out["CURRENT_ENERGY_EFFICIENCY"], errors="coerce")
        pot = pd.to_numeric(out["POTENTIAL_ENERGY_EFFICIENCY"], errors="coerce")
        out["efficiency_gap"] = pot - curr
        out["efficiency_ratio"] = pot / curr.replace(0, np.nan)

    if "TOTAL_FLOOR_AREA" in out.columns:
        floor = pd.to_numeric(out["TOTAL_FLOOR_AREA"], errors="coerce")
        out["total_floor_area_log1p"] = np.log1p(floor)

    for col in [
        "CURRENT_ENERGY_EFFICIENCY",
        "POTENTIAL_ENERGY_EFFICIENCY",
        "TOTAL_FLOOR_AREA",
    ]:
        if col in out.columns:
            out[f"{col}__missing"] = pd.to_numeric(out[col], errors="coerce").isna()
        else:
            out[f"{col}__missing"] = True

    if "PROPERTY_TYPE" in out.columns and "TENURE" in out.columns:
        out["property_type__tenure"] = out["PROPERTY_TYPE"].astype(str) + " | " + out["TENURE"].astype(str)
    if "PROPERTY_TYPE" in out.columns and "BUILT_FORM" in out.columns:
        out["property_type__built_form"] = out["PROPERTY_TYPE"].astype(str) + " | " + out["BUILT_FORM"].astype(str)
    if "PROPERTY_TYPE" in out.columns and "CONSTRUCTION_AGE_BAND" in out.columns:
        out["property_type__age_band"] = out["PROPERTY_TYPE"].astype(str) + " | " + out["CONSTRUCTION_AGE_BAND"].astype(str)

    return out


def _load_variant(variant: str, base_dir: Path | None = None) -> tuple[object, list[str], list[str], list[str]]:
    base = base_dir or get_base_dir()
    cfg = MODEL_REGISTRY[variant]
    model_path = base / cfg["model"]
    features_path = base / cfg["features"]
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Feature metadata not found: {features_path}")

    model = joblib.load(model_path)
    meta = json.loads(features_path.read_text())
    cat_cols = list(meta["categorical"])
    num_cols = list(meta["numeric"])
    feature_cols = list(getattr(model, "feature_names_", []) or (cat_cols + num_cols))
    return model, cat_cols, num_cols, feature_cols


def _predict_scores(
    model: object,
    df: pd.DataFrame,
    cat_cols: list[str],
    feature_cols: list[str],
) -> np.ndarray:
    X = df.copy()
    for col in feature_cols:
        if col not in X.columns:
            X[col] = np.nan
    X = X[feature_cols]
    for col in cat_cols:
        X[col] = X[col].astype("string").fillna("Unknown").astype(str)
        X[col] = X[col].replace({"nan": "Unknown", "NaN": "Unknown", "<NA>": "Unknown", "None": "Unknown"})
    num_cols = [c for c in feature_cols if c not in set(cat_cols)]
    for col in num_cols:
        if col not in X.columns:
            continue
        if col == "epc_date" or col.endswith("_date"):
            dt = pd.to_datetime(X[col], errors="coerce")
            X[col] = dt.astype("int64")
            X.loc[dt.isna(), col] = np.nan
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce")
    pool = Pool(X, cat_features=cat_cols)
    return model.predict_proba(pool)[:, 1]


def predict_for_rows(
    input_path: Path | str,
    row_numbers: list[int],
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Load CSV, select rows by 1-indexed row number, and return scores for both focus variants.

    Returns a list of dicts: [{"row": 1, "score_focus_c": 0.01, "score_focus_e": 0.02}, ...]
    """
    base = base_dir or get_base_dir()
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    raw = pd.read_csv(input_path, low_memory=False)
    max_row = len(raw)
    valid_rows = [r for r in row_numbers if 1 <= r <= max_row]
    if not valid_rows:
        raise ValueError(f"No valid row numbers in range 1–{max_row}")

    # Select rows (1-indexed)
    mask = np.isin(np.arange(1, len(raw) + 1), valid_rows)
    selected = raw.loc[mask].copy()
    selected = selected.reset_index(drop=False).rename(columns={"index": "source_row_0idx"})
    selected["source_row_1idx"] = selected["source_row_0idx"] + 1

    scored_input = apply_feature_engineering(selected)

    # Build a dict row -> {score_focus_c, score_focus_e}
    out: dict[int, dict[str, Any]] = {}
    for i, row_1idx in enumerate(selected["source_row_1idx"]):
        out[int(row_1idx)] = {"row": int(row_1idx)}

    for variant in ["v3_focus_c", "v3_focus_e"]:
        model, cat_cols, _num_cols, feature_cols = _load_variant(variant, base)
        scores = _predict_scores(model, scored_input, cat_cols, feature_cols)
        key = "score_focus_c" if variant == "v3_focus_c" else "score_focus_e"
        for i, row_1idx in enumerate(selected["source_row_1idx"]):
            out[int(row_1idx)][key] = float(scores[i])

    # Return in same order as row_numbers
    return [out[r] for r in row_numbers if r in out]
