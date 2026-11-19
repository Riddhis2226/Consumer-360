"""Raw ingestion and source-data validation for Online Retail II."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
REPORT_DIR = PROJECT_ROOT / "reports"

SOURCE_FILES = [
    "online_retail_II_2009-10.csv",
    "online_retail_II_2010-11.csv",
]

REQUIRED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]

STRING_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Customer ID",
    "Country",
]

DATE_FORMAT = "%d-%m-%y %H:%M"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def read_source_file(path: Path) -> tuple[pd.DataFrame, str]:
    """Read a source CSV while preserving identifier columns as strings."""
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    dtype_map = {column: "string" for column in STRING_COLUMNS}
    last_error: UnicodeDecodeError | None = None

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            dataframe = pd.read_csv(
                path,
                encoding=encoding,
                dtype=dtype_map,
                low_memory=False,
            )
            return dataframe, encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(
        f"Could not decode {path.name} using supported encodings."
    ) from last_error


def validate_schema(dataframe: pd.DataFrame, filename: str) -> None:
    """Raise an error if required source columns are missing."""
    missing_columns = sorted(
        set(REQUIRED_COLUMNS) - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{filename} is missing required columns: {missing_columns}"
        )

    logger.info("Schema validation passed: %s", filename)


def profile_source(
    dataframe: pd.DataFrame,
    path: Path,
    encoding: str,
) -> dict[str, Any]:
    """Calculate source-data quality statistics without modifying the data."""
    validate_schema(dataframe, path.name)

    quantity = pd.to_numeric(dataframe["Quantity"], errors="coerce")
    price = pd.to_numeric(dataframe["Price"], errors="coerce")

    invoice_dates = pd.to_datetime(
        dataframe["InvoiceDate"],
        format=DATE_FORMAT,
        errors="coerce",
    )

    invoice_values = dataframe["Invoice"].astype("string")

    return {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "encoding": encoding,
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "columns": list(dataframe.columns),
        "missing_values": {
            column: int(count)
            for column, count in dataframe.isna().sum().items()
        },
        "exact_duplicate_rows": int(dataframe.duplicated().sum()),
        "invalid_quantity_values": int(
            (quantity.isna() & dataframe["Quantity"].notna()).sum()
        ),
        "invalid_price_values": int(
            (price.isna() & dataframe["Price"].notna()).sum()
        ),
        "invalid_invoice_dates": int(
            (
                invoice_dates.isna()
                & dataframe["InvoiceDate"].notna()
            ).sum()
        ),
        "negative_quantity_rows": int((quantity < 0).sum()),
        "zero_quantity_rows": int((quantity == 0).sum()),
        "negative_price_rows": int((price < 0).sum()),
        "zero_price_rows": int((price == 0).sum()),
        "cancellation_invoice_rows": int(
            invoice_values.str.startswith("C", na=False).sum()
        ),
        "distinct_invoice_count": int(
            dataframe["Invoice"].nunique(dropna=True)
        ),
        "distinct_stock_code_count": int(
            dataframe["StockCode"].nunique(dropna=True)
        ),
        "distinct_customer_count": int(
            dataframe["Customer ID"].nunique(dropna=True)
        ),
        "date_min": (
            invoice_dates.min().isoformat()
            if invoice_dates.notna().any()
            else None
        ),
        "date_max": (
            invoice_dates.max().isoformat()
            if invoice_dates.notna().any()
            else None
        ),
    }


def run_ingestion() -> dict[str, Any]:
    """Inspect all configured source files and write an ingestion report."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    file_reports: list[dict[str, Any]] = []

    for filename in SOURCE_FILES:
        source_path = RAW_DATA_DIR / filename
        logger.info("Reading source file: %s", filename)

        dataframe, encoding = read_source_file(source_path)
        file_report = profile_source(dataframe, source_path, encoding)

        file_reports.append(file_report)
        logger.info(
            "Completed %s: %s rows",
            filename,
            file_report["row_count"],
        )

        del dataframe

    report: dict[str, Any] = {
        "project": "Consumer360",
        "process": "raw_source_ingestion",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_directory": str(RAW_DATA_DIR),
        "source_files_processed": len(file_reports),
        "total_rows": sum(item["row_count"] for item in file_reports),
        "files": file_reports,
        "source_files_modified": False,
    }

    report_path = REPORT_DIR / "ingestion_report.json"
    temporary_path = report_path.with_suffix(".json.tmp")

    temporary_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(report_path)

    logger.info("Ingestion report saved: %s", report_path)

    return report


def main() -> None:
    """Run raw ingestion from the command line."""
    report = run_ingestion()

    print("\nConsumer360 raw ingestion completed.")
    print(f"Files processed: {report['source_files_processed']}")
    print(f"Total rows inspected: {report['total_rows']:,}")
    print(f"Report: {REPORT_DIR / 'ingestion_report.json'}")


if __name__ == "__main__":
    main()
