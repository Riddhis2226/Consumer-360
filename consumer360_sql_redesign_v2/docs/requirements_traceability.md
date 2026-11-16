# Infotact requirements traceability

| Infotact requirement | Redesigned SQL support | Remaining work outside SQL |
|---|---|---|
| Fact sales + customer/product/date dimensions | `dw.fact_transaction_line`, `dw.dim_*` | ERD image and Power BI model |
| Clean raw logs; handle NULLs and negative returns | Typed staging, DQ counts, Unknown Customer, return flag | Review DQ output and sign off exclusions |
| Single Customer View | `dw.mv_customer_360` | Python integration |
| RFM scores 1–5 and segments | `dw.v_rfm` | Statistical holdout validation |
| Champions highest spend and LTV | `dw.v_rfm_validation` gives spend baseline | CLV notebook must test LTV ordering |
| Cohort retention | `dw.v_cohort_retention` | Power BI cohort matrix and interpretation |
| Top products and sales by geography/time | `mart.top_products`, `mart.monthly_sales` | Dashboard visuals |
| Advanced SQL CTE/window functions | CTEs, `RANK`, `DENSE_RANK`, `LAG`, `LEAD` (invoice-sequence view), `NTILE` | Query plan/performance evidence |
| Reusable stored procedures | `ops.refresh_customer_360()` | Test procedure against local database |
| Regional manager RLS | Transaction-time `region` in monthly mart; customer latest region in private mart | Configure and test Power BI RLS roles |
| Market basket analysis | Warehouse fact supports it | Python `mlxtend` FP-Growth and rules |
| CLV | Customer features provide model inputs | PyMC-Marketing BG/NBD + Gamma-Gamma and holdout validation |
| Churn | Customer features provide model inputs | Define prediction horizon, train LightGBM, explain with SHAP |
| Automated raw-to-dashboard pipeline | `run_all.sql` and refresh procedure | Scheduler, CI, Supabase publication and dashboard refresh |
