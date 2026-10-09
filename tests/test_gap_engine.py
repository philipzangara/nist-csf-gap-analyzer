"""
Unit tests for gap_engine.py.

Uses a small hand-built fixture (2 Functions, 3 Categories, 6 Subcategories)
rather than the real 106-subcategory CSF 2.0 reference — per the original
stub's own guidance, small fixture data is easier to hand-verify and keeps
tests fast. All expected values below are computed by hand in the test
comments, not derived from running the code and copying its output.

Fixture shape:
    FN1
      FN1.CA: FN1.CA-01, FN1.CA-02
      FN1.CB: FN1.CB-01
    FN2
      FN2.CA: FN2.CA-01, FN2.CA-02, FN2.CA-03

Run with: pytest tests/test_gap_engine.py -v
(run from the project root so the `src` package resolves)
"""

import pytest

from src.gap_engine import (
    compute_subcategory_gaps,
    compute_category_coverage,
    compute_function_coverage,
)


@pytest.fixture
def reference():
    return {
        "FN1": {
            "name": "Function One",
            "categories": {
                "FN1.CA": {
                    "name": "Category A",
                    "subcategories": {
                        "FN1.CA-01": {"description": "desc"},
                        "FN1.CA-02": {"description": "desc"},
                    },
                },
                "FN1.CB": {
                    "name": "Category B",
                    "subcategories": {
                        "FN1.CB-01": {"description": "desc"},
                    },
                },
            },
        },
        "FN2": {
            "name": "Function Two",
            "categories": {
                "FN2.CA": {
                    "name": "Category A2",
                    "subcategories": {
                        "FN2.CA-01": {"description": "desc"},
                        "FN2.CA-02": {"description": "desc"},
                        "FN2.CA-03": {"description": "desc"},
                    },
                },
            },
        },
    }


def test_all_implemented_gives_full_coverage(reference):
    # Every one of the 6 subcategories marked implemented -> 100% everywhere,
    # zero partial, zero gaps.
    assessment = {
        "FN1.CA-01": {"status": "implemented"},
        "FN1.CA-02": {"status": "implemented"},
        "FN1.CB-01": {"status": "implemented"},
        "FN2.CA-01": {"status": "implemented"},
        "FN2.CA-02": {"status": "implemented"},
        "FN2.CA-03": {"status": "implemented"},
    }

    gaps = compute_subcategory_gaps(reference, assessment)
    category_coverage = compute_category_coverage(reference, assessment)
    function_coverage = compute_function_coverage(reference, assessment)

    assert gaps == []
    assert category_coverage["FN1.CA"] == {
        "coverage_percent": 100.0, "implemented": 2, "partial": 0, "total": 2,
    }
    assert category_coverage["FN1.CB"] == {
        "coverage_percent": 100.0, "implemented": 1, "partial": 0, "total": 1,
    }
    assert category_coverage["FN2.CA"] == {
        "coverage_percent": 100.0, "implemented": 3, "partial": 0, "total": 3,
    }
    assert function_coverage["FN1"] == {
        "coverage_percent": 100.0, "implemented": 3, "partial": 0, "total": 3,
    }
    assert function_coverage["FN2"] == {
        "coverage_percent": 100.0, "implemented": 3, "partial": 0, "total": 3,
    }


def test_mixed_statuses_match_scoring_model(reference):
    # FN1.CA: 1 implemented, 1 partial -> 1/2 = 50.0%
    # FN1.CB: 1 not_implemented -> 0/1 = 0.0%
    # FN2.CA: 1 implemented, 1 partial, 1 MISSING (not in assessment at all)
    #         -> 1/3 = 33.3% (missing counts as not_implemented, not as a gap
    #            in the numerator, per the locked default)
    # FN1 (CA+CB combined): implemented=1+0=1, partial=1+0=1, total=2+1=3
    #         -> 1/3 = 33.3%
    # FN2: implemented=1, partial=1, total=3 -> 33.3%
    assessment = {
        "FN1.CA-01": {"status": "implemented"},
        "FN1.CA-02": {"status": "partial"},
        "FN1.CB-01": {"status": "not_implemented"},
        "FN2.CA-01": {"status": "implemented"},
        "FN2.CA-02": {"status": "partial"},
        # FN2.CA-03 deliberately omitted entirely
    }

    gaps = compute_subcategory_gaps(reference, assessment)
    category_coverage = compute_category_coverage(reference, assessment)
    function_coverage = compute_function_coverage(reference, assessment)

    assert category_coverage["FN1.CA"] == {
        "coverage_percent": 50.0, "implemented": 1, "partial": 1, "total": 2,
    }
    assert category_coverage["FN1.CB"] == {
        "coverage_percent": 0.0, "implemented": 0, "partial": 0, "total": 1,
    }
    assert category_coverage["FN2.CA"] == {
        "coverage_percent": 33.3, "implemented": 1, "partial": 1, "total": 3,
    }
    assert function_coverage["FN1"] == {
        "coverage_percent": 33.3, "implemented": 1, "partial": 1, "total": 3,
    }
    assert function_coverage["FN2"] == {
        "coverage_percent": 33.3, "implemented": 1, "partial": 1, "total": 3,
    }

    # 4 gaps expected: FN1.CA-02 (partial), FN1.CB-01 (not_implemented),
    # FN2.CA-02 (partial), FN2.CA-03 (missing -> reported as not_implemented)
    gap_ids = {g["subcategory_id"]: g["status"] for g in gaps}
    assert gap_ids == {
        "FN1.CA-02": "partial",
        "FN1.CB-01": "not_implemented",
        "FN2.CA-02": "partial",
        "FN2.CA-03": "not_implemented",
    }


def test_missing_subcategory_treated_as_not_implemented(reference):
    # A subcategory entirely absent from the assessment must be reported
    # as a gap with status "not_implemented" -- never as a separate
    # "missing" state, and never silently dropped from the gap list.
    assessment = {
        "FN1.CA-01": {"status": "implemented"},
        # every other subcategory is absent from this assessment
    }

    gaps = compute_subcategory_gaps(reference, assessment)
    gap_ids = {g["subcategory_id"]: g["status"] for g in gaps}

    assert "FN1.CA-02" in gap_ids
    assert gap_ids["FN1.CA-02"] == "not_implemented"
    assert "FN2.CA-03" in gap_ids
    assert gap_ids["FN2.CA-03"] == "not_implemented"
    # 5 of the 6 subcategories are gaps; only FN1.CA-01 is implemented
    assert len(gaps) == 5


def test_empty_assessment_gives_zero_coverage_no_crash(reference):
    assessment = {}

    gaps = compute_subcategory_gaps(reference, assessment)
    category_coverage = compute_category_coverage(reference, assessment)
    function_coverage = compute_function_coverage(reference, assessment)

    assert len(gaps) == 6  # every subcategory in the fixture is a gap
    assert all(g["status"] == "not_implemented" for g in gaps)

    for stats in category_coverage.values():
        assert stats["coverage_percent"] == 0.0
        assert stats["implemented"] == 0

    for stats in function_coverage.values():
        assert stats["coverage_percent"] == 0.0
        assert stats["implemented"] == 0