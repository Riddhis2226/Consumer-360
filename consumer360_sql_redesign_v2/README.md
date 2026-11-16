# Consumer 360 — redesigned SQL architecture

This pack replaces the original `sql_files/` implementation while preserving the project requirements and PostgreSQL-first workflow. It is designed for PostgreSQL 14+ and the two UCI Online Retail II CSV exports.

## Architecture

```text
UCI CSVs
  └─ stg.online_retail_raw       immutable-in-process raw landing; source-file lineage
       └─ typed parsing + overlap reconciliation + DQ checks
            └─ dw.dim_* + dw.fact_transaction_line   transaction-grain warehouse
                 ├─ dw.mv_customer_360                one row per identified customer
                 ├─ dw.v_rfm / dw.v_rfm_validation
                 ├─ dw.v_cohort_retention
                 ├─ mart.*                           aggregate BI / public-serving tables
                 └─ mart_private.customer_segments   customer-level; local/restricted only

ops.pipeline_run + ops.data_quality_result           operational audit trail
```

## Key design decisions

1. **Raw first, typed later.** CSV fields land as text. Invalid values are counted and excluded from the warehouse instead of causing silent cast failures.
2. **Overlap is not the same as within-file duplication.** Exact duplicate rows shared between 2009–10 and 2010–11 are reconciled using row signatures and multiplicity. Repeated lines within the same source file are retained because they may represent legitimate repeated scans. No invoice-level blanket deletion is performed.
3. **Anonymous transactions are preserved.** `dw.dim_customer.customer_key = 0` is the Unknown Customer member. These rows remain in transaction and revenue analysis, but customer-level models exclude key 0.
4. **Returns are signed consistently.** `is_return` is true for C-prefixed invoices OR negative quantities. Signed revenue is `-ABS(line_amount)` for returns and `line_amount` otherwise. Original quantity and line amount remain available for audit.
5. **Product/service classification is explicit.** All nonblank stock codes can land in the warehouse. `is_merchandise` separates product analysis from postage, discount, adjustment and other lines. The merchandise code rule is intentionally visible and should be reviewed against DQ output.
6. **Geography is transaction-time geography.** The fact references `dim_country`, not the customer's latest country. This prevents historical regional revenue from being reassigned when a customer changes country.
7. **Customer-level data is restricted.** `mart.*` contains aggregate outputs suitable for dashboards. `mart_private.customer_segments` contains customer IDs and must not be copied to a public Supabase project.
8. **Historical snapshot.** RFM recency uses the last observed merchandise sale date + 1 day, not the machine's current date.
9. **Cohort caveats are explicit.** December 2009 is left-censored; the last month is marked partial when the data ends before month-end.

## Run

From the repository root, place the CSVs here:

- `data/raw/online_retail_II_2009-10.csv`
- `data/raw/online_retail_II_2010-11.csv`

Then run:

```bash
psql -d consumer360 -v ON_ERROR_STOP=1 -f sql_files/run_all.sql
```

The loader expects the eight source columns in the standard UCI CSV order. It adds source-file lineage itself. `run_all.sql` uses psql meta-commands (`\copy`, `\i`) and must be run with `psql`, not sent as a single query through a GUI editor.

## Script order

| Script | Responsibility |
|---|---|
| `00_create_schemas.sql` | Schemas, raw landing and operations tables |
| `01_load_staging.sql` | Reload both CSVs with source lineage |
| `02_warehouse_schema.sql` | Dimensions and transaction-line fact |
| `03_clean_and_load_warehouse.sql` | Parsing, overlap reconciliation, DQ, dimensions and fact load |
| `04_customer_360.sql` | Customer feature view, LAG/LEAD, RANK/DENSE_RANK |
| `05_rfm_segmentation.sql` | RFM scores and segment validation |
| `06_cohort_retention.sql` | Monthly cohort retention and caveat flags |
| `07_serving_marts.sql` | Dashboard marts and restricted customer-level mart |
| `08_reporting_procedures.sql` | Reusable refresh procedure and pipeline logging |
| `09_validation.sql` | Referential, segment and revenue reconciliation checks |

## After the initial build

The full `run_all.sql` rebuilds dimensions and facts. For a subsequent refresh after a controlled fact reload, run:

```sql
CALL ops.refresh_customer_360();
```

This refreshes the customer materialized view and repopulates the serving marts. It does not reload the raw CSVs or rebuild the warehouse dimensions/fact table.

## Important release checks

- Review `ops.data_quality_result` after the build.
- Compare `mart.kpis.net_merchandise_revenue` with the sum of `mart.monthly_sales.net_merchandise_revenue`.
- Confirm Unknown Customer transaction volume is expected.
- Review all `product_type` classifications, especially unusual stock codes.
- Verify Champions' average spend against other segments; do not assume the segment label proves the outcome.
- Test actual query timings with `EXPLAIN (ANALYZE, BUFFERS)` on the target machine. No `<2 second` performance claim is made until measured.
- Apply database roles/permissions before exposing marts to Power BI, Streamlit or Supabase.

## Limits

This is a redesigned SQL source pack, not a claim that the database has been executed. PostgreSQL execution, row-count reconciliation, index effectiveness, and BI connector behavior must be verified in the user's local PostgreSQL environment. The SQL uses only source fields present in the supplied Online Retail II files.
