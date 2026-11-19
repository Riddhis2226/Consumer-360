"""Command-line entry point for Consumer360 operational tasks."""

from __future__ import annotations

import argparse


def main() -> None:
    """Run an explicitly selected Consumer360 operation."""
    parser = argparse.ArgumentParser(prog="consumer360")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "profile",
        help="Profile the configured raw Online Retail II source files.",
    )
    subparsers.add_parser(
        "stage",
        help="Load reconciled source rows into PostgreSQL staging.",
    )
    subparsers.add_parser(
        "test-connection",
        help="Test the configured PostgreSQL connection.",
    )

    args = parser.parse_args()

    if args.command == "profile":
        from consumer360.ingestion.retail_loader import main as run_profile

        run_profile()
    elif args.command == "stage":
        from consumer360.ingestion.staging_loader import run_staging_load

        run_staging_load()
    elif args.command == "test-connection":
        from consumer360.database.connection import test_connection

        test_connection()


if __name__ == "__main__":
    main()
