"""
Loads and validates a user's self-assessment file against the CSF reference.

Design decisions locked in here (matching assessments/example_assessment.yaml):
- Valid "status" values: "implemented", "partial", "not_implemented".
- A subcategory ID in the reference but MISSING from the assessment file
  is NOT handled here — that's gap_engine.py's job (it will treat a
  missing entry as equivalent to not_implemented when it computes
  coverage). assessment.py only validates what IS present; it doesn't
  fill in gaps, so the raw loaded dict always reflects exactly what the
  user wrote.
"""

from pathlib import Path

import yaml

VALID_STATUSES = {"implemented", "partial", "not_implemented"}


def load_assessment(path: str | Path) -> dict:
    """
    Load a self-assessment YAML file into memory.

    Same failure philosophy as csf_loader.load_csf_reference: file-not-found
    and malformed-YAML errors propagate as-is rather than being wrapped,
    because there's nothing useful this function can do to recover from
    either case.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        assessment = yaml.safe_load(f)

    if not assessment:
        raise ValueError(f"{path} loaded but is empty")

    return assessment


def validate_assessment(assessment: dict, known_subcategory_ids: set[str]) -> list[str]:
    """
    Check an assessment dict against the known subcategory IDs from the
    CSF reference (get_all_subcategory_ids() in csf_loader.py) and each
    entry's own required fields.

    Returns a list of human-readable error strings — empty list means the
    assessment is valid. Deliberately returns a list rather than raising
    on the first problem: for a file with, say, 20 subcategories, you want
    to see every typo and missing field in one pass, not fix one, rerun,
    find the next.
    """
    errors: list[str] = []

    for subcategory_id, entry in assessment.items():
        if subcategory_id not in known_subcategory_ids:
            errors.append(
                f"'{subcategory_id}' is not a recognized CSF 2.0 subcategory ID"
            )
            continue  # no point validating fields of an entry we don't recognize

        if not isinstance(entry, dict):
            errors.append(
                f"'{subcategory_id}': expected a mapping with a 'status' field, "
                f"got {type(entry).__name__}"
            )
            continue

        status = entry.get("status")
        if status is None:
            errors.append(f"'{subcategory_id}': missing required 'status' field")
        elif status not in VALID_STATUSES:
            errors.append(
                f"'{subcategory_id}': status '{status}' is not one of "
                f"{sorted(VALID_STATUSES)}"
            )

    return errors