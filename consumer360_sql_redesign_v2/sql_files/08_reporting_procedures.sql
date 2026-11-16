\set ON_ERROR_STOP on
-- Explicit reusable reporting procedure required by the Infotact brief.
CREATE OR REPLACE PROCEDURE ops.refresh_customer_360()
LANGUAGE plpgsql
AS $$
DECLARE v_run_id BIGINT;
BEGIN
 INSERT INTO ops.pipeline_run(status,notes) VALUES('running','Refresh customer view, RFM and serving marts') RETURNING run_id INTO v_run_id;
 BEGIN
   REFRESH MATERIALIZED VIEW dw.mv_customer_360;
   TRUNCATE mart.kpis,mart.monthly_sales,mart.top_products,mart.segment_summary,mart.cohort_retention,
            mart_private.customer_segments;
   INSERT INTO mart.kpis
   SELECT (SELECT COUNT(*) FROM dw.mv_customer_360),
          (SELECT COUNT(DISTINCT invoice_no) FROM dw.fact_transaction_line WHERE is_merchandise AND NOT is_return),
          (SELECT ROUND(SUM(CASE WHEN is_return THEN -ABS(line_amount) ELSE line_amount END),2) FROM dw.fact_transaction_line WHERE is_merchandise),
          (SELECT MIN(invoice_ts)::DATE FROM dw.fact_transaction_line WHERE is_merchandise),
          (SELECT MAX(invoice_ts)::DATE FROM dw.fact_transaction_line WHERE is_merchandise),
          (SELECT ROUND(100.0*SUM(monetary) FILTER(WHERE revenue_decile<=2)/NULLIF(SUM(monetary),0),1) FROM dw.mv_customer_360 WHERE monetary>0),
          (SELECT ROUND(100.0*COUNT(*) FILTER(WHERE frequency=1)/NULLIF(COUNT(*),0),1) FROM dw.mv_customer_360);
   INSERT INTO mart.monthly_sales SELECT DATE_TRUNC('month',f.invoice_ts)::DATE,co.country,co.region,
    ROUND(SUM(f.line_amount) FILTER(WHERE NOT f.is_return AND f.is_merchandise),2),
    ROUND(SUM(ABS(f.line_amount)) FILTER(WHERE f.is_return AND f.is_merchandise),2),
    ROUND(SUM(CASE WHEN f.is_return THEN -ABS(f.line_amount) ELSE f.line_amount END) FILTER(WHERE f.is_merchandise),2),
    COUNT(DISTINCT f.invoice_no) FILTER(WHERE NOT f.is_return AND f.is_merchandise),
    COUNT(DISTINCT f.customer_key) FILTER(WHERE NOT f.is_return AND f.is_merchandise AND f.customer_key<>0),
    BOOL_OR(DATE_TRUNC('month',f.invoice_ts)::DATE=DATE_TRUNC('month',b.last_ts)::DATE AND b.last_ts::DATE<>(DATE_TRUNC('month',b.last_ts)+INTERVAL '1 month - 1 day')::DATE)
   FROM dw.fact_transaction_line f JOIN dw.dim_country co USING(country_key)
   CROSS JOIN (SELECT MAX(invoice_ts) last_ts FROM dw.fact_transaction_line WHERE is_merchandise) b
   WHERE f.is_merchandise GROUP BY 1,2,3;
   INSERT INTO mart.top_products
   SELECT p.stock_code,p.description,ROUND(SUM(CASE WHEN f.is_return THEN -ABS(f.line_amount) ELSE f.line_amount END),2),
    SUM(CASE WHEN f.is_return THEN -ABS(f.quantity) ELSE f.quantity END),
    COUNT(DISTINCT f.customer_key) FILTER(WHERE NOT f.is_return AND f.customer_key<>0)
   FROM dw.fact_transaction_line f JOIN dw.dim_product p USING(product_key) WHERE f.is_merchandise
   GROUP BY p.stock_code,p.description ORDER BY 3 DESC LIMIT 100;
   INSERT INTO mart.segment_summary SELECT * FROM dw.v_rfm_validation;
   INSERT INTO mart.cohort_retention SELECT * FROM dw.v_cohort_retention;
   INSERT INTO mart_private.customer_segments
   SELECT r.customer_id,r.latest_country,r.latest_region,r.recency_days,r.frequency,r.monetary,r.r_score,r.f_score,r.m_score,r.rfm_code,r.segment,
    c.first_purchase_date,c.last_purchase_date,c.cohort_month,c.is_legacy_cohort,c.avg_order_value,c.return_rate,c.distinct_products,
    c.avg_days_between_orders,c.revenue_decile
   FROM dw.v_rfm r JOIN dw.mv_customer_360 c USING(customer_key);
   UPDATE ops.pipeline_run SET status='succeeded',finished_at=clock_timestamp(),fact_rows=(SELECT COUNT(*) FROM dw.fact_transaction_line) WHERE run_id=v_run_id;
 EXCEPTION WHEN OTHERS THEN
   UPDATE ops.pipeline_run SET status='failed',finished_at=clock_timestamp(),notes=SQLERRM WHERE run_id=v_run_id;
   RAISE;
 END;
END $$;

CREATE OR REPLACE PROCEDURE ops.record_pipeline_success()
LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO ops.pipeline_run(status,finished_at,source_rows,deduplicated_rows,fact_rows,notes)
 SELECT 'succeeded',clock_timestamp(),(SELECT COUNT(*) FROM stg.online_retail_raw),
        (SELECT COUNT(*) FROM stg.online_retail_raw) - COALESCE((SELECT observed_value FROM ops.data_quality_result WHERE check_name='cross_file_overlap_removed' ORDER BY result_id DESC LIMIT 1),0),
        (SELECT COUNT(*) FROM dw.fact_transaction_line),
        'Initial warehouse build completed';
END $$;
