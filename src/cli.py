"""
Command-line entry point.

Writes a Markdown report via report_generator.py to --output, and also
prints the same executive-summary numbers to stdout so you get instant
feedback without having to open the file.
"""

import argparse
import sys
from pathlib import Path

from src.csf_loader import load_csf_reference, get_all_subcategory_ids
from src.assessment import load_assessment, validate_assessment
from src.gap_engine import (
    compute_subcategory_gaps,
    compute_category_coverage,
    compute_function_coverage,
)
from src.report_generator import generate_markdown_report, write_report, generate_html_heatmap


def _print_summary(reference, assessment, gaps, category_coverage, function_coverage) -> None:
    print("=" * 60)
    print("NIST CSF 2.0 Gap Analysis")
    print("=" * 60)

    print("\n--- Function Coverage ---")
    for function_id, stats in function_coverage.items():
        name = reference[function_id]["name"]
        print(
            f"{function_id} ({name}): {stats['coverage_percent']}% implemented "
            f"[{stats['implemented']}/{stats['total']}], {stats['partial']} partial"
        )

    print("\n--- Category Coverage ---")
    for function_id, function in reference.items():
        for category_id in function["categories"]:
            stats = category_coverage[category_id]
            print(
                f"  {category_id}: {stats['coverage_percent']}% "
                f"[{stats['implemented']}/{stats['total']}], {stats['partial']} partial"
            )

    print(f"\n--- Gaps ({len(gaps)} subcategories not fully implemented) ---")
    for gap in gaps:
        print(f"  {gap['subcategory_id']} ({gap['category_id']}): {gap['status']}")

    total_subs = sum(len(c["subcategories"]) for f in reference.values() for c in f["categories"].values())
    total_implemented = total_subs - len(gaps)
    overall_pct = round((total_implemented / total_subs) * 100, 1) if total_subs else 0.0
    print(f"\n--- Overall: {overall_pct}% implemented ({total_implemented}/{total_subs}) ---")


def main() -> None:
    parser = argparse.ArgumentParser(description="NIST CSF 2.0 Control Gap Analyzer")
    parser.add_argument(
        "--reference",
        default="data/csf_2_0_reference.yaml",
        help="Path to the CSF 2.0 reference YAML (default: data/csf_2_0_reference.yaml)",
    )
    parser.add_argument(
        "--assessment",
        required=True,
        help="Path to your self-assessment YAML file",
    )
    parser.add_argument(
        "--output",
        default="reports/gap_report.md",
        help="Path to write the Markdown report (default: reports/gap_report.md)",
    )
    parser.add_argument(
        "--heatmap",
        default=None,
        help="Optional path to also write an HTML coverage heatmap (e.g. reports/heatmap.html)",
    )
    args = parser.parse_args()

    reference_path = Path(args.reference)
    assessment_path = Path(args.assessment)

    reference = load_csf_reference(reference_path)
    known_ids = get_all_subcategory_ids(reference)

    assessment = load_assessment(assessment_path)
    errors = validate_assessment(assessment, known_ids)
    if errors:
        print(f"Assessment file '{assessment_path}' has {len(errors)} validation error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    gaps = compute_subcategory_gaps(reference, assessment)
    category_coverage = compute_category_coverage(reference, assessment)
    function_coverage = compute_function_coverage(reference, assessment)

    _print_summary(reference, assessment, gaps, category_coverage, function_coverage)

    report = generate_markdown_report(reference, gaps, category_coverage, function_coverage)
    write_report(report, args.output)
    print(f"\nFull report written to {args.output}")

    if args.heatmap:
        heatmap_html = generate_html_heatmap(reference, assessment)
        write_report(heatmap_html, args.heatmap)
        print(f"Heatmap written to {args.heatmap}")


if __name__ == "__main__":
    main()