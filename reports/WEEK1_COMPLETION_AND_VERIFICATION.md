# Week 1 Completion and Verification Record

**Project:** Consumer360 — Retail Customer Behavior & RFM Analysis
**Scope:** Week 1 — Data Engineering & Schema
**Repository:** `Riddhis2226/Consumer-360`
**Verification branch:** `main`
**Latest verified repository commit:** `27ce670` — Optimize Single Customer View with materialized metrics

## Completion Summary

The Week 1 data engineering and schema implementation has been completed and validated against the populated PostgreSQL database.

Source-data reconciliation, staging, cleaning, transaction classification, dimensional modelling, fact-table integrity, Single Customer View validation, ER diagram relationships, and SQL performance checks have been verified.

The Single Customer View was optimized using materialized customer metrics. All three benchmark queries execute below the project target of 2,000 milliseconds.

Documentation and ER diagram updates are included in the current local working changes and must be committed separately.

## Source-Data Reconciliation

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

The reconciliation logic verifies exact values across every source field and separately verifies occurrence multiplicity. It does not rely on a row hash as proof of equality.

## PostgreSQL Data-Foundation Evidence

The populated local PostgreSQL database was inspected and validated.

| Object / Check | Result |
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

The Single Customer View contains identified customers only. The unknown customer dimension member is retained in the dimensional model.

## Data Cleaning and Classification

The cleaned transaction dataset contains 1,044,848 rows.

| Reporting category | Rows |
|---|---:|
| SALE | 1,014,603 |
| CANCELLATION | 18,035 |
| ZERO_PRICE | 6,003 |
| POSTAGE_ADJUSTMENT | 3,511 |
| MANUAL_ADJUSTMENT | 1,473 |
| OPERATIONAL_ADJUSTMENT | 842 |
| DISCOUNT_ADJUSTMENT | 173 |
| SAMPLE_ADJUSTMENT | 102 |
| BANK_CHARGE | 100 |
| BAD_DEBT_ADJUSTMENT | 6 |
| **Total** | **1,044,848** |

Important interpretation rules:

- Negative quantity is a return candidate, not automatically a confirmed refund.
- Cancellation invoice flags and negative quantity are independent signals.
- Candidate line amount is not approved accounting revenue.
- Merchandise and non-merchandise amounts are reported separately.
- Missing customer identifiers map to the unknown customer dimension member; they are not fabricated.
- Within-file duplicate rows are preserved.
- Cross-file overlap is reconciled using exact, null-safe row comparisons and occurrence multiplicity.

## Star Schema and ER Diagram Verification

The implemented dimensional model consists of:

- `analytics.dim_customer`
- `analytics.dim_product`
- `analytics.fact_sales`
- `staging.retail_transactions` as the staging lineage source

The ER diagram is maintained at:

`database/diagrams/consumer360_star_schema.mmd`

The diagram was updated to include the staging relationship and additional implemented attributes.

PostgreSQL foreign-key constraints were queried and compared with the ER diagram.

| Child table | Child column | Parent table | Parent column | Result |
|---|---|---|---|---|
| `fact_sales` | `customer_key` | `dim_customer` | `customer_key` | Passed |
| `fact_sales` | `product_key` | `dim_product` | `product_key` | Passed |
| `fact_sales` | `staging_id` | `retail_transactions` | `staging_id` | Passed |

The staging relationship is one-to-zero-or-one from staging to fact because `fact_sales.staging_id` is unique.

Additional integrity checks confirmed:

- Zero orphan customer keys.
- Zero orphan product keys.
- 1,044,848 fact rows.
- 1,044,848 distinct staging references.
- Zero null staging references.
- Zero duplicate staging references.

**ER diagram relationship validation: passed.**

## Single Customer View Validation

The Single Customer View was validated against the populated PostgreSQL database.

| Validation | Result |
|---|---:|
| Total identified customer rows | 5,942 |
| Distinct customer keys | 5,942 |
| Null customer keys | 0 |
| Null customer IDs | 0 |
| Duplicate customer-key groups | 0 |
| Duplicate customer-ID groups | 0 |
| Negative orders, units, or revenue | 0 |
| Invalid purchase-date ranges | 0 |
| Null snapshot dates | 0 |
| Negative recency values | 0 |
| Snapshot date | 2011-12-09 |
| Recency range | 0–738 days |

