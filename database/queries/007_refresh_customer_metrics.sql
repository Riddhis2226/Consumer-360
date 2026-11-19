-- Purpose: Refresh pre-aggregated customer metrics after fact_sales changes.
-- Dependency: Migration 006_optimize_single_customer_view.sql.
-- Run after warehouse fact loads and before querying the customer view.

REFRESH MATERIALIZED VIEW analytics.mv_customer_metrics;

-- Verify row counts.
SELECT
    (SELECT COUNT(*)
     FROM analytics.mv_customer_metrics) AS summary_customers,
    (SELECT COUNT(*)
     FROM analytics.vw_single_customer) AS view_customers;