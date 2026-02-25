# autoclean/cli.py
import argparse
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .main import run_pipeline

console = Console()


def fmt2(x):
    return f"{x:.2f}" if isinstance(x, (int, float)) else "N/A"


def main():
    parser = argparse.ArgumentParser(
        description="AutoClean++ — Intelligent Data Quality & Cleaning Tool"
    )

    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save cleaned CSV (optional). If omitted, auto-generates based on input filename."
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path to save report JSON (optional). If omitted, no report is written."
    )

    args = parser.parse_args()

    # Auto-generate output path if not provided
    if not args.output:
        base = os.path.splitext(os.path.basename(args.input))[0]
        args.output = os.path.join("data", "cleaned", f"{base}_cleaned.csv")

    console.print(
        Panel.fit(
            "[bold cyan]AutoClean++[/bold cyan]\n[white]Intelligent Data Quality Engine[/white]",
            border_style="cyan"
        )
    )

    with console.status("[bold green]Running data pipeline...[/bold green]"):
        before, after, changes = run_pipeline(
            input_path=args.input,
            output_path=args.output,
            report_path=args.report,
        )

    # -------- Summary Table --------
    table = Table(title="Data Quality Summary", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")

    table.add_row("Rows", str(before.get("rows")), str(after.get("rows")))
    table.add_row("Missing %", fmt2(before.get("missing_percent")), fmt2(after.get("missing_percent")))
    table.add_row("Duplicate %", fmt2(before.get("duplicate_percent")), fmt2(after.get("duplicate_percent")))
    table.add_row("Outlier %", fmt2(before.get("outlier_percent")), fmt2(after.get("outlier_percent")))

    table.add_row(
        "Health Score",
        fmt2(before.get("data_health_score")),
        f"[bold green]{fmt2(after.get('data_health_score'))}[/bold green]"
    )

    console.print(table)

    # -------- Changes --------
    console.print("\n[bold]Cleaning Actions[/bold]")
    for msg in changes:
        console.print(f"• {msg}")

    console.print(f"\n[bold green]✔ Cleaned dataset saved to[/bold green] {args.output}")
    if args.report:
        console.print(f"[bold green]✔ Report saved to[/bold green] {args.report}")


if __name__ == "__main__":
    main()