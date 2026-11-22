<div align="center">

<img src="assets/banner.png" alt="Consumer-360 Retail Analytics Banner" width="100%" />

# Consumer-360 Retail Analytics

**End-to-End Customer Intelligence Pipeline, Commercial Strategy & Live Cloud BI Platform**



[License: MIT](https://www.google.com/search?q=LICENSE)

*Bridging **Data Engineering & Statistical Modeling** with **Commercial Strategy & Revenue Optimization** across **399,568** retail transactions.*

</div>

## Executive Summary

> \[!NOTE\]
> **Business Problem:** Leadership lacked unified visibility into which customer tiers actually drive margin, when seasonal buyers churn, and which SKUs should be bundled—limiting retention targeting and merchandising ROI across **37** international markets.

| Commercial KPI | Verified Baseline | Analytical Takeaway | 
| ----- | ----- | ----- | 
| **Net Revenue** | **£8,639,657.21** | 13-month operating window (`2009-12` – `2010-12`) | 
| **Order Volume** | **18,966 invoices** | **£455.53** AOV · **290.8 units/basket** (wholesale-heavy demand) | 
| **Customer Base** | **4,285 buyers** | Top 10% (`429`) generate **59.79%** of revenue; Top 20% (`857`) generate **73.38%** | 
| **Catalog Breadth** | **4,008 SKUs** | **51,240** co-purchased product pairs (`pair_count >= 20`) | 

## Business Impact & Strategic Recommendations

| Focus Area | Empirical Finding | Recommended Business Action | 
| ----- | ----- | ----- | 
| **VIP Retention** | **457 Champions** (`10.67%` of buyers) generate **£4,379,830.38** (**50.69%** of total revenue) with `7.5d` avg recency. | Prioritize white-glove retention: early Q4 stock allocation, volume rebates, and dedicated account outreach. | 
| **Churn Recovery** | **398 At Risk** customers represent **£391,012.46** in historical spend (`144.4d` avg recency, `2.3` orders). | Trigger automated win-back campaigns at the 90–120 day inactivity mark before buyers slip into `Hibernating`. | 
| **Seasonal Timing** | Cohort retention rebounds from **20.52%** (`M+1`) to **29.98%** (`M+11`), with `2009-12` hitting **49.63%** at `M+11`. | Concentrate reactivation budgets on Q4 restocking windows rather than flat year-round discounting. | 
| **Cross-Sell Bundling** | `WOODEN PICTURE FRAME WHITE FINISH` + `WOODEN FRAME ANTIQUE WHITE` co-occur in **554** baskets at **12.73x lift**. | Surface high-lift pairs as "Frequently Bought Together" cart add-ons and tiered bundle promotions. | 

## Technical Architecture

```mermaid
flowchart LR
    A["Raw Transaction Ledger"] --> B["Data Audit & RFM Engineering\nweek1_eda.ipynb"]
    B --> C[("Local PostgreSQL\nretail_analytics")]
    C --> D["SQL Views & Affinity Engine\nweek2_views.sql + week2_market_basket.sql"]
    C --> E["K-Means & Cohort Modeling\nweek2_segmentation.ipynb + week2_cohorts.ipynb"]
    D --> F[("Managed Cloud PostgreSQL")]
    E --> F
    F --> G["Live Streamlit BI Platform\napp.py"]
```

### Data & Analytics Engineering Decisions

* **SQL-Side Basket Deduplication:** `week2_market_basket.sql` deduplicates `(invoice, stock_code)` in a CTE prior to the self-join so repeated line items on the same invoice never inflate support or lift.

* **Skew-Normalized Clustering:** Because retail spend is heavily right-skewed (`£455` AOV with wholesale buyers exceeding `£300k`), `recency`, `frequency`, and `monetary` are log-transformed (`np.log1p`) and standardized (`StandardScaler`) prior to K-Means (`k=4`, Silhouette `0.3331`).

* **Indexed Analytical Warehouse:** Core fact and dimension tables are indexed on `invoice_date`, `customer_id`, and `rfm_segment` for sub-second filtering and view aggregation.

* **Resilient Cloud Connectivity:** The Streamlit layer uses `sqlalchemy.URL.create` over an IPv4-compatible database pooler with `@st.cache_data` caching for fast, reliable cloud rendering.

## Data Model (`retail_analytics`)

| Object | Type | Rows | Grain | Role in Pipeline | 
| ----- | ----- | ----- | ----- | ----- | 
| `cleaned_transactions` | Table | 399,568 | Invoice line | Audited, positive-revenue transaction ledger | 
| `customer_rfm` | Table | 4,285 | Customer | Recency, Frequency, Monetary & quartile scores | 
| `customer_segments` | Table | 4,285 | Customer | RFM segment labels + K-Means cluster assignments | 
| `cohort_retention` | Table | 91 | Cohort × Month | Monthly acquisition retention (`M+0` to `M+12`) | 
| `product_affinity` | Table | 51,240 | SKU pair | Co-purchase counts, support, confidence & lift | 
| `vw_monthly_kpis` | View | 13 | Month | Monthly revenue, orders, customers & AOV | 
| `vw_country_performance` | View | 37 | Country | Geographic revenue and order distribution | 
| `vw_rfm_segments` | View | 4,285 | Customer | Rule-based RFM segment rollups | 

## Analytical Deep Dive

<details>
<summary><b>1. RFM & K-Means Segmentation Breakdown</b></summary>

| RFM Segment | Customers | Customer Share | Total Revenue | Revenue Share | Avg Recency | Avg Frequency | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **Champions** | 457 | 10.67% | £4,379,830.38 | **50.69%** | 7.5 d | 16.1 | 
| **Loyal Customers** | 1,334 | 31.13% | £3,092,755.92 | **35.80%** | 56.7 d | 5.7 | 
| **Hibernating / Lost** | 1,393 | 32.51% | £429,627.77 | 4.97% | 167.0 d | 1.5 | 
| **At Risk** | 398 | 9.29% | £391,012.46 | 4.53% | 144.4 d | 2.3 | 
| **Potential Loyalists** | 703 | 16.41% | £346,430.67 | 4.01% | 26.8 d | 1.4 | 

* **K-Means Validation (`k=4`):** **Cluster 3** (`762` customers: `456` Champions + `306` Loyalists) captures **£5,587,685.98** (`64.67%` of total revenue) with an average spend of **£7,332.92**.

</details>

<details>
<summary><b>2. Cohort Retention & Market Basket Benchmarks</b></summary>

* **Cohort Retention (`M+0` – `M+12`):** Average retention progresses from **20.52%** (`M+1`) to **29.98%** (`M+11`), anchored by the `2009-12` cohort (`951` customers) peaking at **49.63%** in `M+11`.

* **Top Co-Purchased SKU Pairs (`pair_count >= 20`):**

| Product A | Product B | Shared Baskets | Lift | 
| ----- | ----- | ----- | ----- | 
| `RED HANGING HEART T-LIGHT HOLDER` | `WHITE HANGING HEART T-LIGHT HOLDER` | **722** | 4.56x | 
| `SWEETHEART CERAMIC TRINKET BOX` | `STRAWBERRY CERAMIC TRINKET BOX` | **622** | 10.94x | 
| `PACK OF 72 RETROSPOT CAKE CASES` | `60 TEATIME FAIRY CAKE CASES` | **601** | 6.59x | 
| `WOODEN PICTURE FRAME WHITE FINISH` | `WOODEN FRAME ANTIQUE WHITE` | **554** | **12.73x** | 
| `RED RETROSPOT JUMBO BAG` | `JUMBO BAG STRAWBERRY` | **549** | 6.96x | 

</details>

## Interactive BI Modules ([Open Live App](https://consumer-360.streamlit.app/))

* <kbd>Executive Overview</kbd> — Dual-axis Monthly Net Revenue & Order Volume trend, Top 10 Countries ranking, and Hourly Order Volume profile.

* <kbd>Customer Segmentation</kbd> — RFM revenue vs. headcount, K-Means cluster profiles, Recency vs. Monetary (log-scale) scatter plot, and filtered CSV export.

* <kbd>Cohort Retention</kbd> — Annotated `M+0` to `M+12` retention heatmap and average retention trajectory.

* <kbd>Market Basket</kbd> — Live SKU keyword search with adjustable `Min Co-Purchased Baskets` and `Min Lift` sliders for bundle discovery.

## Repository Structure

```
Consumer-360/
├── app.py                              # Production Streamlit + Plotly application
├── notebooks/
│   ├── week1_eda.ipynb                 # Data cleaning, EDA & RFM baseline
│   ├── week2_segmentation.ipynb        # RFM profiling & K-Means clustering
│   └── week2_cohorts.ipynb             # Monthly cohort retention analysis
├── sql/
│   ├── week2_views.sql                 # Indexed KPI, geography & RFM views
│   └── week2_market_basket.sql         # Co-purchase support, confidence & lift
├── data/processed/                     # Cleaned & aggregated CSV exports
├── .env.example                        # Environment variable template
├── pyproject.toml                      # uv dependency specification
└── requirements.txt                    # Cloud deployment dependency manifest

```

<details>
<summary><b>Local Reproduction</b></summary>

```
# 1. Install dependencies
uv sync

# 2. Configure local environment from template (keep .env untracked)
cp .env.example .env

# 3. Launch the dashboard
uv run streamlit run app.py

```

For cloud deployment, configure your database connection credentials in your hosting platform's **Secrets** manager.

</details>
