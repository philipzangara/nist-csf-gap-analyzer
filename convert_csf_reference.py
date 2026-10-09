"""
One-off conversion script (not part of the hand-coded project logic).

Converts the raw NIST CPRT export (data/csf_2_0_raw.json) into this
project's csf_2_0_reference.yaml schema (Function -> Category -> Subcategory).

WHY THIS SHAPE: I inspected the actual downloaded file before writing this
(not guessing from memory). Key findings:

- Top-level shape: {"response": {"elements": {"elements": [...], "relationships": [...]}}}
- "elements" is a FLAT list of dicts, each with "element_type" one of:
  function, category, subcategory, implementation_example, party, sort,
  withdraw_reason.
- Each function/category/subcategory element has: element_identifier,
  title, text, doc_identifier (all "CSF_2_0_0" here — this export bundles
  the CSF 2.0 Core alongside withdrawn CSF 1.1 elements in ONE list).
- The file has 34 "category" elements and 185 "subcategory" elements —
  more than the real CSF 2.0 counts (22 categories, 106 subcategories).
  The extras are WITHDRAWN CSF 1.1 items included for historical mapping.
- How withdrawn items are marked: there's a separate "withdraw_reason"
  element type, with element_identifier "WR-<old_id>" (e.g. "WR-DE.DP-05").
  Any category/subcategory whose identifier appears (stripped of "WR-")
  in the withdraw_reason list is a WITHDRAWN 1.1 item, not part of the
  real CSF 2.0 Core. Filtering these out gives exactly 22 categories and
  106 subcategories, which matches published CSF 2.0 counts.
- Hierarchy is NOT given via a separate relationship — it's encoded in the
  identifiers themselves: a category id's prefix before "." is its
  Function (e.g. "GV.OC" -> Function "GV"); a subcategory id's prefix
  before "-" is its Category (e.g. "GV.OC-01" -> Category "GV.OC").

Run:
    python3 convert_csf_reference.py
Reads:  data/csf_2_0_raw.json   (download this yourself from CPRT first)
Writes: data/csf_2_0_reference.yaml
"""

import json
import yaml
from pathlib import Path

RAW_PATH = Path("data/csf_2_0_raw.json")
OUT_PATH = Path("data/csf_2_0_reference.yaml")


def load_raw(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["response"]["elements"]["elements"]


def get_withdrawn_ids(elements: list[dict]) -> set[str]:
    """IDs (with the 'WR-' prefix stripped) that are withdrawn CSF 1.1 items."""
    return {
        e["element_identifier"][len("WR-"):]
        for e in elements
        if e.get("element_type") == "withdraw_reason"
    }


def build_reference(elements: list[dict]) -> dict:
    withdrawn = get_withdrawn_ids(elements)

    functions = {
        e["element_identifier"]: {"name": e["title"], "categories": {}}
        for e in elements
        if e.get("element_type") == "function"
    }

    categories = [
        e for e in elements
        if e.get("element_type") == "category"
        and e["element_identifier"] not in withdrawn
    ]
    for cat in categories:
        cat_id = cat["element_identifier"]
        func_id = cat_id.split(".")[0]
        functions[func_id]["categories"][cat_id] = {
            "name": cat["title"],
            "subcategories": {},
        }

    subcategories = [
        e for e in elements
        if e.get("element_type") == "subcategory"
        and e["element_identifier"] not in withdrawn
    ]
    for sub in subcategories:
        sub_id = sub["element_identifier"]
        cat_id = sub_id.split("-")[0]
        func_id = cat_id.split(".")[0]
        # Subcategory "title" is usually empty in this export; "text" holds
        # the actual outcome description.
        functions[func_id]["categories"][cat_id]["subcategories"][sub_id] = {
            "description": sub["text"],
        }

    return functions


def main() -> None:
    elements = load_raw(RAW_PATH)
    reference = build_reference(elements)

    with open(OUT_PATH, "w") as f:
        yaml.dump(reference, f, sort_keys=False, allow_unicode=True, width=100)

    # Quick sanity counts so you can eyeball it matches published totals
    # (22 categories, 106 subcategories for CSF 2.0).
    num_categories = sum(len(fn["categories"]) for fn in reference.values())
    num_subcategories = sum(
        len(cat["subcategories"])
        for fn in reference.values()
        for cat in fn["categories"].values()
    )
    print(f"Functions: {len(reference)}")
    print(f"Categories: {num_categories}")
    print(f"Subcategories: {num_subcategories}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
