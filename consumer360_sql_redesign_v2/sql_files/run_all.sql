\set ON_ERROR_STOP on
\echo 'Consumer 360 | redesigned PostgreSQL warehouse build'
\i sql_files/00_create_schemas.sql
\i sql_files/01_load_staging.sql
\i sql_files/02_warehouse_schema.sql
\i sql_files/03_clean_and_load_warehouse.sql
\i sql_files/04_customer_360.sql
\i sql_files/05_rfm_segmentation.sql
\i sql_files/06_cohort_retention.sql
\i sql_files/07_serving_marts.sql
\i sql_files/08_reporting_procedures.sql
\i sql_files/09_validation.sql
CALL ops.record_pipeline_success();
\echo 'Build complete. Inspect validation output and ops.data_quality_result.'
