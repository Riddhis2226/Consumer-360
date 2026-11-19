# Consumer360 — Retail Analytics

Retail analytics project using the UCI Online Retail II dataset. Week 1 establishes a reproducible PostgreSQL data foundation for downstream customer analytics.

## Technology
- Python 3.11+, uv, pandas, SQLAlchemy 2, Psycopg 3
- PostgreSQL 18 (the SQL is intended to work on PostgreSQL 15+)
- SQL migrations and analytical views

## Week 1 deliverables
- Source profiling for both Online Retail II files
- Exact cross-file overlap reconciliation; within-file duplicates are preserved
- PostgreSQL staging with source-file and source-row lineage
- Data-quality flags and transaction classification
- Star schema: `analytics.dim_customer`, `analytics.dim_product`, `analytics.fact_sales`
- Single Customer View: `analytics.vw_single_customer`
- Unknown dimension members and referential-integrity checks
- Historical SQL benchmarks with a target below 2,000 ms

## Source files
Place the two source files in `data/raw/` (they are intentionally not committed):
- `online_retail_II_2009-10.csv`
- `online_retail_II_2010-11.csv`

## Environment
```bash
uv sync --all-groups
cp .env.example .env
```
Configure local PostgreSQL credentials in `.env`. Use `DB_SCHEMA=analytics`. Never commit `.env` or raw source CSV files.

## Week 1 execution
Run from the repository root:
```bash
uv run consumer360 test-connection
uv run consumer360 profile
uv run consumer360 stage
```
The staging loader refuses to append when `staging.retail_transactions` is non-empty. This prevents accidental duplicate loads.

For a clean database, apply migrations once and in numerical order:
```bash
for migration in database/migrations/00{1,2,3,4,5}_*.sql; do
  psql -v ON_ERROR_STOP=1 -d consumer360 -f "$migration"
done
```
These SQL files are an ordered first-install sequence, not a rerunnable migration framework. Back up an existing database before schema changes.

## Validation
```bash
uv run pytest
uv run ruff check .
```
Open `notebooks/01_week1_data_foundation_audit.ipynb` and run all cells after source files and PostgreSQL are available. Database checks are read-only. Missing prerequisites are reported as `NOT VERIFIED`, never as a pass.

Run the historical query set:
```bash
psql -v ON_ERROR_STOP=1 -d consumer360 -f database/queries/006_performance_benchmark.sql
```
Committed benchmark figures are historical, not guaranteed current runtimes. Re-run on the target machine and record the PostgreSQL version, data state, and execution times.

## Data interpretation rules
- Negative quantity is a return candidate, not automatically a confirmed refund.
- Cancellation invoice flags and negative quantity are independent signals.
- Candidate line amount is not approved accounting revenue.
- Merchandise and non-merchandise amounts are reported separately.
- Missing customer identifiers map to the unknown customer dimension member; they are not fabricated.
- The Single Customer View covers identified customers, so its revenue differs from the full fact-table merchandise total.

## Subsequent work
RFM, cohort analysis, market basket analysis, CLV, Power BI reporting, and automation belong to later project phases.
