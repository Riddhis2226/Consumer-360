\set ON_ERROR_STOP on
CREATE OR REPLACE VIEW dw.v_cohort_retention AS
WITH activity AS (
 SELECT DISTINCT customer_key,DATE_TRUNC('month',invoice_ts)::DATE AS active_month
 FROM dw.fact_transaction_line
 WHERE is_merchandise AND NOT is_return AND customer_key<>0
), cohort_customers AS (
 SELECT customer_key,DATE_TRUNC('month',first_purchase_date)::DATE AS cohort_month,
        DATE_TRUNC('month',first_purchase_date)::DATE=DATE '2009-12-01' AS is_legacy_cohort
 FROM dw.mv_customer_360
), cohort_activity AS (
 SELECT c.cohort_month,c.is_legacy_cohort,c.customer_key,a.active_month,
  ((EXTRACT(YEAR FROM a.active_month)-EXTRACT(YEAR FROM c.cohort_month))*12+
   EXTRACT(MONTH FROM a.active_month)-EXTRACT(MONTH FROM c.cohort_month))::INT AS month_offset
 FROM cohort_customers c JOIN activity a USING(customer_key)
), cohort_sizes AS (
 SELECT cohort_month,COUNT(*) AS cohort_size,BOOL_OR(is_legacy_cohort) AS is_legacy_cohort
 FROM cohort_customers GROUP BY cohort_month
), end_date AS (
 SELECT MAX(invoice_ts)::DATE AS last_date,DATE_TRUNC('month',MAX(invoice_ts))::DATE AS last_month
 FROM dw.fact_transaction_line WHERE is_merchandise
)
SELECT ca.cohort_month,ca.month_offset,cs.cohort_size,COUNT(DISTINCT ca.customer_key) AS active_customers,
 ROUND(COUNT(DISTINCT ca.customer_key)::NUMERIC/NULLIF(cs.cohort_size,0),4) AS retention_rate,
 cs.is_legacy_cohort,
 (ca.active_month=ed.last_month AND ed.last_date<> (ed.last_month+INTERVAL '1 month - 1 day')::DATE) AS is_partial_month
FROM cohort_activity ca JOIN cohort_sizes cs USING(cohort_month) CROSS JOIN end_date ed
WHERE ca.month_offset>=0
GROUP BY ca.cohort_month,ca.month_offset,cs.cohort_size,cs.is_legacy_cohort,ca.active_month,ed.last_month,ed.last_date;
