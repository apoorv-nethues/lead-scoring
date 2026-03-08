"""
API routes for the Lead Scoring demo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .predict_service import get_base_dir, predict_for_rows

router = APIRouter(prefix="/api", tags=["api"])

# Path to input CSV - configurable via env
INPUT_CSV = os.environ.get(
    "INPUT_CSV",
    str(Path(__file__).resolve().parent.parent / "data" / "holdout" / "manual_review_sample_v2.csv"),
)
BASE_DIR = Path(os.environ.get("BASE_DIR", str(get_base_dir())))


def _to_serializable(obj: Any) -> Any:
    """Convert numpy/pandas types for JSON."""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if pd.isna(obj):
        return None
    return obj


# Lazy-loaded dataframe for pagination
_dataframe: pd.DataFrame | None = None


def _get_df() -> pd.DataFrame:
    global _dataframe
    if _dataframe is None:
        path = Path(INPUT_CSV)
        if not path.exists():
            raise FileNotFoundError(f"Input CSV not found: {path}")
        _dataframe = pd.read_csv(path, low_memory=False)
    return _dataframe


@router.get("/data/preview")
def get_data_preview(page: int = 1, page_size: int = 50) -> dict[str, Any]:
    """Paginated preview of the input CSV. Rows are 1-indexed."""
    df = _get_df()
    total = len(df)
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50
    start = (page - 1) * page_size
    end = start + page_size
    slice_df = df.iloc[start:end]
    # Convert to records with row numbers (1-indexed)
    records = []
    for i, (_, row) in enumerate(slice_df.iterrows()):
        row_num = start + i + 1
        rec = {"row": row_num, **{k: _to_serializable(v) for k, v in row.to_dict().items()}}
        records.append(rec)
    return {
        "rows": records,
        "page": page,
        "page_size": page_size,
        "total_rows": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/data/row/{row_num}")
def get_row(row_num: int) -> dict[str, Any]:
    """Get a single row by 1-indexed row number."""
    df = _get_df()
    if row_num < 1 or row_num > len(df):
        raise HTTPException(status_code=404, detail=f"Row {row_num} not found. Valid range: 1–{len(df)}")
    row = df.iloc[row_num - 1]
    rec = {"row": row_num, **{k: _to_serializable(v) for k, v in row.to_dict().items()}}
    return rec


class PredictRequest(BaseModel):
    row_numbers: list[int]


@router.post("/predict")
def predict(request: PredictRequest) -> dict[str, Any]:
    """Predict scores for given row numbers (1-indexed)."""
    if not request.row_numbers:
        raise HTTPException(status_code=400, detail="row_numbers cannot be empty")
    df = _get_df()
    max_row = len(df)
    invalid = [r for r in request.row_numbers if r < 1 or r > max_row]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid row numbers: {invalid}. Valid range: 1–{max_row}",
        )
    try:
        results = predict_for_rows(INPUT_CSV, request.row_numbers, base_dir=BASE_DIR)
        return {"predictions": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/glossary")
def get_glossary() -> dict[str, Any]:
    """Non-technical explanations of columns, metrics, and focus C vs E."""
    import json
    glossary_path = Path(__file__).resolve().parent / "glossary.json"
    with open(glossary_path) as f:
        return json.load(f)
