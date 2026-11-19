"""Overlap-aware ingestion into the PostgreSQL staging layer."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from consumer360.database.connection import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

SOURCE_FILES = [
    "online_retail_II_2009-10.csv",
    "online_retail_II_2010-11.csv",
]

COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]

DTYPE_MAP = {
    "Invoice": "string",
    "StockCode": "string",
    "Description": "string",
    "Customer ID": "string",
    "Country": "string",
}

DATE_FORMAT = "%d-%m-%y %H:%M"
CHUNK_SIZE = 2000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def read_source(path: Path) -> pd.DataFrame:
    """Read a source file, handling UTF-8 BOM and Windows-1252."""
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    last_error = None

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            frame = pd.read_csv(
                path,
                encoding=encoding,
                dtype=DTYPE_MAP,
                low_memory=False,
            )
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError(
            f"Unable to decode {path.name}"
        ) from last_error

    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing columns: {sorted(missing)}"
        )

    frame = frame[COLUMNS].copy()

    # Preserve the original CSV line number, including the header offset.
    frame["source_row_number"] = range(2, len(frame) + 2)

    return frame


def reconcile_cross_file_overlap(
    first: pd.DataFrame,
    second: pd.DataFrame,
) -> tuple[pd.Series, int]:
    """Return a mask retaining second-file rows not present in the first.

    Matching is performed on all source columns using pandas' exact
    MultiIndex equality semantics. This avoids treating a fingerprint
    collision as proof that two source rows are identical. Multiplicity
    must match for every shared row; within-file duplicates are preserved.
    """
    first_counts = first[COLUMNS].value_counts(dropna=False, sort=False)
    second_counts = second[COLUMNS].value_counts(dropna=False, sort=False)
    shared = first_counts.index.intersection(second_counts.index)

    if len(shared):
        left_counts = first_counts.reindex(shared).to_numpy()
        right_counts = second_counts.reindex(shared).to_numpy()
        mismatched = int((left_counts != right_counts).sum())
        if mismatched:
            raise ValueError(
                f"Overlap multiplicity changed: {mismatched} shared "
                "source rows have different counts. No records were loaded."
            )

    # pandas merge uses null-safe key matching and preserves left row order.
    # Carry an explicit position so the mask is aligned to the source frame.
    second_keys = second[COLUMNS].copy()
    second_keys["_row_position"] = range(len(second_keys))
    matches = second_keys.merge(
        first[COLUMNS].drop_duplicates(),
        on=COLUMNS,
        how="left",
        indicator=True,
        sort=False,
    )
    keep_second = (
        matches.sort_values("_row_position")["_merge"]
        .eq("left_only")
        .to_numpy()
    )
    overlap_rows = int((~keep_second).sum())
    return pd.Series(keep_second, index=second.index), overlap_rows


def prepare_for_database(
    frame: pd.DataFrame,
    source_file: str,
) -> pd.DataFrame:
    """Map source columns to staging columns and create quality flags."""
    result = pd.DataFrame(index=frame.index)

    result["invoice"] = frame["Invoice"]
    result["stock_code"] = frame["StockCode"]
    result["description"] = frame["Description"]

    result["quantity"] = pd.to_numeric(
        frame["Quantity"], errors="raise"
    ).astype("int64")

    result["invoice_date"] = pd.to_datetime(
        frame["InvoiceDate"],
        format=DATE_FORMAT,
        errors="raise",
    )

    result["unit_price"] = pd.to_numeric(
        frame["Price"], errors="raise"
    ).round(4)

    result["customer_id"] = frame["Customer ID"]
    result["country"] = frame["Country"]

    result["source_file"] = source_file
    result["source_row_number"] = frame["source_row_number"]

    result["is_cancellation"] = (
        result["invoice"].str.startswith("C", na=False)
    )

    result["is_return_candidate"] = result["quantity"] < 0
    result["has_missing_customer"] = result["customer_id"].isna()
    result["has_missing_description"] = result["description"].isna()
    result["has_zero_price"] = result["unit_price"] == 0
    result["has_negative_price"] = result["unit_price"] < 0

    return result


def run_staging_load() -> None:
    """Load both source files while excluding verified cross-file overlap."""

    logger.info("Reading first source file.")
    first = read_source(RAW_DIR / SOURCE_FILES[0])

    logger.info("Reading second source file.")
    second = read_source(RAW_DIR / SOURCE_FILES[1])

    # Keep all first-file rows and remove only exact cross-file matches.
    second_keep, overlap_rows = reconcile_cross_file_overlap(first, second)
    second_clean = second.loc[second_keep].copy()

    first_prepared = prepare_for_database(
        first, SOURCE_FILES[0]
    )
    second_prepared = prepare_for_database(
        second_clean, SOURCE_FILES[1]
    )

    final_data = pd.concat(
        [first_prepared, second_prepared],
        ignore_index=True,
    )

    expected_rows = len(first) + len(second) - overlap_rows

    if len(final_data) != expected_rows:
        raise AssertionError("Unexpected final row count.")

    engine = get_engine()

    try:
        with engine.begin() as connection:
            existing_count = connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM staging.retail_transactions"
                )
            ).scalar_one()

            if existing_count != 0:
                raise RuntimeError(
                    f"Staging table already contains {existing_count} "
                    "rows. Refusing to append duplicate data."
                )

            final_data.to_sql(
                name="retail_transactions",
                schema="staging",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=CHUNK_SIZE,
                method="multi",
            )

            loaded_count = connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM staging.retail_transactions"
                )
            ).scalar_one()

            if loaded_count != expected_rows:
                raise AssertionError(
                    f"Expected {expected_rows} rows, "
                    f"but found {loaded_count}."
                )

    finally:
        engine.dispose()

    logger.info("Staging load completed successfully.")
    print("\nCONSUMER360 STAGING LOAD")
    print("-----------------------")
    print(f"First source rows:       {len(first):,}")
    print(f"Second source rows:      {len(second):,}")
    print(f"Cross-file overlap:      {overlap_rows:,}")
    print(f"Excluded second rows:    {overlap_rows:,}")
    print(f"Expected staging rows:   {expected_rows:,}")
    print(f"Actual staging rows:     {loaded_count:,}")


if __name__ == "__main__":
    run_staging_load()
