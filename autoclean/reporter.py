# autoclean/reporter.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from .metrics import compute_health_score


def _safe_makedirs_for_file(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def _ensure_health_score(profile: Dict[str, Any]) -> Dict[str, Any]:
    """If profiler didn't compute data_health_score, compute a fallback."""
    out = dict(profile)
    if not isinstance(out.get("data_health_score"), (int, float)):
        out["data_health_score"] = compute_health_score(
            missing_percent=out.get("missing_percent", 0.0),
            duplicate_percent=out.get("duplicate_percent", 0.0),
            outlier_percent=out.get("outlier_percent", 0.0),
        )
    return out


def _build_markdown(report: Dict[str, Any]) -> str:
    b = report["before"]
    a = report["after"]
    actions = report.get("actions", [])

    lines = []
    lines.append("# AutoClean++ Report")
    lines.append("")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append(f"**Input:** `{report['input_path']}`")
    lines.append(f"**Output:** `{report['output_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Before | After | Δ |")
    lines.append("|---|---:|---:|---:|")

    def row(name: str, key: str, fmt: str = "{:.2f}"):
        bv = b.get(key)
        av = a.get(key)
        if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
            delta = av - bv
            lines.append(f"| {name} | {fmt.format(bv)} | {fmt.format(av)} | {fmt.format(delta)} |")
        else:
            lines.append(f"| {name} | {bv} | {av} |  |")

    row("Rows", "rows", fmt="{:.0f}")
    row("Columns", "columns", fmt="{:.0f}")
    row("Missing %", "missing_percent")
    row("Duplicate %", "duplicate_percent")
    row("Outlier %", "outlier_percent")
    row("Health Score", "data_health_score")

    lines.append("")
    lines.append("## Cleaning Actions")
    lines.append("")
    if actions:
        for act in actions:
            lines.append(f"- {act}")
    else:
        lines.append("- (No actions recorded)")

    return "\n".join(lines) + "\n"


def write_report(
    report_path: str,
    input_path: str,
    output_path: str,
    profile_before: Dict[str, Any],
    profile_after: Dict[str, Any],
    actions: List[str],
) -> None:
    """
    Writes:
      - report_path as JSON
      - a sibling Markdown file with same stem (report.md)
    """
    _safe_makedirs_for_file(report_path)

    before = _ensure_health_score(profile_before)
    after = _ensure_health_score(profile_after)

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": input_path,
        "output_path": output_path,
        "before": before,
        "after": after,
        "actions": actions,
    }

    # Write JSON
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Write Markdown alongside it
    base, ext = os.path.splitext(report_path)
    md_path = base + ".md" if ext else report_path + ".md"
    _safe_makedirs_for_file(md_path)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(report))