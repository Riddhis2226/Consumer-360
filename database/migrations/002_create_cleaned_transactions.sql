-- Consumer360: classified transaction layer
-- Source: staging.retail_transactions
-- The original staging table is not modified.

CREATE TABLE analytics.cleaned_transactions AS
SELECT
    classified.*,

    CASE
        WHEN transaction_category IN (
            'SALE',
            'RETURN_CANDIDATE'
        )
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

            WHEN UPPER(TRIM(stock_code)) = 'M'
                THEN 'MANUAL_ADJUSTMENT'

            WHEN UPPER(TRIM(stock_code)) = 'POST'
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

-- Preserve one-to-one traceability to the staging record.
ALTER TABLE analytics.cleaned_transactions
    ADD CONSTRAINT pk_cleaned_transactions
    PRIMARY KEY (staging_id);

CREATE INDEX idx_cleaned_customer_date
    ON analytics.cleaned_transactions (customer_id, invoice_date);

CREATE INDEX idx_cleaned_invoice_date
    ON analytics.cleaned_transactions (invoice_date);

CREATE INDEX idx_cleaned_stock_code
    ON analytics.cleaned_transactions (stock_code);

CREATE INDEX idx_cleaned_category
    ON analytics.cleaned_transactions (transaction_category);
