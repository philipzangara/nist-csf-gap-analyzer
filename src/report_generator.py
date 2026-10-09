"""
Renders gap_engine output into a human-readable Markdown report.

Deviation from the original stub signature: generate_markdown_report()
also takes `reference`, which the stub didn't include. Without it, the
report can only show raw IDs ("GV.RM-01") with no Function/Category names
or subcategory descriptions — not readable to anyone who doesn't have the
CSF spec memorized. The reference dict is cheap to load and pass through,
so this earns its place.
"""

from pathlib import Path


def _get_subcategory_description(reference: dict, function_id: str, category_id: str, subcategory_id: str) -> str:
    return reference[function_id]["categories"][category_id]["subcategories"][subcategory_id]["description"]


def generate_markdown_report(
    reference: dict,
    gaps: list[dict],
    category_coverage: dict,
    function_coverage: dict,
) -> str:
    """
    Build the full Markdown report as a single string.

    Sections, in order:
    1. Executive summary — overall % implemented across the whole framework.
    2. Per-Function breakdown — coverage % and partial count per Function.
    3. Quick wins — partial subcategories, since these are the closest to
       done and usually the best next action for a small team.
    4. Full gap table — every not-fully-implemented subcategory, grouped
       by Function/Category, with its description so the reader doesn't
       need the CSF spec open in another tab.
    """
    total_subs = sum(
        len(category["subcategories"])
        for function in reference.values()
        for category in function["categories"].values()
    )
    total_implemented = total_subs - len(gaps)
    overall_pct = round((total_implemented / total_subs) * 100, 1) if total_subs else 0.0

    lines: list[str] = []

    # --- 1. Executive summary ---
    lines.append("# NIST CSF 2.0 Gap Analysis Report")
    lines.append("")
    lines.append(
        f"**Overall coverage: {overall_pct}%** "
        f"({total_implemented} of {total_subs} subcategories fully implemented)"
    )
    lines.append("")

    # --- 2. Per-Function breakdown ---
    lines.append("## Function Coverage")
    lines.append("")
    lines.append("| Function | Coverage | Implemented | Partial | Total |")
    lines.append("|---|---|---|---|---|")
    for function_id, function in reference.items():
        stats = function_coverage[function_id]
        lines.append(
            f"| {function_id} ({function['name']}) | {stats['coverage_percent']}% "
            f"| {stats['implemented']} | {stats['partial']} | {stats['total']} |"
        )
    lines.append("")

    # --- 3. Quick wins (partial subcategories) ---
    quick_wins = [g for g in gaps if g["status"] == "partial"]
    lines.append(f"## Quick Wins ({len(quick_wins)} partially implemented)")
    lines.append("")
    if quick_wins:
        lines.append(
            "These are already partially in place — likely the fastest path to closing a gap."
        )
        lines.append("")
        for gap in quick_wins:
            desc = _get_subcategory_description(
                reference, gap["function_id"], gap["category_id"], gap["subcategory_id"]
            )
            lines.append(f"- **{gap['subcategory_id']}** ({gap['category_id']}): {desc}")
    else:
        lines.append("None — no subcategories are currently marked partial.")
    lines.append("")

    # --- 4. Full gap table, grouped by Function then Category ---
    lines.append(f"## Full Gap List ({len(gaps)} subcategories not fully implemented)")
    lines.append("")
    gaps_by_function: dict[str, list[dict]] = {}
    for gap in gaps:
        gaps_by_function.setdefault(gap["function_id"], []).append(gap)

    for function_id, function in reference.items():
        function_gaps = gaps_by_function.get(function_id, [])
        if not function_gaps:
            continue
        lines.append(f"### {function_id} — {function['name']}")
        lines.append("")
        lines.append("| Subcategory | Category | Status | Description |")
        lines.append("|---|---|---|---|")
        for gap in function_gaps:
            desc = _get_subcategory_description(
                reference, gap["function_id"], gap["category_id"], gap["subcategory_id"]
            )
            lines.append(
                f"| {gap['subcategory_id']} | {gap['category_id']} | {gap['status']} | {desc} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_report(content: str, output_path: str | Path) -> None:
    """
    Write report content to disk, creating parent directories if needed
    (e.g. the gitignored reports/ folder, which won't exist on a fresh
    clone of the repo).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


_STATUS_COLORS = {
    "implemented": "#8ec843",      # Navigator's default gradient: green (high score)
    "partial": "#ffe766",          # Navigator's default gradient: yellow (mid score)
    "not_implemented": "#ff6666",  # Navigator's default gradient: red (low/no score)
}


def generate_html_heatmap(reference: dict, assessment: dict) -> str:
    """
    Render a clickable HTML heatmap matching the real MITRE ATT&CK Navigator
    look: dark navy page, bold white column headers with a grey item-count
    subtitle beneath each, a visible resize-handle-style divider bar between
    columns, and cells rendered as left-aligned rows (not centered boxes)
    like Navigator's actual technique list. Colors are Navigator's real
    default gradient (see _STATUS_COLORS above), pulled from its source
    repo, not approximated.

    Cells link out to csf.tools instead of being non-interactive, per
    earlier discussion -- Navigator's own cells are clickable too, so this
    isn't a deviation from the reference, just pointed at CSF documentation
    instead of ATT&CK's own technique pages.

    Columns are allowed to have different heights (Functions have very
    different Subcategory counts, e.g. GV has 31 vs RC has 8) rather than
    forcing every column to match the tallest one -- same approach
    Navigator itself uses for tactics with different technique counts.
    """
    from src.gap_engine import get_subcategory_status

    BASE_URL = "https://csf.tools/reference/nist-cybersecurity-framework/v2-0"

    column_html_parts = []
    for function_id, function in reference.items():
        cell_html_parts = []
        subcategory_count = sum(
            len(category["subcategories"]) for category in function["categories"].values()
        )
        for category_id, category in function["categories"].items():
            for subcategory_id, subcategory in category["subcategories"].items():
                status = get_subcategory_status(assessment, subcategory_id)
                color = _STATUS_COLORS[status]
                description = subcategory["description"].replace('"', "&quot;")
                function_slug = function_id.lower()
                category_slug = category_id.lower().replace(".", "-")
                subcategory_slug = subcategory_id.lower().replace(".", "-")
                url = f"{BASE_URL}/{function_slug}/{category_slug}/{subcategory_slug}/"
                cell_html_parts.append(
                    f'<a class="cell" href="{url}" target="_blank" rel="noopener" '
                    f'style="background-color: {color};" '
                    f'title="{subcategory_id}: {description}">{subcategory_id}</a>'
                )
        column_html_parts.append(
            f'<div class="column-wrap">'
            f'<div class="column">'
            f'<div class="column-header">{function["name"]}'
            f'<div class="item-count">{subcategory_count} subcategories</div>'
            f'</div>'
            f'<div class="cell-stack">{"".join(cell_html_parts)}</div>'
            f'</div>'
            f'<div class="divider"></div>'
            f'</div>'
        )

    legend_html = "".join(
        f'<div class="legend-item"><span class="legend-swatch" style="background-color: {color};"></span>{status.replace("_", " ")}</div>'
        for status, color in _STATUS_COLORS.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NIST CSF 2.0 Coverage Heatmap</title>
<style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        background-color: #131c2e;
        color: #ffffff;
        margin: 0;
        padding: 20px;
    }}
    .subtitle {{
        color: #8a95a8;
        font-size: 13px;
        margin-bottom: 20px;
    }}
    .board {{
        display: flex;
        align-items: flex-start;
        overflow-x: auto;
    }}
    .column-wrap {{
        display: flex;
        align-items: flex-start;
    }}
    .column {{
        display: flex;
        flex-direction: column;
        width: 150px;
    }}
    .divider {{
        width: 6px;
        align-self: stretch;
        background-color: #2a3549;
        margin: 0 2px;
    }}
    .column-header {{
        color: #ffffff;
        font-weight: 700;
        font-size: 15px;
        padding: 8px 4px 10px 4px;
    }}
    .item-count {{
        font-weight: 400;
        font-size: 11px;
        color: #8a95a8;
        margin-top: 2px;
    }}
    .cell-stack {{
        display: flex;
        flex-direction: column;
    }}
    .cell {{
        display: block;
        font-family: Arial, Helvetica, sans-serif;
        font-size: 11px;
        font-weight: 400;
        color: #000000;
        text-align: left;
        text-decoration: none;
        padding: 6px 8px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.15);
    }}
    .cell:hover {{
        outline: 2px solid #ffffff;
        outline-offset: -2px;
    }}
    .legend {{
        display: flex;
        gap: 20px;
        margin-top: 24px;
        font-size: 12px;
        color: #ffffff;
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .legend-swatch {{
        width: 14px;
        height: 14px;
        display: inline-block;
        border: 1px solid #2a3549;
    }}
</style>
</head>
<body>
    <div class="subtitle">NIST CSF 2.0 Coverage Heatmap. Hover a cell for its full description. Click for more information.</div>
    <div class="board">
        {"".join(column_html_parts)}
    </div>
    <div class="legend">
        {legend_html}
    </div>
</body>
</html>
"""