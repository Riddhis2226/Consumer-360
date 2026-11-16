\set ON_ERROR_STOP on
CREATE OR REPLACE VIEW dw.v_rfm AS
WITH base AS (
 SELECT customer_key,customer_id,latest_country,latest_region,recency_days,frequency,monetary,
        COUNT(*) OVER() AS n,
        RANK() OVER(ORDER BY recency_days ASC) AS r_rank,
        RANK() OVER(ORDER BY monetary ASC) AS m_rank
 FROM dw.mv_customer_360 WHERE monetary>0 AND frequency>0
), scored AS (
 SELECT *,
  (5-LEAST(4,FLOOR(5.0*(r_rank-1)/NULLIF(n,0))))::INT AS r_score,
  CASE WHEN frequency>=9 THEN 5 WHEN frequency>=5 THEN 4 WHEN frequency>=3 THEN 3 WHEN frequency=2 THEN 2 ELSE 1 END AS f_score,
  (1+LEAST(4,FLOOR(5.0*(m_rank-1)/NULLIF(n,0))))::INT AS m_score
 FROM base
)
SELECT customer_key,customer_id,latest_country,latest_region,recency_days,frequency,monetary,
 r_score,f_score,m_score,r_score::TEXT||f_score::TEXT||m_score::TEXT AS rfm_code,
 CASE WHEN r_score>=4 AND f_score>=4 THEN 'Champions'
      WHEN r_score>=3 AND f_score>=3 THEN 'Loyalists'
      WHEN r_score<=2 AND f_score>=3 THEN 'At Risk'
      WHEN r_score>=4 AND f_score<=2 THEN 'New / Promising'
      WHEN r_score=3 AND f_score<=2 THEN 'Needs Attention'
      ELSE 'Hibernating' END AS segment
FROM scored;

CREATE OR REPLACE VIEW dw.v_rfm_validation AS
SELECT segment,COUNT(*) AS customers,ROUND(AVG(monetary),2) AS avg_net_monetary,
       ROUND(AVG(frequency),2) AS avg_frequency,ROUND(AVG(recency_days),1) AS avg_recency_days,
       ROUND(SUM(monetary),2) AS segment_net_revenue
FROM dw.v_rfm GROUP BY segment;
