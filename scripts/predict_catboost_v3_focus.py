"""
Predict scores for CatBoost v3 focus models on holdout/raw data.

Supports:
- Model variant: v3_focus_c, v3_focus_e, or both.
- Output to CSV and/or terminal.
- Row selection: first N, explicit row numbers, and row ranges.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import Pool

logger = logging.getLogger(__name__)

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict with CatBoost v3 focus models")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument(
        "--variant",
        choices=["v3_focus_c", "v3_focus_e", "both"],
        default="both",
        help="Which model variant to score.",
    )
    parser.add_argument(
        "--output",
        default="reports/v3_focus_holdout_predictions.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--print-scores",
        action="store_true",
        help="Print selected row scores to terminal.",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Do not write CSV output.",
    )
    parser.add_argument(
        "--target",
        default="label",
        help="Target column to keep in output if present.",
    )
    parser.add_argument(
        "--id-column",
        default=None,
        help="Optional ID column to include in output.",
    )
    parser.add_argument(
        "--first-n",
        type=int,
        default=None,
        help="Score only the first N rows (1-indexed).",
    )
    parser.add_argument(
        "--rows",
        default=None,
        help="Comma-separated 1-indexed row numbers (example: 1,5,12).",
    )
    parser.add_argument(
        "--row-range",
        default=None,
        help="Inclusive 1-indexed range 'start:end' (example: 100:250).",
    )
    return parser.parse_args()


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
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


def parse_row_numbers(rows_arg: str | None) -> set[int]:
    if not rows_arg:
        return set()
    out: set[int] = set()
    for token in rows_arg.split(","):
        token = token.strip()
        if not token:
            continue
        n = int(token)
        if n < 1:
            raise ValueError("Row numbers are 1-indexed and must be >= 1.")
        out.add(n)
    return out


def parse_row_range(range_arg: str | None) -> tuple[int, int] | None:
    if not range_arg:
        return None
    if ":" not in range_arg:
        raise ValueError("Row range must be in 'start:end' format.")
    start_s, end_s = range_arg.split(":", 1)
    start = int(start_s)
    end = int(end_s)
    if start < 1 or end < 1 or end < start:
        raise ValueError("Row range must be 1-indexed with end >= start.")
    return start, end


def select_rows(df: pd.DataFrame, first_n: int | None, rows_set: set[int], row_range: tuple[int, int] | None) -> pd.DataFrame:
    idx = np.arange(1, len(df) + 1)
    if first_n is None and not rows_set and row_range is None:
        return df.copy()

    mask = np.zeros(len(df), dtype=bool)
    if first_n is not None:
        if first_n < 1:
            raise ValueError("--first-n must be >= 1")
        mask |= idx <= first_n
    if rows_set:
        mask |= np.isin(idx, list(rows_set))
    if row_range is not None:
        start, end = row_range
        mask |= (idx >= start) & (idx <= end)

    return df.loc[mask].copy()


def load_variant(variant: str) -> tuple[object, list[str], list[str], list[str]]:
    cfg = MODEL_REGISTRY[variant]
    model_path = Path(cfg["model"])
    features_path = Path(cfg["features"])
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


def predict_scores(model, df: pd.DataFrame, cat_cols: list[str], feature_cols: list[str]) -> np.ndarray:
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


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    raw = pd.read_csv(input_path, low_memory=False)
    selected = select_rows(
        raw,
        first_n=args.first_n,
        rows_set=parse_row_numbers(args.rows),
        row_range=parse_row_range(args.row_range),
    )
    selected = selected.reset_index(drop=False).rename(columns={"index": "source_row_0idx"})
    selected["source_row_1idx"] = selected["source_row_0idx"] + 1

    if selected.empty:
        raise ValueError("No rows selected by current row filters.")

    scored_input = apply_feature_engineering(selected)
    variants = ["v3_focus_c", "v3_focus_e"] if args.variant == "both" else [args.variant]

    out = pd.DataFrame(
        {
            "source_row_1idx": selected["source_row_1idx"],
        }
    )
    if args.id_column and args.id_column in selected.columns:
        out[args.id_column] = selected[args.id_column]
    if args.target in selected.columns:
        out[args.target] = selected[args.target]

    for variant in variants:
        model, cat_cols, _num_cols, feature_cols = load_variant(variant)
        scores = predict_scores(model, scored_input, cat_cols, feature_cols)
        out[f"score_{variant}"] = scores

    if not args.no_csv:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(output_path, index=False)
        logger.info("Wrote predictions to %s (rows: %d)", output_path, len(out))

    if args.print_scores:
        print(out.to_string(index=False))
        sys.stdout.flush()

    if args.no_csv and not args.print_scores:
        logger.warning("No output selected. Use --print-scores and/or omit --no-csv.")


if __name__ == "__main__":
    main()
