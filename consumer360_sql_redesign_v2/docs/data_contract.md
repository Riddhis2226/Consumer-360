# Consumer 360 data contract

## Grain

- `stg.online_retail_raw`: one loaded CSV row, with source file and ingestion identity.
- `dw.fact_transaction_line`: one retained source transaction line after cross-file overlap reconciliation and field validation.
- `dw.mv_customer_360`: one identified customer with at least one eligible merchandise purchase.
- `mart.monthly_sales`: one month × transaction country × region.
- `mart.cohort_retention`: one acquisition cohort × month offset.
- `mart_private.customer_segments`: one identified scored customer.

## Measures

| Measure | Definition |
|---|---|
| Raw line amount | `quantity * unit_price`, stored as generated `line_amount` |
| Return flag | Invoice begins with `C` OR quantity is negative |
| Signed merchandise revenue | Return: `-ABS(line_amount)`; otherwise: `line_amount` |
| Gross merchandise revenue | Sum of positive non-return merchandise line amounts |
| Return value | Sum of absolute return line amounts |
| Net merchandise revenue | Sum of signed merchandise revenue |
| Frequency | Distinct non-return merchandise invoice count per identified customer |
| Monetary | Customer net merchandise revenue over the observed data window |
| Recency | Snapshot date minus last non-return merchandise purchase date |
| Snapshot date | Maximum observed non-return merchandise timestamp date + one day |
| Cohort | Calendar month of first observed non-return merchandise purchase |

## Population rules

- Anonymous customer rows are retained in the fact with `customer_key=0`.
- Customer models exclude `customer_key=0` because identity cannot be inferred.
- Return-only customers do not enter the customer feature view.
- Non-merchandise transaction lines remain in the warehouse but are excluded from product/customer merchandise behaviour.
- Invalid date, quantity, price, blank invoice or blank stock code rows are excluded from the fact and should be investigated through staging/DQ checks.
- Zero and negative prices are not automatically discarded; valid numeric values remain available for audit and classification.
- Exact cross-file overlap is removed only from the older source file up to the duplicate multiplicity found in the newer file. Repeated records within one file are retained.

## Geography

`dim_country` maps the United Kingdom to its own region, a curated European country list to Europe, other known countries to Rest of World, and blank country to Unknown. This is a project-level grouping, not an external geopolitical standard. Revenue is grouped by transaction country.

## Data access

- `stg`, `dw`, `ops`: local engineering/analytics access.
- `mart`: aggregate serving layer intended for BI/public-safe use after review.
- `mart_private`: contains customer IDs and customer-level metrics; keep local or behind authenticated, least-privilege access. Do not publish to a public Supabase schema.
