"""Unit tests for source-row reconciliation."""

import pandas as pd
import pytest

from consumer360.ingestion.staging_loader import (
    COLUMNS,
    reconcile_cross_file_overlap,
)


def frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def test_removes_exact_cross_file_overlap_and_preserves_within_file_duplicates():
    first = frame([
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
    ])
    second = frame([
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
        ["B", "SKU2", "other", 1, "02-01-10", 3.0, "11", "UK"],
        ["B", "SKU2", "other", 1, "02-01-10", 3.0, "11", "UK"],
    ])

    keep, overlap = reconcile_cross_file_overlap(first, second)

    assert overlap == 2
    assert keep.tolist() == [False, False, True, True]
    assert int(keep.sum()) == 2


def test_null_values_match_exactly_across_files():
    first = frame([
        ["A", "SKU1", None, 1, "01-01-10", 2.0, None, "UK"],
    ])
    second = frame([
        ["A", "SKU1", None, 1, "01-01-10", 2.0, None, "UK"],
        ["B", "SKU2", None, 1, "02-01-10", 3.0, None, "UK"],
    ])

    keep, overlap = reconcile_cross_file_overlap(first, second)

    assert overlap == 1
    assert keep.tolist() == [False, True]


def test_shared_row_multiplicity_must_match():
    first = frame([
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
    ])
    second = frame([
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
    ])

    with pytest.raises(ValueError, match="Overlap multiplicity changed"):
        reconcile_cross_file_overlap(first, second)


def test_distinct_rows_are_not_removed():
    first = frame([
        ["A", "SKU1", "item", 1, "01-01-10", 2.0, "10", "UK"],
    ])
    second = frame([
        ["A", "SKU2", "different item", 1, "01-01-10", 2.0, "10", "UK"],
    ])

    keep, overlap = reconcile_cross_file_overlap(first, second)

    assert overlap == 0
    assert keep.tolist() == [True]
