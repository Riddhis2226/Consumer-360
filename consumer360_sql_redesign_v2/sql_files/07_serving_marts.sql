\set ON_ERROR_STOP on
CREATE SCHEMA IF NOT EXISTS mart_private;
DROP TABLE IF EXISTS mart.kpis,mart.monthly_sales,mart.monthly_product_sales,mart.top_products,
 mart.segment_summary,mart.cohort_retention,mart_private.customer_segments CASCADE;

-- Public-safe aggregate marts: no customer IDs or row-level purchase histories.
CREATE TABLE mart.kpis AS
SELECT (SELECT COUNT(*) FROM dw.mv_customer_360) AS scored_customers,
       (SELECT COUNT(DISTINCT invoice_no) FROM dw.fact_transaction_line WHERE is_merchandise AND NOT is_return) AS purchase_invoices,
       (SELECT ROUND(SUM(CASE WHEN is_return THEN -ABS(line_amount) ELSE line_amount END),2)
          FROM dw.fact_transaction_line WHERE is_merchandise) AS net_merchandise_revenue,
       (SELECT MIN(invoice_ts)::DATE FROM dw.fact_transaction_line WHERE is_merchandise) AS data_start,
       (SELECT MAX(invoice_ts)::DATE FROM dw.fact_transaction_line WHERE is_merchandise) AS data_end,
       (SELECT ROUND(100.0*SUM(monetary) FILTER(WHERE revenue_decile<=2)/NULLIF(SUM(monetary),0),1)
          FROM dw.mv_customer_360 WHERE monetary>0) AS top_20pct_customer_revenue_share,
       (SELECT ROUND(100.0*COUNT(*) FILTER(WHERE frequency=1)/NULLIF(COUNT(*),0),1)
          FROM dw.mv_customer_360) AS one_time_buyer_pct;

CREATE TABLE mart.monthly_sales AS
SELECT DATE_TRUNC('month',f.invoice_ts)::DATE AS month,co.country,co.region,
 ROUND(SUM(f.line_amount) FILTER(WHERE NOT f.is_return AND f.is_merchandise),2) AS gross_merchandise_revenue,
 ROUND(SUM(ABS(f.line_amount)) FILTER(WHERE f.is_return AND f.is_merchandise),2) AS return_value,
 ROUND(SUM(CASE WHEN f.is_return THEN -ABS(f.line_amount) ELSE f.line_amount END)
       FILTER(WHERE f.is_merchandise),2) AS net_merchandise_revenue,
 COUNT(DISTINCT f.invoice_no) FILTER(WHERE NOT f.is_return AND f.is_merchandise) AS purchase_invoices,
 COUNT(DISTINCT f.customer_key) FILTER(WHERE NOT f.is_return AND f.is_merchandise AND f.customer_key<>0) AS identified_active_customers,
 BOOL_OR(DATE_TRUNC('month',f.invoice_ts)::DATE=DATE_TRUNC('month',bounds.last_ts)::DATE
  AND bounds.last_ts::DATE<>(DATE_TRUNC('month',bounds.last_ts)+INTERVAL '1 month - 1 day')::DATE) AS is_partial_month
FROM dw.fact_transaction_line f JOIN dw.dim_country co USING(country_key)
CROSS JOIN (SELECT MAX(invoice_ts) AS last_ts FROM dw.fact_transaction_line WHERE is_merchandise) bounds
WHERE f.is_merchandise GROUP BY 1,2,3;

CREATE TABLE mart.top_products AS
SELECT p.stock_code,p.description,
 ROUND(SUM(CASE WHEN f.is_return THEN -ABS(f.line_amount) ELSE f.line_amount END),2) AS net_revenue,
 SUM(CASE WHEN f.is_return THEN -ABS(f.quantity) ELSE f.quantity END) AS net_units,
 COUNT(DISTINCT f.customer_key) FILTER(WHERE NOT f.is_return AND f.customer_key<>0) AS identified_buyers
FROM dw.fact_transaction_line f JOIN dw.dim_product p USING(product_key)
WHERE f.is_merchandise GROUP BY p.stock_code,p.description
ORDER BY net_revenue DESC LIMIT 100;

CREATE TABLE mart.segment_summary AS SELECT * FROM dw.v_rfm_validation;
CREATE TABLE mart.cohort_retention AS SELECT * FROM dw.v_cohort_retention;

-- Restricted local mart: contains customer identifiers; do not publish to public Supabase.
CREATE TABLE mart_private.customer_segments AS
SELECT r.customer_id,r.latest_country,r.latest_region,r.recency_days,r.frequency,r.monetary,
 r.r_score,r.f_score,r.m_score,r.rfm_code,r.segment,
 c.first_purchase_date,c.last_purchase_date,c.cohort_month,c.is_legacy_cohort,
 c.avg_order_value,c.return_rate,c.distinct_products,c.avg_days_between_orders,
 c.revenue_decile
FROM dw.v_rfm r JOIN dw.mv_customer_360 c USING(customer_key);
ALTER TABLE mart_private.customer_segments ADD PRIMARY KEY(customer_id);

CREATE INDEX ix_monthly_sales_month_region ON mart.monthly_sales(month,region);
CREATE INDEX ix_cohort_month_offset ON mart.cohort_retention(cohort_month,month_offset);
CREATE INDEX ix_private_segment ON mart_private.customer_segments(segment);
ANALYZE;
SELECT * FROM mart.kpis;
SELECT * FROM mart.segment_summary ORDER BY segment_net_revenue DESC;
