# Consumer360 — Retail Analytics

Retail analytics project using the UCI Online Retail II dataset.

## Technology
- Python 3.11, uv, pandas, SQLAlchemy
- PostgreSQL 18
- SQL migrations and analytical views
- Power BI (planned reporting layer)

## Week 1 — Completed
- Source profiling and cross-file overlap handling
- PostgreSQL staging and data-quality audits
- Transaction classification
- Star schema: dim_customer, dim_product, fact_sales
- Single Customer View: analytics.vw_single_customer
- ER and referential-integrity validation
- SQL performance benchmarks under 2 seconds

See Consumer360_Week1_Completion_and_Details.docx for the completion report.

## Database Migrations
Run migrations 001 through 005 in numerical order from database/migrations/.
Performance queries: database/queries/006_performance_benchmark.sql

## Setup
Run uv sync, copy .env.example to .env, and configure local PostgreSQL credentials.
Never commit .env or raw source CSV files.

## Remaining Work
RFM, cohort analysis, market basket analysis, CLV, Power BI reporting, and automation.