All recorded Single Customer View quality checks passed.

The optimized view was also compared against the original implementation across 5,942 customers and 16 fields. All compared values matched, with zero mismatches.

## Repository Corrections

The repository work included:

- Removed Git merge-conflict markers from the Week 1 notebook and validated its JSON structure.
- Cleared stale notebook outputs so the audit must be re-executed to produce current results.
- Aligned notebook invoice-date parsing with the ingestion loader's explicit `%d-%m-%y %H:%M` format.
- Replaced hash-only overlap filtering with null-safe exact matching and multiplicity validation.
- Added unit tests for exact overlap, duplicate preservation, null values, multiplicity mismatch, and distinct rows.
- Added the missing `consumer360.cli` module required by the existing project script entry point.
- Removed the unused `consumer_360` package stub so `consumer360` is the single canonical package.
- Added schema creation to migration 001 so a fresh database can apply the migration sequence.
- Added migration 006 to optimize the Single Customer View using materialized customer metrics.
- Added query 007 to refresh and validate the materialized customer metrics.
- Updated the README with setup, migration order, validation, data interpretation, and refresh instructions.
- Updated the ER diagram to reflect the verified database relationships.
- Added GitHub Actions checks for Python tests, lint, notebook integrity, and PostgreSQL migration smoke tests.
- Confirmed `.env.example` uses `DB_SCHEMA=analytics`.

## Automated Verification

GitHub Actions completed successfully for the repository quality gates on the latest verified commit.

Recorded checks include:

- Python dependency installation: passed.
- Week 1 notebook JSON and code-cell compilation: passed.
- Unit tests: passed.
- Ruff lint: passed.
- PostgreSQL fresh-database migration smoke tests for migrations 001–005: passed.
- Required staging, classification, dimension, fact, and Single Customer View objects: passed.

Migration 006 was subsequently applied and validated against the populated local PostgreSQL database.

The CI fresh-database migration test and populated local database validation are separate verification activities. The CI test verifies clean installation; the local validation verifies the populated historical dataset.

## Single Customer View Performance Optimization

The original Single Customer View calculated customer metrics from the fact table at query time.

Migration:

`database/migrations/006_optimize_single_customer_view.sql`

creates:

- `analytics.mv_customer_metrics`
- A unique index on the customer key
- An optimized `analytics.vw_single_customer` using the materialized metrics

The refresh query is maintained at:

`database/queries/007_refresh_customer_metrics.sql`

After changes to `analytics.fact_sales`, refresh the materialized metrics explicitly before querying the updated Single Customer View:

```sql
REFRESH MATERIALIZED VIEW analytics.mv_customer_metrics;
```

The refresh is not automatically triggered by the staging loader.

## Performance Evidence

The populated local PostgreSQL database was benchmarked after applying migration 006.

| Query | Optimized execution time | Target | Result |
|---|---:|---:|---|
| Single customer lookup (18102) | 195.495 ms | Under 2,000 ms | Passed |
| Top 10 customers by merchandise revenue | 9.469 ms | Under 2,000 ms | Passed |
| Country-level merchandise revenue | 9.040 ms | Under 2,000 ms | Passed |

All three measured queries satisfy the Week 1 performance requirement.

The customer lookup still calculates the snapshot date from the fact table. The materialized metrics optimize the customer-level aggregation; they do not eliminate every fact-table scan.

These measurements are specific to the populated local PostgreSQL environment and are not guaranteed runtimes on other machines.

## Final Status

**Source-data reconciliation:** Passed.
**Data staging and transformation:** Passed.
**Star schema implementation:** Passed.
**ER diagram relationship validation:** Passed.
**Single Customer View validation:** Passed.
**Materialized-view optimization:** Passed.
**SQL performance target:** Passed.
**Automated repository quality gates:** Passed.

**Week 1 implementation and technical validation: complete.**

Documentation and ER diagram changes remain to be committed and pushed to `main`.

No Week 2 analytical work is included in this completion record.
