\set ON_ERROR_STOP on
BEGIN;
TRUNCATE dw.fact_transaction_line, dw.dim_customer, dw.dim_product, dw.dim_country, dw.dim_date RESTART IDENTITY CASCADE;
TRUNCATE ops.data_quality_result;

CREATE OR REPLACE FUNCTION stg.parse_invoice_ts(p_text TEXT) RETURNS TIMESTAMP
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE m TEXT[]; v TEXT := BTRIM(p_text);
BEGIN
  IF v IS NULL OR v = '' THEN RETURN NULL; END IF;
  m := regexp_match(v, '^(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?$');
  IF m IS NOT NULL THEN
    RETURN make_timestamp(m[1]::INT,m[2]::INT,m[3]::INT,m[4]::INT,m[5]::INT,COALESCE(m[6],'0')::INT);
  END IF;
  m := regexp_match(v, '^(\d{1,2})[-/](\d{1,2})[-/](\d{2}|\d{4}) (\d{1,2}):(\d{2})(?::(\d{2}))?$');
  IF m IS NOT NULL THEN
    RETURN make_timestamp(CASE WHEN LENGTH(m[3])=2 THEN 2000+m[3]::INT ELSE m[3]::INT END,
      m[2]::INT,m[1]::INT,m[4]::INT,m[5]::INT,COALESCE(m[6],'0')::INT);
  END IF;
  RETURN NULL;
EXCEPTION WHEN datetime_field_overflow OR invalid_text_representation THEN RETURN NULL;
END $$;

-- Parse safely; reject invalid numeric/date rows into DQ counts rather than aborting casts.
CREATE TEMP TABLE parsed_rows AS
SELECT r.*,
       CASE WHEN BTRIM(quantity_text) ~ '^[+-]?\d+$' THEN BTRIM(quantity_text)::INTEGER END AS qty,
       CASE WHEN BTRIM(price_text) ~ '^[+-]?(\d+(\.\d*)?|\.\d+)$' THEN BTRIM(price_text)::NUMERIC(14,4) END AS price,
       CASE WHEN NULLIF(BTRIM(customer_id_text),'') ~ '^\d+(\.0+)?$' THEN BTRIM(customer_id_text)::NUMERIC::INTEGER END AS customer_id,
       stg.parse_invoice_ts(invoice_date_text) AS invoice_ts,
       UPPER(BTRIM(stock_code)) AS normalized_stock_code
FROM stg.online_retail_raw r;

-- Cross-file overlap only: remove older-file copies up to the multiplicity present in newer file.
-- Same-file repeated lines are retained because they may be legitimate repeated scans.
-- The row signature is a hash of the whole row. ROW(...)::TEXT keeps NULL and '' distinct and,
-- unlike joining on the columns, matches rows whose customer_id or description is NULL
-- (NULL = NULL is never true in a join, which would leave ~7.7k anonymous overlap lines double counted).
CREATE TEMP TABLE deduplicated_rows AS
WITH signed AS (
 SELECT p.*,
        md5(ROW(invoice,stock_code,description,quantity_text,invoice_date_text,price_text,customer_id_text,country)::TEXT) AS row_sig
 FROM parsed_rows p
), numbered AS (
 SELECT s.*, ROW_NUMBER() OVER (PARTITION BY row_sig, source_file ORDER BY raw_row_id) AS same_file_n
 FROM signed s
), newer_counts AS (
 SELECT row_sig, COUNT(*) AS n FROM signed WHERE source_file='2010-11' GROUP BY row_sig
)
SELECT nb.* FROM numbered nb
LEFT JOIN newer_counts nc USING (row_sig)
WHERE nb.source_file='2010-11' OR nb.same_file_n > COALESCE(nc.n,0);

INSERT INTO ops.data_quality_result(check_name,observed_value,status,details)
SELECT 'raw_rows',COUNT(*),'pass','Rows loaded from both source files' FROM stg.online_retail_raw
UNION ALL SELECT 'missing_customer_id',COUNT(*),'warn','Retained in fact table under Unknown Customer; excluded from customer modelling' FROM parsed_rows WHERE customer_id IS NULL
UNION ALL SELECT 'invalid_invoice_date',COUNT(*),'fail','Rows excluded from warehouse; investigate source date strings' FROM parsed_rows WHERE invoice_ts IS NULL
UNION ALL SELECT 'invalid_quantity_or_price',COUNT(*),'warn','Rows excluded if quantity or price cannot be parsed' FROM parsed_rows WHERE qty IS NULL OR price IS NULL
UNION ALL SELECT 'negative_quantity',COUNT(*),'warn','Negative quantities classified as returns even without C invoice prefix' FROM parsed_rows WHERE qty < 0
UNION ALL SELECT 'cancellation_invoice',COUNT(*),'warn','C-prefixed invoice lines classified as returns' FROM parsed_rows WHERE invoice ILIKE 'C%'
UNION ALL SELECT 'cross_file_overlap_removed',
 (SELECT COUNT(*) FROM parsed_rows)-(SELECT COUNT(*) FROM deduplicated_rows),'pass','Older-file duplicate copies removed by exact row signature and multiplicity';

