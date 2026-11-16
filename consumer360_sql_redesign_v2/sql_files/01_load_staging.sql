\set ON_ERROR_STOP on
TRUNCATE stg.online_retail_raw RESTART IDENTITY;
CREATE TEMP TABLE load_buffer (
    invoice TEXT, stock_code TEXT, description TEXT, quantity_text TEXT,
    invoice_date_text TEXT, price_text TEXT, customer_id_text TEXT, country TEXT
);
BEGIN;
\copy load_buffer FROM 'data/raw/online_retail_II_2009-10.csv' WITH (FORMAT csv, HEADER true, NULL '')
INSERT INTO stg.online_retail_raw (invoice,stock_code,description,quantity_text,invoice_date_text,price_text,customer_id_text,country,source_file)
SELECT invoice,stock_code,description,quantity_text,invoice_date_text,price_text,customer_id_text,country,'2009-10' FROM load_buffer;
TRUNCATE load_buffer;
\copy load_buffer FROM 'data/raw/online_retail_II_2010-11.csv' WITH (FORMAT csv, HEADER true, NULL '')
INSERT INTO stg.online_retail_raw (invoice,stock_code,description,quantity_text,invoice_date_text,price_text,customer_id_text,country,source_file)
SELECT invoice,stock_code,description,quantity_text,invoice_date_text,price_text,customer_id_text,country,'2010-11' FROM load_buffer;
COMMIT;
ANALYZE stg.online_retail_raw;
SELECT source_file, COUNT(*) AS loaded_rows FROM stg.online_retail_raw GROUP BY source_file ORDER BY source_file;
