BEGIN;

CREATE OR REPLACE VIEW analytics.vw_single_customer AS
WITH snapshot AS (
    SELECT MAX(invoice_date)::date AS snapshot_date
    FROM analytics.fact_sales
),
customer_metrics AS (
    SELECT
        customer_key,

        COUNT(DISTINCT invoice) FILTER (
            WHERE merchandise_line_amount > 0
        ) AS total_orders,

        COUNT(*) FILTER (
            WHERE merchandise_line_amount > 0
        ) AS merchandise_transaction_lines,

        COALESCE(
            SUM(quantity) FILTER (
                WHERE merchandise_line_amount > 0
            ), 0
        ) AS merchandise_units,

        COALESCE(
            SUM(merchandise_line_amount), 0
        ) AS total_merchandise_revenue,

        COALESCE(
            SUM(non_merchandise_line_amount), 0
        ) AS total_non_merchandise_amount,

        SUM(candidate_line_amount) FILTER (
            WHERE source_category = 'RETURN_CANDIDATE'
        ) AS candidate_return_amount,

        COUNT(*) FILTER (
            WHERE source_category = 'RETURN_CANDIDATE'
        ) AS candidate_return_lines,

        MIN(invoice_date) FILTER (
            WHERE merchandise_line_amount > 0
        ) AS first_purchase_at,

        MAX(invoice_date) FILTER (
            WHERE merchandise_line_amount > 0
        ) AS last_purchase_at,

        COUNT(DISTINCT invoice) AS all_invoice_count

    FROM analytics.fact_sales
    WHERE customer_key <> 0
    GROUP BY customer_key
)
SELECT
    dc.customer_key,
    dc.customer_id,
    dc.country,
    dc.country_count,

    COALESCE(cm.total_orders, 0) AS total_orders,
    COALESCE(cm.all_invoice_count, 0) AS all_invoice_count,
    COALESCE(cm.merchandise_transaction_lines, 0)
        AS merchandise_transaction_lines,
    COALESCE(cm.merchandise_units, 0) AS merchandise_units,

    COALESCE(cm.total_merchandise_revenue, 0)
        AS total_merchandise_revenue,

    COALESCE(cm.total_non_merchandise_amount, 0)
        AS total_non_merchandise_amount,

    COALESCE(cm.candidate_return_amount, 0)
        AS candidate_return_amount,

    COALESCE(cm.candidate_return_lines, 0)
        AS candidate_return_lines,

    cm.first_purchase_at,
    cm.last_purchase_at,

    CASE
        WHEN cm.total_orders > 0
        THEN cm.total_merchandise_revenue
             / NULLIF(cm.total_orders, 0)
        ELSE 0
    END AS average_order_value,

    s.snapshot_date,

    CASE
        WHEN cm.last_purchase_at IS NOT NULL
        THEN s.snapshot_date - cm.last_purchase_at::date
        ELSE NULL
    END AS recency_days

FROM analytics.dim_customer dc
CROSS JOIN snapshot s
LEFT JOIN customer_metrics cm
    ON cm.customer_key = dc.customer_key
WHERE dc.is_unknown = FALSE;

-- Validate one row per identified customer.
DO $$
DECLARE
    expected_customers BIGINT;
    actual_customers BIGINT;
    duplicate_customers BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO expected_customers
    FROM analytics.dim_customer
    WHERE NOT is_unknown;

    SELECT COUNT(*)
    INTO actual_customers
    FROM analytics.vw_single_customer;

    SELECT COUNT(*)
    INTO duplicate_customers
    FROM (
        SELECT customer_key
        FROM analytics.vw_single_customer
        GROUP BY customer_key
        HAVING COUNT(*) > 1
    ) duplicates;

    IF expected_customers <> actual_customers THEN
        RAISE EXCEPTION
            'Customer count mismatch: expected %, actual %',
            expected_customers, actual_customers;
    END IF;

    IF duplicate_customers > 0 THEN
        RAISE EXCEPTION
            'Duplicate customer records found: %',
            duplicate_customers;
    END IF;

    RAISE NOTICE
        'Single Customer View validated: % customers',
        actual_customers;
END $$;

COMMIT;
