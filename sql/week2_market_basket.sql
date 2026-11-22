DROP TABLE IF EXISTS product_affinity;

CREATE TABLE product_affinity AS
WITH basket_items AS (
    SELECT DISTINCT
        invoice,
        stock_code,
        MAX(description) OVER (PARTITION BY stock_code) AS description
    FROM cleaned_transactions
),
total_baskets AS (
    SELECT COUNT(DISTINCT invoice)::numeric AS total_invoices
    FROM basket_items
),
item_counts AS (
    SELECT
        stock_code,
        MAX(description) AS description,
        COUNT(DISTINCT invoice)::numeric AS item_invoices
    FROM basket_items
    GROUP BY stock_code
),
pair_counts AS (
    SELECT
        a.stock_code AS stock_code_a,
        b.stock_code AS stock_code_b,
        COUNT(*)::numeric AS pair_invoices
    FROM basket_items a
    JOIN basket_items b
        ON a.invoice = b.invoice
       AND a.stock_code < b.stock_code
    GROUP BY a.stock_code, b.stock_code
    HAVING COUNT(*) >= 20
)
SELECT
    p.stock_code_a,
    ia.description AS description_a,
    p.stock_code_b,
    ib.description AS description_b,
    p.pair_invoices::int AS pair_count,
    ia.item_invoices::int AS item_a_count,
    ib.item_invoices::int AS item_b_count,
    ROUND(p.pair_invoices * 100.0 / tb.total_invoices, 4) AS support_pct,
    ROUND(p.pair_invoices * 100.0 / ia.item_invoices, 2) AS confidence_a_to_b_pct,
    ROUND(p.pair_invoices * 100.0 / ib.item_invoices, 2) AS confidence_b_to_a_pct,
    ROUND(
        (p.pair_invoices / tb.total_invoices)
        / NULLIF((ia.item_invoices / tb.total_invoices) * (ib.item_invoices / tb.total_invoices), 0),
        2
    ) AS lift
FROM pair_counts p
JOIN item_counts ia ON p.stock_code_a = ia.stock_code
JOIN item_counts ib ON p.stock_code_b = ib.stock_code
CROSS JOIN total_baskets tb
ORDER BY p.pair_invoices DESC, lift DESC;