import pandas as pd
import numpy as np

from pandas.api.types import (
    is_numeric_dtype,
    is_bool_dtype,
    is_datetime64_any_dtype,
)

# Keep these lowercase because we normalize strings to lowercase
MISSING_MARKERS = {
    "", "?", "na", "n/a", "null", "none", "nan"
}


def _normalize_missing_tokens(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make missing detection consistent even when CSV wasn't loaded with na_values.
    - strip whitespace in string/object cols
    - lowercase
    - turn common missing markers into real NaN
    """
    df = df.copy()
    obj_cols = df.select_dtypes(include=["object", "string"]).columns

    for c in obj_cols:
        s = (
            df[c]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        # after strip+lower, convert markers to NA
        s = s.replace({m: pd.NA for m in MISSING_MARKERS})

        df[c] = s

    return df


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """Best-effort coerce dirty numeric strings -> floats (NaN on failure)."""
    if is_numeric_dtype(series):
        return series

    # Don't try to coerce datetimes / booleans into numeric
    if is_datetime64_any_dtype(series) or is_bool_dtype(series):
        return pd.Series([np.nan] * len(series), index=series.index)

    cleaned = (
        series.astype("string")
        .str.replace(r"[\$,]", "", regex=True)
        .str.replace(r"\[.*?\]", "", regex=True)
        .str.replace(r"[†‡]", "", regex=True)
        .str.strip()
        .str.lower()
    )

    cleaned = cleaned.replace({m: pd.NA for m in MISSING_MARKERS})

    return pd.to_numeric(cleaned, errors="coerce")


def infer_column_type(series: pd.Series) -> str:
    """Infer semantic column type."""
    if is_datetime64_any_dtype(series):
        return "datetime"

    if is_bool_dtype(series):
        return "binary"

    if is_numeric_dtype(series):
        return "numeric"

    numeric_version = clean_numeric_series(series)
    if numeric_version.notna().mean() > 0.8:
        return "numeric"

    n = len(series)
    if n == 0:
        return "categorical"

    nunique = series.nunique(dropna=True)

    if nunique == 2:
        return "binary"

    unique_ratio = nunique / n
    if unique_ratio > 0.9:
        return "id"

    return "categorical"


def calculate_entropy(series: pd.Series) -> float:
    probs = series.dropna().value_counts(normalize=True)
    if probs.empty:
        return 0.0
    return float(-(probs * np.log2(probs + 1e-9)).sum())


def detect_outliers(series: pd.Series) -> int:
    if not is_numeric_dtype(series):
        return 0

    s = series.dropna()
    if len(s) < 3:
        return 0

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1

    if pd.isna(iqr) or iqr == 0:
        return 0

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((s < lower) | (s > upper)).sum())


def profile_dataset(df: pd.DataFrame) -> dict:
    # normalize missing tokens so missing% is accurate
    df = _normalize_missing_tokens(df)

    profile: dict = {}
    column_profiles: dict = {}

    rows, cols = df.shape
    total_cells = rows * cols

    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    total_outliers = 0

    for col in df.columns:
        raw_col = df[col]
        col_type = infer_column_type(raw_col)

        col_profile = {
            "type": col_type,
            "missing_percent": round(raw_col.isna().mean() * 100, 2) if rows else 0.0,
            "cardinality": int(raw_col.nunique(dropna=True)),
        }

        if col_type == "numeric":
            numeric_col = clean_numeric_series(raw_col).dropna()

            if len(numeric_col) >= 3:
                col_profile["skew"] = round(float(numeric_col.skew()), 2)
                outliers = detect_outliers(numeric_col)
            else:
                col_profile["skew"] = None
                outliers = 0

            col_profile["outliers"] = outliers
            total_outliers += outliers

        if col_type == "categorical":
            col_profile["entropy"] = round(calculate_entropy(raw_col), 2)

        column_profiles[col] = col_profile

    # ---- Data Health Score ----
    if rows == 0 or total_cells == 0:
        health_score = None
        missing_percent = 0.0
        duplicate_percent = 0.0
        outlier_percent = 0.0
    else:
        missing_penalty = (missing_cells / total_cells) * 40
        duplicate_penalty = (duplicate_rows / rows) * 20
        outlier_penalty = min((total_outliers / total_cells) * 30, 30)

        total_penalty = missing_penalty + duplicate_penalty + outlier_penalty

        if np.isnan(total_penalty) or np.isinf(total_penalty):
            health_score = 0.0
        else:
            health_score = round(max(0.0, 100.0 - float(total_penalty)), 2)

        missing_percent = round((missing_cells / total_cells) * 100, 2)
        duplicate_percent = round((duplicate_rows / rows) * 100, 2)
        outlier_percent = round((total_outliers / total_cells) * 100, 2)

    profile["rows"] = rows
    profile["columns"] = cols
    profile["missing_percent"] = missing_percent
    profile["duplicate_percent"] = duplicate_percent
    profile["outlier_percent"] = outlier_percent
    profile["data_health_score"] = health_score
    profile["columns_profile"] = column_profiles

    return profile