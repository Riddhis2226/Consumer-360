\set ON_ERROR_STOP on
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS mart_private;
CREATE SCHEMA IF NOT EXISTS ops;

-- This is a full-rebuild pack. Replace the prior raw-table shape, but keep the schemas.
DROP TABLE IF EXISTS stg.online_retail_raw CASCADE;

-- Raw landing is deliberately text-first: preserve source values before validation.
CREATE TABLE stg.online_retail_raw (
    raw_row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice TEXT, stock_code TEXT, description TEXT, quantity_text TEXT,
    invoice_date_text TEXT, price_text TEXT, customer_id_text TEXT, country TEXT,
    source_file TEXT NOT NULL CHECK (source_file IN ('2009-10','2010-11')),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS ops.pipeline_run (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','succeeded','failed')),
    source_rows BIGINT, deduplicated_rows BIGINT, fact_rows BIGINT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS ops.data_quality_result (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT REFERENCES ops.pipeline_run(run_id),
    check_name TEXT NOT NULL,
    observed_value NUMERIC,
    expected_value NUMERIC,
    status TEXT NOT NULL CHECK (status IN ('pass','warn','fail')),
    details TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
