\echo '===================================================='
\echo 'TEST 1: Single customer lookup'
\echo '===================================================='

EXPLAIN (ANALYZE, BUFFERS, SUMMARY)
SELECT
    customer_id,
    total_orders,
    total_merchandise_revenue,
    average_order_value,
    recency_days
FROM analytics.vw_single_customer
WHERE customer_id = '18102';

\echo '===================================================='
\echo 'TEST 2: Top 10 customers by merchandise revenue'
\echo '===================================================='

EXPLAIN (ANALYZE, BUFFERS, SUMMARY)
SELECT
    customer_id,
    country,
    total_orders,
    total_merchandise_revenue
FROM analytics.vw_single_customer
ORDER BY total_merchandise_revenue DESC
LIMIT 10;

\echo '===================================================='
\echo 'TEST 3: Country-level merchandise revenue'
\echo '===================================================='

EXPLAIN (ANALYZE, BUFFERS, SUMMARY)
SELECT
    country,
    COUNT(*) AS customers,
    SUM(total_orders) AS total_orders,
    SUM(total_merchandise_revenue) AS merchandise_revenue
FROM analytics.vw_single_customer
GROUP BY country
ORDER BY merchandise_revenue DESC;

