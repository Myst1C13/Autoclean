# autoclean/main.py
import os
import pandas as pd
from typing import Optional

from .profiler import profile_dataset
from .cleaner import clean_dataset
from .reporter import write_report


def _safe_makedirs_for_file(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def run_pipeline(input_path: str, output_path: str, report_path: Optional[str] = None):
    # -----------------------------
    # Load dataset (robust parsing)
    # -----------------------------
    try:
        df = pd.read_csv(
            input_path,
            na_values=["?", " ?"],        # ✅ UCI Adult-style missing markers
            keep_default_na=True,
            skipinitialspace=True         # ✅ trims leading spaces after commas
        )
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV: {input_path} ({type(e).__name__}: {e})")

    # Normalize column names ONCE
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print("\n=== DATASET LOADED ===")
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(df.head())

    # -----------------------------
    # Profile BEFORE cleaning (safe)
    # -----------------------------
    try:
        profile_before = profile_dataset(df)
    except Exception as e:
        profile_before = {
            "rows": len(df),
            "columns": df.shape[1],
            "missing_percent": round(df.isna().mean().mean() * 100, 2),
            "duplicate_percent": round(df.duplicated().mean() * 100, 2),
            "outlier_percent": 0.0,
            "data_health_score": None,
            "columns_profile": {},
            "error": f"profiling_failed: {type(e).__name__}",
        }

    print("\n=== BEFORE CLEANING ===")
    print(f"Rows: {profile_before.get('rows')}")
    print(f"Missing %: {profile_before.get('missing_percent'):.2f}")
    print(f"Duplicate %: {profile_before.get('duplicate_percent'):.2f}")
    print(f"Outlier %: {profile_before.get('outlier_percent'):.2f}")

    bscore = profile_before.get("data_health_score")
    print(
        f"Data Health Score: {bscore:.2f} / 100"
        if isinstance(bscore, (int, float))
        else "Data Health Score: N/A"
    )

    # -----------------------------
    # Clean dataset
    # -----------------------------
    cleaned_df, changes = clean_dataset(df)

    print("\n=== CLEANING SUMMARY ===")
    for msg in changes:
        print(f"- {msg}")

    # -----------------------------
    # Profile AFTER cleaning (safe)
    # -----------------------------
    try:
        profile_after = profile_dataset(cleaned_df)
    except Exception as e:
        profile_after = {
            "rows": len(cleaned_df),
            "columns": cleaned_df.shape[1],
            "missing_percent": round(cleaned_df.isna().mean().mean() * 100, 2),
            "duplicate_percent": round(cleaned_df.duplicated().mean() * 100, 2),
            "outlier_percent": 0.0,
            "data_health_score": None,
            "columns_profile": {},
            "error": f"profiling_failed: {type(e).__name__}",
        }

    print("\n=== AFTER CLEANING ===")
    print(f"Rows: {profile_after.get('rows')}")
    print(f"Missing %: {profile_after.get('missing_percent'):.2f}")
    print(f"Duplicate %: {profile_after.get('duplicate_percent'):.2f}")
    print(f"Outlier %: {profile_after.get('outlier_percent'):.2f}")

    ascore = profile_after.get("data_health_score")
    print(
        f"Data Health Score: {ascore:.2f} / 100"
        if isinstance(ascore, (int, float))
        else "Data Health Score: N/A"
    )

    # -----------------------------
    # Save cleaned dataset (safe)
    # -----------------------------
    try:
        _safe_makedirs_for_file(output_path)
        cleaned_df.to_csv(output_path, index=False)
        print("\nCleaned dataset saved to", output_path)
    except Exception as e:
        raise RuntimeError(f"Failed to save cleaned CSV: {output_path} ({type(e).__name__}: {e})")

    # -----------------------------
    # Write report (optional)
    # -----------------------------
    if report_path:
        write_report(
            report_path=report_path,
            input_path=input_path,
            output_path=output_path,
            profile_before=profile_before,
            profile_after=profile_after,
            actions=changes,
        )
        print("\nReport saved to", report_path)

    return profile_before, profile_after, changes