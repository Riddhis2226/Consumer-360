CREATE TABLE IF NOT EXISTS staging.retail_transactions (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    invoice VARCHAR(20),
    stock_code VARCHAR(50),
    description TEXT,
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(12, 4),
    customer_id VARCHAR(20),
    country VARCHAR(100),

    source_file VARCHAR(100) NOT NULL,
    source_row_number BIGINT NOT NULL,

    is_cancellation BOOLEAN NOT NULL DEFAULT FALSE,
    is_return_candidate BOOLEAN NOT NULL DEFAULT FALSE,
    has_missing_customer BOOLEAN NOT NULL DEFAULT FALSE,
    has_missing_description BOOLEAN NOT NULL DEFAULT FALSE,
    has_zero_price BOOLEAN NOT NULL DEFAULT FALSE,
    has_negative_price BOOLEAN NOT NULL DEFAULT FALSE,

    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_staging_source_row
        UNIQUE (source_file, source_row_number)
);

CREATE INDEX IF NOT EXISTS idx_staging_invoice
    ON staging.retail_transactions (invoice);

CREATE INDEX IF NOT EXISTS idx_staging_customer
    ON staging.retail_transactions (customer_id);

CREATE INDEX IF NOT EXISTS idx_staging_invoice_date
    ON staging.retail_transactions (invoice_date);

CREATE INDEX IF NOT EXISTS idx_staging_stock_code
    ON staging.retail_transactions (stock_code);
