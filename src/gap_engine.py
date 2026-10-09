"""
Core logic: cross-references the assessment against the CSF reference and
computes coverage/gaps at the Subcategory, Category, and Function level.

Locked-in design decisions (from README + prior discussion):
- Coverage % is BINARY per subcategory: "implemented" = 1, everything else
  (partial, not_implemented, or missing from the assessment entirely) = 0.
  "Partial" does NOT get fractional credit toward the percentage — it's
  tracked as its own separate count instead, so a report can say
  "40% implemented, 6 partial" rather than blending partial into a
  misleading combined score.
- A subcategory missing from the assessment file is treated identically
  to "not_implemented" (decided when building assessment.py).
- Category coverage = average of its subcategories' binary scores.
- Function coverage = average of ALL its subcategories' binary scores
  directly (not an average of its categories' percentages). This matters
  when a Function's categories have different subcategory counts — this
  approach weights every subcategory equally rather than weighting every
  category equally.
"""


def _is_implemented(assessment: dict, subcategory_id: str) -> bool:
    entry = assessment.get(subcategory_id)
    return bool(entry) and entry.get("status") == "implemented"


def _is_partial(assessment: dict, subcategory_id: str) -> bool:
    entry = assessment.get(subcategory_id)
    return bool(entry) and entry.get("status") == "partial"


def get_subcategory_status(assessment: dict, subcategory_id: str) -> str:
    """
    Return "implemented", "partial", or "not_implemented" for a single
    subcategory. Unlike compute_subcategory_gaps (which only returns
    gaps), this covers every status including "implemented" -- needed
    by anything that wants to render ALL subcategories, not just the
    ones that aren't done yet (e.g. a Navigator-style heatmap).
    """
    if _is_implemented(assessment, subcategory_id):
        return "implemented"
    if _is_partial(assessment, subcategory_id):
        return "partial"
    return "not_implemented"


def compute_subcategory_gaps(reference: dict, assessment: dict) -> list[dict]:
    """
    Return every subcategory that is NOT fully implemented, with its
    Category/Function context attached, so report_generator.py doesn't
    need to re-walk the reference structure to render a gap list.

    "Status" in the returned dicts is always one of "partial" or
    "not_implemented" — a subcategory missing from the assessment file
    is reported as "not_implemented" (per the locked default), not as a
    separate "missing" state, so downstream code has only two gap
    statuses to handle, not three.
    """
    gaps = []
    for function_id, function in reference.items():
        for category_id, category in function["categories"].items():
            for subcategory_id in category["subcategories"]:
                if _is_implemented(assessment, subcategory_id):
                    continue
                status = "partial" if _is_partial(assessment, subcategory_id) else "not_implemented"
                gaps.append({
                    "subcategory_id": subcategory_id,
                    "category_id": category_id,
                    "function_id": function_id,
                    "status": status,
                })
    return gaps


def compute_category_coverage(reference: dict, assessment: dict) -> dict:
    """
    Per-Category stats: {category_id: {"coverage_percent", "implemented",
    "partial", "total"}}.

    coverage_percent is implemented-count / total-count * 100 — partial
    subcategories count toward "total" (the denominator) but not toward
    "implemented" (the numerator), which is what makes partial visible
    as its own number instead of quietly inflating the percentage.
    """
    coverage = {}
    for function in reference.values():
        for category_id, category in function["categories"].items():
            subcategory_ids = list(category["subcategories"])
            total = len(subcategory_ids)
            implemented = sum(_is_implemented(assessment, sid) for sid in subcategory_ids)
            partial = sum(_is_partial(assessment, sid) for sid in subcategory_ids)
            coverage[category_id] = {
                "coverage_percent": round((implemented / total) * 100, 1) if total else 0.0,
                "implemented": implemented,
                "partial": partial,
                "total": total,
            }
    return coverage


def compute_function_coverage(reference: dict, assessment: dict) -> dict:
    """
    Per-Function stats, same shape as compute_category_coverage but rolled
    up one level. Computed directly from all subcategories in the Function
    (not by averaging the Function's category percentages) — see the
    module docstring for why that distinction matters.
    """
    coverage = {}
    for function_id, function in reference.items():
        subcategory_ids = [
            sid
            for category in function["categories"].values()
            for sid in category["subcategories"]
        ]
        total = len(subcategory_ids)
        implemented = sum(_is_implemented(assessment, sid) for sid in subcategory_ids)
        partial = sum(_is_partial(assessment, sid) for sid in subcategory_ids)
        coverage[function_id] = {
            "coverage_percent": round((implemented / total) * 100, 1) if total else 0.0,
            "implemented": implemented,
            "partial": partial,
            "total": total,
        }
    return coverage