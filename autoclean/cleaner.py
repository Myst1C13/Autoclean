# autoclean/cleaner.py
from __future__ import annotations

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd


BOOL_TRUE = {"true", "t", "yes", "y", "1"}
BOOL_FALSE = {"false", "f", "no", "n", "0"}


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _parse_bool(series: pd.Series) -> pd.Series:
    s = series.copy()

    # normalize
    s = s.astype("string")
    s = s.str.strip().str.lower()

    # treat empty-ish tokens as missing
    s = s.replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})

    out = pd.Series(pd.NA, index=s.index, dtype="boolean")
    out[s.isin(BOOL_TRUE)] = True
    out[s.isin(BOOL_FALSE)] = False

    if series.dtype == bool:
        out = series.astype("boolean")

    return out


def _try_parse_datetime(df: pd.DataFrame, col: str, actions: List[str]) -> None:
    if col not in df.columns:
        return
    before_na = df[col].isna().sum()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    after_na = df[col].isna().sum()
    actions.append(f"try_parse_datetime: {col} (na {before_na}->{after_na})")


def _fill_missing_numeric(df: pd.DataFrame, col: str, strategy: str, actions: List[str]) -> None:
    if col not in df.columns:
        return

    df[col] = _to_numeric(df[col])
    before = int(df[col].isna().sum())
    if before == 0:
        return

    if strategy == "median":
        val = df[col].median(skipna=True)
    elif strategy == "mean":
        val = df[col].mean(skipna=True)
    elif strategy == "mode":
        m = df[col].mode(dropna=True)
        val = m.iloc[0] if len(m) else np.nan
    else:
        raise ValueError(f"Unknown numeric fill strategy: {strategy}")

    if pd.isna(val):
        return

    df[col] = df[col].fillna(val)
    after = int(df[col].isna().sum())
    actions.append(f"fill_missing: {col} ({strategy}) (na {before}->{after})")


def _fill_missing_bool_mode(df: pd.DataFrame, col: str, actions: List[str]) -> None:
    if col not in df.columns:
        return

    df[col] = _parse_bool(df[col])
    before = int(df[col].isna().sum())
    if before == 0:
        return

    mode_vals = df[col].mode(dropna=True)
    fill_val = mode_vals.iloc[0] if len(mode_vals) else False
    df[col] = df[col].fillna(fill_val).astype("boolean")

    after = int(df[col].isna().sum())
    actions.append(f"fill_missing: {col} (mode={bool(fill_val)}) (na {before}->{after})")


def _fill_missing_categorical_unknown(df: pd.DataFrame, col: str, actions: List[str]) -> None:
    if col not in df.columns:
        return

    # Only for non-numeric columns
    if pd.api.types.is_numeric_dtype(df[col]):
        return

    before = int(df[col].isna().sum())
    if before == 0:
        return

    df[col] = df[col].fillna("Unknown")
    after = int(df[col].isna().sum())
    actions.append(f"fill_missing: {col} (categorical='Unknown') (na {before}->{after})")


def _cap_outliers_iqr(df: pd.DataFrame, col: str, actions: List[str], k: float = 1.5) -> None:
    if col not in df.columns:
        return
    if not pd.api.types.is_numeric_dtype(df[col]):
        return
    if pd.api.types.is_bool_dtype(df[col]) or str(df[col].dtype) == "boolean":
        return

    s = df[col].dropna()
    if s.empty:
        return

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return

    lo = q1 - k * iqr
    hi = q3 + k * iqr

    before = df[col].copy()
    df[col] = df[col].clip(lower=lo, upper=hi)

    changed = int((before.notna() & (before != df[col])).sum())
    if changed:
        actions.append(f"cap_outliers: {col} (changed {changed})")


def _reconcile_price_qty_total(
    df: pd.DataFrame,
    price_col: str = "price_per_unit",
    qty_col: str = "quantity",
    total_col: str = "total_spent",
    actions: Optional[List[str]] = None,
) -> int:
    if actions is None:
        actions = []

    for c in (price_col, qty_col, total_col):
        if c in df.columns:
            df[c] = _to_numeric(df[c])

    if not all(c in df.columns for c in (price_col, qty_col, total_col)):
        return 0

    p = df[price_col]
    q = df[qty_col]
    t = df[total_col]

    filled = 0

    mask = p.notna() & q.notna() & t.isna()
    if mask.any():
        df.loc[mask, total_col] = (p[mask] * q[mask]).round(2)
        filled += int(mask.sum())

    mask = t.notna() & q.notna() & p.isna() & (q != 0)
    if mask.any():
        df.loc[mask, price_col] = (t[mask] / q[mask]).round(2)
        filled += int(mask.sum())

    mask = t.notna() & p.notna() & q.isna() & (p != 0)
    if mask.any():
        df.loc[mask, qty_col] = (t[mask] / p[mask]).round(2)
        filled += int(mask.sum())

    if filled > 0:
        actions.append(f"reconcile: filled {filled} values across price/qty/total")
    return filled


def clean_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    cleaned = df.copy()
    actions: List[str] = []

    # --- Normalize common missing tokens in object columns ---
    for c in cleaned.columns:
        if cleaned[c].dtype == object or pd.api.types.is_string_dtype(cleaned[c]):
            cleaned[c] = (
                cleaned[c]
                .astype("string")
                .str.strip()
                .replace(
                    {
                        "": pd.NA,
                        "NA": pd.NA,
                        "N/A": pd.NA,
                        "null": pd.NA,
                        "None": pd.NA,
                        "nan": pd.NA,
                        "?": pd.NA,      # ✅ if any survived ingestion
                    }
                )
            )

    actions.append("normalize_strings: stripped whitespace + standardized missing markers")

    # --- Parse known special columns if present ---
    _try_parse_datetime(cleaned, "transaction_date", actions)

    if "discount_applied" in cleaned.columns:
        actions.append("try_parse_bool: discount_applied")
        cleaned["discount_applied"] = _parse_bool(cleaned["discount_applied"])

    # --- Ensure numeric cols for known retail schema (if present) ---
    for num_col in ["price_per_unit", "quantity", "total_spent"]:
        if num_col in cleaned.columns:
            cleaned[num_col] = _to_numeric(cleaned[num_col])

    # --- Reconcile retail math relationship first (if present) ---
    _reconcile_price_qty_total(cleaned, actions=actions)

    # --- Fill numeric missing (median is safest default) ---
    # Skip boolean dtype columns — they are handled separately below
    for col in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[col]) and not (
            pd.api.types.is_bool_dtype(cleaned[col]) or str(cleaned[col].dtype) == "boolean"
        ):
            _fill_missing_numeric(cleaned, col, strategy="median", actions=actions)

    # --- Fill boolean missing (mode) ---
    for col in cleaned.columns:
        if pd.api.types.is_bool_dtype(cleaned[col]) or str(cleaned[col].dtype) == "boolean":
            _fill_missing_bool_mode(cleaned, col, actions)

    # --- Fill categorical missing with "Unknown" ---
    for col in cleaned.columns:
        _fill_missing_categorical_unknown(cleaned, col, actions)

    # --- Outlier capping (optional): numeric columns only ---
    for col in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[col]):
            _cap_outliers_iqr(cleaned, col, actions)

    return cleaned, actions