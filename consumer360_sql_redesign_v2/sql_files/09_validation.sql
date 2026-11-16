\set ON_ERROR_STOP on
-- These queries are intended as release gates; investigate every FAIL/WARN.
SELECT 'fact_rows' AS check_name,COUNT(*)::BIGINT AS observed_value FROM dw.fact_transaction_line
UNION ALL SELECT 'unknown_customer_lines',COUNT(*) FROM dw.fact_transaction_line WHERE customer_key=0
UNION ALL SELECT 'invalid_customer_key',COUNT(*) FROM dw.fact_transaction_line f LEFT JOIN dw.dim_customer c USING(customer_key) WHERE c.customer_key IS NULL
UNION ALL SELECT 'invalid_product_key',COUNT(*) FROM dw.fact_transaction_line f LEFT JOIN dw.dim_product p USING(product_key) WHERE p.product_key IS NULL
UNION ALL SELECT 'invalid_country_key',COUNT(*) FROM dw.fact_transaction_line f LEFT JOIN dw.dim_country c USING(country_key) WHERE c.country_key IS NULL;

-- Segment sanity: Champions should be materially stronger than the population.
SELECT * FROM dw.v_rfm_validation ORDER BY segment;
SELECT CASE WHEN MAX(avg_net_monetary) FILTER(WHERE segment='Champions') >= MAX(avg_net_monetary) FILTER(WHERE segment<>'Champions')
            THEN 'PASS' ELSE 'REVIEW' END AS champion_spend_validation
FROM dw.v_rfm_validation;

-- Revenue reconciliation: signed line-level merchandise value must equal monthly mart total.
SELECT (SELECT ROUND(SUM(CASE WHEN is_return THEN -ABS(line_amount) ELSE line_amount END),2)
        FROM dw.fact_transaction_line WHERE is_merchandise) AS warehouse_net_revenue,
       (SELECT ROUND(SUM(net_merchandise_revenue),2) FROM mart.monthly_sales) AS mart_net_revenue;
