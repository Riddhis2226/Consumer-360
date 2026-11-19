# Consumer360 — Retail Analytics

Retail analytics project using the UCI Online Retail II dataset. Week 1 establishes a reproducible PostgreSQL data foundation for downstream customer analytics.

## Technology Stack

- Python 3.11+
- uv for dependency and environment management
- pandas, SQLAlchemy 2, Psycopg 3
- PostgreSQL 18 (SQL intended to work on PostgreSQL 15+)
- SQL migrations and analytical views
- GitHub Actions for automated quality checks

## Week 1 Deliverables

- Source profiling for both Online Retail II files
- Exact cross-file overlap reconciliation; within-file duplicates are preserved
- PostgreSQL staging with source-file and source-row lineage
- Data-quality flags and transaction classification
- Star schema:
  - `analytics.dim_customer`
  - `analytics.dim_product`
  - `analytics.fact_sales`
- Validated ER diagram: `database/diagrams/consumer360_star_schema.mmd`
- Unknown dimension members and referential-integrity checks
- Single Customer View: `analytics.vw_single_customer`
- Materialized customer metrics: `analytics.mv_customer_metrics`
- SQL performance benchmarks with a target below 2,000 ms

## Source Files

Place the two source files in `data/raw/`. They are intentionally not committed.

- `online_retail_II_2009-10.csv`
- `online_retail_II_2010-11.csv`

## Environment Setup

Run the following commands from the repository root:

```bash
uv sync --all-groups
cp .env.example .env
```

Configure local PostgreSQL credentials in `.env`.

Use:

```env
DB_SCHEMA=analytics
```

Never commit `.env` or raw source CSV files.

## Week 1 Execution

Run the CLI commands from the repository root:

```bash
uv run consumer360 test-connection
uv run consumer360 profile
uv run consumer360 stage
```

The staging loader refuses to append when `staging.retail_transactions` is non-empty. This prevents accidental duplicate loads.

### Database Migrations

For a clean database, apply migrations once and in numerical order:

```bash
for migration in database/migrations/00{1,2,3,4,5,6}_*.sql; do
  psql -v ON_ERROR_STOP=1 -d consumer360 -f "$migration"
done
```

Migration 006 creates the materialized customer metrics and optimizes the Single Customer View.

These SQL files are an ordered first-install sequence, not a rerunnable migration framework. Back up an existing database before applying schema changes.

## Single Customer View and Metric Refresh

The optimized Single Customer View uses:

- `analytics.mv_customer_metrics` — materialized customer-level merchandise metrics.
- `analytics.vw_single_customer` — customer-level analytical view joining customer attributes with the materialized metrics.

After changes to `analytics.fact_sales`, refresh the materialized metrics explicitly:

```sql
REFRESH MATERIALIZED VIEW analytics.mv_customer_metrics;
```

The refresh statement and its validation checks are available in:

`database/queries/007_refresh_customer_metrics.sql`

Run the refresh after fact-table updates and before querying the refreshed Single Customer View.

The refresh is not automatically triggered by the staging loader.

## Validation

Run the automated Python tests and lint checks:

```bash
uv run pytest
uv run ruff check .
```

Open:

`notebooks/01_week1_data_foundation_audit.ipynb`

Run all notebook cells after the source files and PostgreSQL database are available.

Database checks are read-only. Missing prerequisites are reported as `NOT VERIFIED`, never as a pass.

### Performance Benchmark

Run the SQL benchmark:

```bash
psql -v ON_ERROR_STOP=1 -d consumer360 -f database/queries/006_performance_benchmark.sql
```

The target for each benchmark query is below 2,000 ms.

Committed benchmark figures are historical or environment-specific, not guaranteed current runtimes. Re-run the benchmark on the target machine and record the PostgreSQL version, data state, and execution times.

## Data Interpretation Rules

- Negative quantity is a return candidate, not automatically a confirmed refund.
- Cancellation invoice flags and negative quantity are independent signals.
- Candidate line amount is not approved accounting revenue.
- Merchandise and non-merchandise amounts are reported separately.
- Missing customer identifiers map to the unknown customer dimension member; they are not fabricated.
- The Single Customer View covers identified customers, so its revenue differs from the full fact-table merchandise total.
- Within-file duplicate rows are preserved; cross-file overlap is reconciled using exact, null-safe row comparisons and occurrence multiplicity.

## Repository Structure

```text
Consumer-360/
├── database/
│   ├── diagrams/
│   │   └── consumer360_star_schema.mmd
│   ├── migrations/
│   └── queries/
├── notebooks/
├── reports/
├── scripts/
├── src/
├── tests/
├── data/
│   └── raw/
└── README.md
```

## Subsequent Work

The following activities belong to later project phases:

- RFM analysis
- Cohort analysis
- Market basket analysis
- Customer Lifetime Value (CLV)
- Power BI reporting
- Further customer analytics and automation
