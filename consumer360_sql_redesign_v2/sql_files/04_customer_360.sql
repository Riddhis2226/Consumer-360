\set ON_ERROR_STOP on
DROP MATERIALIZED VIEW IF EXISTS dw.mv_customer_360 CASCADE;
CREATE MATERIALIZED VIEW dw.mv_customer_360 AS
WITH sales_lines AS (
 SELECT f.*,
        CASE WHEN f.is_return THEN -ABS(f.line_amount) ELSE f.line_amount END AS signed_amount
 FROM dw.fact_transaction_line f
 WHERE f.is_merchandise
), purchase_invoices AS (
 SELECT customer_key, invoice_no, MIN(invoice_ts) AS invoice_ts, SUM(line_amount) AS invoice_amount
 FROM sales_lines WHERE NOT is_return AND customer_key <> 0
 GROUP BY customer_key,invoice_no
), order_gaps AS (
 SELECT customer_key, invoice_ts::DATE - LAG(invoice_ts::DATE) OVER (PARTITION BY customer_key ORDER BY invoice_ts,invoice_no) AS days_between
 FROM purchase_invoices
), gap_summary AS (
 SELECT customer_key,ROUND(AVG(days_between),1) AS avg_days_between_orders FROM order_gaps GROUP BY customer_key
), customer_metrics AS (
 SELECT customer_key,
  MIN(invoice_ts) FILTER(WHERE NOT is_return AND line_amount>0) AS first_purchase_ts,
  MAX(invoice_ts) FILTER(WHERE NOT is_return AND line_amount>0) AS last_purchase_ts,
  COUNT(DISTINCT invoice_no) FILTER(WHERE NOT is_return AND line_amount>0) AS frequency,
  SUM(line_amount) FILTER(WHERE NOT is_return AND line_amount>0) AS gross_revenue,
  SUM(ABS(line_amount)) FILTER(WHERE is_return) AS return_value,
  SUM(signed_amount) AS net_revenue,
  SUM(quantity) FILTER(WHERE NOT is_return) AS units_purchased,
  COUNT(DISTINCT product_key) FILTER(WHERE NOT is_return) AS distinct_products
 FROM sales_lines WHERE customer_key<>0 GROUP BY customer_key
), snapshot AS (
 SELECT MAX(invoice_ts)::DATE + 1 AS snapshot_date FROM sales_lines WHERE NOT is_return
)
SELECT c.customer_key,c.customer_id,
       (SELECT co.country FROM dw.fact_transaction_line f JOIN dw.dim_country co USING(country_key)
        WHERE f.customer_key=c.customer_key AND f.is_merchandise ORDER BY f.invoice_ts DESC,f.transaction_line_key DESC LIMIT 1) AS latest_country,
       (SELECT co.region FROM dw.fact_transaction_line f JOIN dw.dim_country co USING(country_key)
        WHERE f.customer_key=c.customer_key AND f.is_merchandise ORDER BY f.invoice_ts DESC,f.transaction_line_key DESC LIMIT 1) AS latest_region,
       m.first_purchase_ts::DATE AS first_purchase_date,m.last_purchase_ts::DATE AS last_purchase_date,
       (s.snapshot_date-m.last_purchase_ts::DATE) AS recency_days,
       m.frequency,ROUND(m.gross_revenue,2) AS gross_revenue,ROUND(COALESCE(m.return_value,0),2) AS return_value,
       ROUND(m.net_revenue,2) AS monetary,
       ROUND(COALESCE(m.return_value,0)/NULLIF(m.gross_revenue,0),4) AS return_rate,
       ROUND(m.gross_revenue/NULLIF(m.frequency,0),2) AS avg_order_value,
       m.units_purchased,m.distinct_products,
       (s.snapshot_date-m.first_purchase_ts::DATE) AS tenure_days,
       g.avg_days_between_orders,
       RANK() OVER(ORDER BY m.net_revenue DESC) AS revenue_rank,
       DENSE_RANK() OVER(ORDER BY m.net_revenue DESC) AS revenue_dense_rank,
       NTILE(10) OVER(ORDER BY m.net_revenue DESC) AS revenue_decile,
       DATE_TRUNC('month',m.first_purchase_ts)::DATE AS cohort_month,
       EXTRACT(MONTH FROM m.first_purchase_ts) IN(10,11,12) AS acquired_holiday_season,
       DATE_TRUNC('month',m.first_purchase_ts)::DATE=DATE '2009-12-01' AS is_legacy_cohort,
       s.snapshot_date
FROM customer_metrics m
JOIN dw.dim_customer c USING(customer_key)
CROSS JOIN snapshot s
LEFT JOIN gap_summary g USING(customer_key)
WHERE m.frequency>0;
CREATE UNIQUE INDEX ux_mv_customer_360_key ON dw.mv_customer_360(customer_key);
CREATE INDEX ix_mv_customer_360_region ON dw.mv_customer_360(latest_region);
CREATE INDEX ix_mv_customer_360_cohort ON dw.mv_customer_360(cohort_month);

-- Invoice-level sequence view: LEAD is meaningful at this grain (next observed purchase after each invoice).
CREATE OR REPLACE VIEW dw.v_customer_purchase_sequence AS
SELECT customer_key,invoice_no,invoice_ts,invoice_amount,
       LEAD(invoice_ts) OVER(PARTITION BY customer_key ORDER BY invoice_ts,invoice_no) AS next_purchase_ts,
       LEAD(invoice_ts::DATE) OVER(PARTITION BY customer_key ORDER BY invoice_ts,invoice_no)-invoice_ts::DATE AS days_to_next_purchase
FROM (
 SELECT customer_key,invoice_no,MIN(invoice_ts) AS invoice_ts,SUM(line_amount) AS invoice_amount
 FROM dw.fact_transaction_line
 WHERE customer_key<>0 AND is_merchandise AND NOT is_return
 GROUP BY customer_key,invoice_no
) purchase_invoices;
