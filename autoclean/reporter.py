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


def _build_html(report: Dict[str, Any]) -> str:
    b = report["before"]
    a = report["after"]
    actions = report.get("actions", [])

    def fmt(v: Any, f: str = ".2f") -> str:
        return format(v, f) if isinstance(v, (int, float)) else str(v)

    def delta_class(key: str) -> str:
        bv, av = b.get(key), a.get(key)
        if not (isinstance(bv, (int, float)) and isinstance(av, (int, float))):
            return ""
        diff = av - bv
        # For health score, higher is better; for issues, lower is better
        good = diff > 0 if key == "data_health_score" else diff < 0
        return "good" if good else ("bad" if diff != 0 else "")

    metric_rows = ""
    for label, key, f in [
        ("Rows",         "rows",              ".0f"),
        ("Missing %",    "missing_percent",   ".2f"),
        ("Duplicate %",  "duplicate_percent", ".2f"),
        ("Outlier %",    "outlier_percent",   ".2f"),
        ("Health Score", "data_health_score", ".1f"),
    ]:
        bv, av = b.get(key), a.get(key)
        delta_str = ""
        cls = delta_class(key)
        if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
            d = av - bv
            delta_str = ("+" if d > 0 else "") + format(d, f)
        metric_rows += (
            f"<tr><td>{label}</td><td>{fmt(bv, f)}</td>"
            f"<td>{fmt(av, f)}</td><td class='{cls}'>{delta_str}</td></tr>\n"
        )

    action_items = "\n".join(f"<li><code>{a}</code></li>" for a in actions) or "<li>No actions recorded</li>"

    score_before = fmt(b.get("data_health_score", 0), ".1f")
    score_after  = fmt(a.get("data_health_score", 0), ".1f")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AutoClean Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f7f8fa; color: #1a1a1a; padding: 2rem; }}
  .card {{ background: #fff; border-radius: 10px; padding: 1.5rem 2rem;
           box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 1.5rem; }}
  h1 {{ font-size: 1.8rem; margin-bottom: .25rem; }}
  .meta {{ color: #666; font-size: .85rem; margin-bottom: 1.5rem; }}
  h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #333; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th {{ text-align: left; padding: .5rem .75rem; background: #f0f1f3;
        font-weight: 600; border-radius: 4px; }}
  td {{ padding: .5rem .75rem; border-bottom: 1px solid #f0f1f3; }}
  .good {{ color: #16a34a; font-weight: 600; }}
  .bad  {{ color: #dc2626; font-weight: 600; }}
  .scores {{ display: flex; gap: 1.5rem; }}
  .score-box {{ flex: 1; text-align: center; padding: 1.5rem;
                border-radius: 8px; color: #fff; }}
  .score-box.before {{ background: #e05252; }}
  .score-box.after  {{ background: #2ecc71; }}
  .score-box .num {{ font-size: 2.5rem; font-weight: 700; line-height: 1; }}
  .score-box .lbl {{ font-size: .8rem; opacity: .9; margin-top: .3rem; }}
  ul {{ padding-left: 1.2rem; }}
  li {{ margin-bottom: .35rem; font-size: .875rem; }}
  code {{ background: #f0f1f3; padding: .1rem .35rem; border-radius: 4px;
          font-size: .8rem; }}
  footer {{ text-align: center; color: #aaa; font-size: .8rem; margin-top: 1rem; }}
</style>
</head>
<body>

<div class="card">
  <h1>🧹 AutoClean Report</h1>
  <p class="meta">
    Generated: {report['generated_at']}<br/>
    Input: <code>{report['input_path']}</code><br/>
    Output: <code>{report['output_path']}</code>
  </p>

  <h2>Health Score</h2>
  <div class="scores">
    <div class="score-box before">
      <div class="num">{score_before}</div>
      <div class="lbl">Before</div>
    </div>
    <div class="score-box after">
      <div class="num">{score_after}</div>
      <div class="lbl">After</div>
    </div>
  </div>
</div>

<div class="card">
  <h2>Summary Metrics</h2>
  <table>
    <thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Δ</th></tr></thead>
    <tbody>{metric_rows}</tbody>
  </table>
</div>

<div class="card">
  <h2>Cleaning Actions ({len(actions)})</h2>
  <ul>{action_items}</ul>
</div>

<footer>AutoClean — automated data quality pipeline</footer>
</body>
</html>
"""


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
      - a sibling HTML file with same stem (report.html)
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

    base = os.path.splitext(report_path)[0]

    # Write JSON
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Write Markdown
    md_path = base + ".md"
    _safe_makedirs_for_file(md_path)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(report))

    # Write HTML
    html_path = base + ".html"
    _safe_makedirs_for_file(html_path)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_build_html(report))