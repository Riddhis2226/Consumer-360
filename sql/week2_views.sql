-- ============================================================
-- Week 2 Step 1: Indexes & Analytical Views (retail_analytics)
-- ============================================================

-- 1. Performance indexes for joins, cohorts, and market basket
CREATE INDEX IF NOT EXISTS idx_tx_customer_id ON cleaned_transactions (customer_id);
CREATE INDEX IF NOT EXISTS idx_tx_invoice     ON cleaned_transactions (invoice);
CREATE INDEX IF NOT EXISTS idx_tx_stock_code  ON cleaned_transactions (stock_code);
CREATE INDEX IF NOT EXISTS idx_tx_year_month  ON cleaned_transactions (year_month);
CREATE INDEX IF NOT EXISTS idx_rfm_customer   ON customer_rfm (customer_id);

-- 2. Monthly Commercial KPIs View
CREATE OR REPLACE VIEW vw_monthly_kpis AS
SELECT
    year_month,
    COUNT(DISTINCT invoice)                        AS total_orders,
    COUNT(DISTINCT customer_id)                    AS active_customers,
    SUM(quantity)                                  AS total_units,
    ROUND(SUM(line_revenue)::numeric, 2)           AS net_revenue,
    ROUND((SUM(line_revenue) / NULLIF(COUNT(DISTINCT invoice), 0))::numeric, 2) AS avg_order_value
FROM cleaned_transactions
GROUP BY year_month
ORDER BY year_month;

-- 3. Country Performance & Revenue Share View
CREATE OR REPLACE VIEW vw_country_performance AS
SELECT
    country,
    COUNT(DISTINCT customer_id)                    AS unique_customers,
    COUNT(DISTINCT invoice)                        AS total_orders,
    SUM(quantity)                                  AS total_units,
    ROUND(SUM(line_revenue)::numeric, 2)           AS net_revenue,
    ROUND((SUM(line_revenue) * 100.0 / SUM(SUM(line_revenue)) OVER ())::numeric, 2) AS revenue_share_pct
FROM cleaned_transactions
GROUP BY country
ORDER BY net_revenue DESC;

-- 4. Rule-Based RFM Customer Segments View
CREATE OR REPLACE VIEW vw_rfm_segments AS
SELECT
    customer_id,
    country,
    last_purchase,
    recency,
    frequency,
    ROUND(monetary::numeric, 2)                    AS monetary,
    total_units,
    ROUND(avg_order_value::numeric, 2)             AS avg_order_value,
    r_score,
    f_score,
    m_score,
    rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN f_score >= 3 AND m_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2                  THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND (f_score >= 3 OR m_score >= 3) THEN 'At Risk'
        ELSE 'Hibernating / Lost'
    END AS rfm_segment
FROM customer_rfm;