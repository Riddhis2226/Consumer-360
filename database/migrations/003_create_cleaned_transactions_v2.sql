-- Consumer360: revised classified transaction layer
-- Original cleaned_transactions remains unchanged.

BEGIN;

CREATE TABLE analytics.cleaned_transactions_v2 AS
SELECT
    classified.*,
    CASE
        WHEN transaction_category IN ('SALE', 'RETURN_CANDIDATE')
            THEN quantity::NUMERIC * unit_price
        ELSE 0::NUMERIC
    END AS candidate_line_amount
FROM (
    SELECT
        source_data.*,
        CASE
            WHEN unit_price < 0
                THEN 'BAD_DEBT_ADJUSTMENT'
            WHEN UPPER(TRIM(stock_code)) = 'B'
                THEN 'BAD_DEBT_ADJUSTMENT'
            WHEN UPPER(TRIM(stock_code)) = 'BANK CHARGES'
                THEN 'BANK_CHARGE'
            WHEN UPPER(TRIM(stock_code)) = 'D'
                THEN 'DISCOUNT_ADJUSTMENT'
            WHEN UPPER(TRIM(stock_code)) IN ('M', 'ADJUST', 'ADJUST2')
                THEN 'MANUAL_ADJUSTMENT'
            WHEN UPPER(TRIM(stock_code)) IN ('POST', 'DOT')
                THEN 'POSTAGE_ADJUSTMENT'
            WHEN UPPER(TRIM(stock_code)) = 'S'
                THEN 'SAMPLE_ADJUSTMENT'
            WHEN unit_price = 0
                THEN 'ZERO_PRICE'
            WHEN is_cancellation
                THEN 'CANCELLATION'
            WHEN LOWER(COALESCE(description, '')) ~
                '(damag|lost|short|wet|sold as|invcd as|mixed|check)'
                THEN 'OPERATIONAL_ADJUSTMENT'
            WHEN quantity < 0 AND unit_price > 0
                THEN 'RETURN_CANDIDATE'
            WHEN quantity > 0 AND unit_price > 0
                THEN 'SALE'
            ELSE 'OTHER_EXCEPTION'
        END AS transaction_category
    FROM staging.retail_transactions AS source_data
) AS classified;

ALTER TABLE analytics.cleaned_transactions_v2
    ADD CONSTRAINT pk_cleaned_transactions_v2
    PRIMARY KEY (staging_id);

CREATE INDEX idx_cleaned_v2_customer_date
    ON analytics.cleaned_transactions_v2 (customer_id, invoice_date);

CREATE INDEX idx_cleaned_v2_invoice_date
    ON analytics.cleaned_transactions_v2 (invoice_date);

CREATE INDEX idx_cleaned_v2_stock_code
    ON analytics.cleaned_transactions_v2 (stock_code);

CREATE INDEX idx_cleaned_v2_category
    ON analytics.cleaned_transactions_v2 (transaction_category);

COMMIT;