INSERT INTO dw.dim_customer(customer_key,customer_id,is_unknown) VALUES (0,NULL,TRUE);
SELECT setval(pg_get_serial_sequence('dw.dim_customer','customer_key'),1,FALSE);
INSERT INTO dw.dim_customer(customer_id,is_unknown)
SELECT DISTINCT customer_id,FALSE FROM deduplicated_rows WHERE customer_id IS NOT NULL
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO dw.dim_product(stock_code,description,product_type)
SELECT normalized_stock_code,
       (ARRAY_AGG(NULLIF(BTRIM(description),'') ORDER BY (NULLIF(BTRIM(description),'') IS NULL), raw_row_id DESC))[1],
       CASE WHEN normalized_stock_code LIKE 'POST%' OR normalized_stock_code = 'DOT' THEN 'postage'   -- DOT = "DOTCOM POSTAGE"
            WHEN normalized_stock_code = 'D' THEN 'discount'
            WHEN normalized_stock_code LIKE 'BANK%' OR normalized_stock_code LIKE 'ADJUST%' OR normalized_stock_code = 'B' THEN 'adjustment'
            WHEN normalized_stock_code ~ '^[0-9]{5}[A-Z]{0,3}$' THEN 'merchandise'                     -- 85123A, 15056BL, 79323LP ...
            ELSE 'other' END
FROM deduplicated_rows WHERE NULLIF(BTRIM(stock_code),'') IS NOT NULL
GROUP BY normalized_stock_code ON CONFLICT(stock_code) DO NOTHING;

INSERT INTO dw.dim_country(country,region)
SELECT DISTINCT COALESCE(NULLIF(BTRIM(country),''),'Unknown'),
 CASE WHEN COALESCE(NULLIF(BTRIM(country),''),'Unknown')='United Kingdom' THEN 'United Kingdom'
      WHEN COALESCE(NULLIF(BTRIM(country),''),'Unknown') IN
       ('Austria','Belgium','Channel Islands','Cyprus','Czech Republic','Denmark','EIRE','European Community','Finland','France','Germany','Greece','Iceland','Italy','Lithuania','Malta','Netherlands','Norway','Poland','Portugal','Spain','Sweden','Switzerland') THEN 'Europe'
      WHEN COALESCE(NULLIF(BTRIM(country),''),'Unknown')='Unknown' THEN 'Unknown' ELSE 'Rest of World' END
FROM deduplicated_rows ON CONFLICT(country) DO NOTHING;

INSERT INTO dw.dim_date
SELECT TO_CHAR(d::DATE,'YYYYMMDD')::INTEGER,d::DATE,EXTRACT(YEAR FROM d)::SMALLINT,
 EXTRACT(QUARTER FROM d)::SMALLINT,EXTRACT(MONTH FROM d)::SMALLINT,TO_CHAR(d,'Mon'),
 EXTRACT(ISODOW FROM d)::SMALLINT,(EXTRACT(ISODOW FROM d) IN (6,7)),
 (EXTRACT(MONTH FROM d) IN (10,11,12))
FROM generate_series((SELECT MIN(invoice_ts)::DATE FROM deduplicated_rows WHERE invoice_ts IS NOT NULL),
                     (SELECT MAX(invoice_ts)::DATE FROM deduplicated_rows WHERE invoice_ts IS NOT NULL),INTERVAL '1 day') d;

INSERT INTO dw.fact_transaction_line(source_raw_row_id,invoice_no,invoice_ts,date_key,customer_key,product_key,country_key,quantity,unit_price,is_return,is_merchandise,source_file)
SELECT p.raw_row_id,p.invoice, p.invoice_ts,TO_CHAR(p.invoice_ts,'YYYYMMDD')::INTEGER,
       COALESCE(c.customer_key,0),pr.product_key,co.country_key,p.qty,p.price,
       (p.invoice ILIKE 'C%' OR p.qty < 0), (pr.product_type='merchandise'),p.source_file
FROM deduplicated_rows p
JOIN dw.dim_product pr ON pr.stock_code=p.normalized_stock_code
JOIN dw.dim_country co ON co.country=COALESCE(NULLIF(BTRIM(p.country),''),'Unknown')
LEFT JOIN dw.dim_customer c ON c.customer_id=p.customer_id
WHERE p.invoice_ts IS NOT NULL AND p.qty IS NOT NULL AND p.qty<>0 AND p.price IS NOT NULL
  AND NULLIF(BTRIM(p.invoice),'') IS NOT NULL AND NULLIF(BTRIM(p.stock_code),'') IS NOT NULL;

INSERT INTO ops.data_quality_result(check_name,observed_value,status,details)
SELECT 'fact_rows_loaded',COUNT(*),'pass','All valid transaction lines including anonymous and non-merchandise lines' FROM dw.fact_transaction_line
UNION ALL SELECT 'unknown_customer_fact_rows',COUNT(*),'warn','Rows retained but excluded from customer-level models' FROM dw.fact_transaction_line WHERE customer_key=0
UNION ALL SELECT 'merchandise_fact_rows',COUNT(*),'pass','Merchandise subset used for product/customer behaviour' FROM dw.fact_transaction_line WHERE is_merchandise;

CREATE INDEX IF NOT EXISTS ix_fact_customer_ts ON dw.fact_transaction_line(customer_key,invoice_ts);
ANALYZE dw.fact_transaction_line;
ANALYZE dw.dim_customer;
ANALYZE dw.dim_product;
ANALYZE dw.dim_country;
ANALYZE dw.dim_date;

COMMIT;