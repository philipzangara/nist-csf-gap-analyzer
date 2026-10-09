"""
Loads the NIST CSF 2.0 reference structure from data/csf_2_0_reference.yaml.

Design choice: plain nested dicts, not dataclasses.
The YAML is already shaped exactly as Function -> Category -> Subcategory,
so a dict load is a 1:1 mapping with zero translation logic. Dataclasses
would add type safety but also add a class per level (Function, Category,
Subcategory) plus conversion code, for a schema that never changes shape
at runtime. If this project later needs computed properties (e.g. a
Category object exposing its own coverage %), that's the point to
reconsider dataclasses — not before.
"""

from pathlib import Path

import yaml


def load_csf_reference(path: str | Path) -> dict:
    """
    Load the CSF 2.0 reference YAML into memory.

    Raises FileNotFoundError if the path doesn't exist, and
    yaml.YAMLError if the file is malformed — both are allowed to
    propagate rather than being caught here. A broken reference file
    means the tool can't do anything meaningful, so failing loudly and
    immediately (with Python's normal traceback) is more useful than
    limping along or hiding the problem behind a custom exception.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        reference = yaml.safe_load(f)

    if not reference:
        raise ValueError(f"{path} loaded but is empty")

    return reference


def get_all_subcategory_ids(reference: dict) -> set[str]:
    """
    Return every Subcategory ID in the reference (e.g. {"GV.OC-01", ...}).

    Used by assessment.py to validate that every ID in a user's
    assessment file actually exists in the framework — catches typos
    like "GV.OC-1" instead of "GV.OC-01" before they silently produce
    a wrong gap report.
    """
    ids: set[str] = set()
    for function in reference.values():
        for category in function["categories"].values():
            ids.update(category["subcategories"].keys())
    return ids


def get_category_for_subcategory(reference: dict, subcategory_id: str) -> str:
    """
    Return the Category ID that owns the given Subcategory ID.

    Raises KeyError if the subcategory doesn't exist in the reference —
    callers should validate against get_all_subcategory_ids() first if
    they want to handle unknown IDs gracefully instead of hitting this.
    """
    for function in reference.values():
        for category_id, category in function["categories"].items():
            if subcategory_id in category["subcategories"]:
                return category_id
    raise KeyError(f"Subcategory '{subcategory_id}' not found in reference")
