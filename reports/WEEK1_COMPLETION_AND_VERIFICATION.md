# Week 1 Completion and Verification Record

**Project:** Consumer360 — Retail Customer Behavior & RFM Analysis  
**Scope:** Week 1 — Data Engineering & Schema  
**Repository:** `Riddhis2226/Consumer-360`  
**Verification branch:** `fix/week-1-quality-and-reproducibility`

## Completion summary

The Week 1 implementation is complete in the repository. The original source data and the current database audit record reconcile to the expected row counts. Repository defects found during review have been corrected, and automated quality gates pass.

## Source-data reconciliation

The two supplied source CSV files were re-read and reconciled using all eight source columns with null-safe row equality.

| Check | Result |
|---|---:|
| 2009–10 source rows | 525,461 |
| 2010–11 source rows | 541,910 |
| Distinct shared source rows | 22,202 |
| Cross-file overlap occurrences | 22,523 |
| Shared-row multiplicity mismatches | 0 |
| Rows retained from second file | 519,387 |
| Final staged row expectation | 1,044,848 |
| Within-file duplicates in 2009–10 | 6,865 (preserved) |
| Within-file duplicates in 2010–11 | 5,268 (preserved) |

The reconciliation logic now verifies exact values across every source field and separately verifies occurrence multiplicity. It does not rely on a row hash as proof of equality.

## PostgreSQL data-foundation evidence

The previously recorded live PostgreSQL audit reported:

| Object / check | Recorded result |
|---|---:|
| `staging.retail_transactions` | 1,044,848 rows |
| `analytics.cleaned_transactions_v2` | 1,044,848 rows |
| `analytics.dim_customer` | 5,943 rows, including unknown member |
| `analytics.dim_product` | 5,305 rows, including unknown member |
| `analytics.fact_sales` | 1,044,848 rows |
| `analytics.vw_single_customer` | 5,942 identified customers |
| Customers with merchandise orders | 5,852 |
| Customers without merchandise orders | 90 |
| SCV merchandise revenue | £17,117,089.2970 |
| Fact/dimension orphan checks | 0 |
| Fact staging-key uniqueness | Passed |

These are recorded database results from the project audit, not a new connection to the developer's local PostgreSQL instance during this repository repair.

## Repository corrections

- Removed all Git merge-conflict markers from the Week 1 notebook and validated its JSON structure.
- Cleared stale notebook outputs so the audit must be re-executed to produce current results.
- Aligned notebook invoice-date parsing with the ingestion loader's explicit `%d-%m-%y %H:%M` format.
- Replaced hash-only overlap filtering with null-safe exact matching and multiplicity validation.
- Added unit tests for exact overlap, duplicate preservation, null values, multiplicity mismatch, and distinct rows.
- Added the missing `consumer360.cli` module required by the existing project script entry point.
- Removed the unused `consumer_360` package stub so `consumer360` is the single canonical package.
- Added schema creation to migration 001 so a fresh database can apply the migration sequence.
- Updated the README with setup, migration order, validation, and data interpretation rules.
- Added GitHub Actions checks for Python tests, lint, notebook integrity, and PostgreSQL migration smoke tests.
- Confirmed `.env.example` uses `DB_SCHEMA=analytics`.

## Automated verification

GitHub Actions on the repair branch completed successfully:

- Python dependency installation: passed
- Week 1 notebook JSON and code-cell compilation: passed
- Unit tests: passed
- Ruff lint: passed
- PostgreSQL 18 fresh-database migrations 001–005: passed
- Required staging, classification, dimension, fact, and Single Customer View objects: passed

The CI migration test starts from an empty database. It verifies that the SQL architecture can be installed cleanly; it does not repopulate the developer's production dataset.

## Performance evidence

The project audit records these historical `EXPLAIN ANALYZE` results:

| Query | Historical execution time | Target |
|---|---:|---:|
| Single customer lookup (18102) | 1,045.764 ms | under 2,000 ms |
| Top 10 customers by merchandise revenue | 1,544.473 ms | under 2,000 ms |
| Country-level merchandise revenue | 1,891.806 ms | under 2,000 ms |

These are historical measurements. Re-run `database/queries/006_performance_benchmark.sql` against the current populated local database when recording a fresh machine-specific performance baseline.

## Final status

**Week 1 implementation: complete.**  
**Repository quality gates: passing.**  
**Fresh populated-local-database benchmark: environment-dependent recheck recommended.**

No Week 2 analytical work is included in this completion record.
