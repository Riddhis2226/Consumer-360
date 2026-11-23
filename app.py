import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from streamlit.errors import StreamlitSecretNotFoundError

st.set_page_config(
    page_title="Consumer-360 Retail Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border: 1px solid #e2e8f0;
            border-left: 4px solid #0f766e;
            border-radius: 10px;
            padding: 0.9rem 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.82rem;
            font-weight: 600;
            color: #475569;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.28rem;
            font-weight: 700;
            color: #0f172a;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.5rem;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }
        button[data-baseweb="tab"] {
            font-weight: 600;
            padding: 0.55rem 1rem;
            border-radius: 8px 8px 0 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_secret(key: str) -> str | None:
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except (StreamlitSecretNotFoundError, FileNotFoundError, KeyError):
        pass
    val = os.getenv(key)
    return val.strip() if val else None


def _build_supabase_engine():
    db_password = _get_secret("SUPABASE_DB_PASSWORD")
    if db_password:
        db_url = URL.create(
            drivername="postgresql+psycopg2",
            username=_get_secret("SUPABASE_DB_USER") or "postgres.jtydikmxeclhrkcpxpyr",
            password=db_password,
            host=_get_secret("SUPABASE_DB_HOST") or "aws-1-ap-south-1.pooler.supabase.com",
            port=int(_get_secret("SUPABASE_DB_PORT") or "5432"),
            database=_get_secret("SUPABASE_DB_NAME") or "postgres",
            query={"sslmode": "require"},
        )
        return create_engine(db_url, connect_args={"connect_timeout": 10})

    supabase_url = _get_secret("SUPABASE_DB_URL")
    if supabase_url:
        if supabase_url.startswith("postgres://"):
            supabase_url = supabase_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif supabase_url.startswith("postgresql://"):
            supabase_url = supabase_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return create_engine(supabase_url, connect_args={"connect_timeout": 10})

    return None


@st.cache_data(ttl=3600, show_spinner="Loading data from Supabase PostgreSQL...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    engine = _build_supabase_engine()
    if engine is None:
        st.error(
            "Missing Supabase credentials. Set `SUPABASE_DB_PASSWORD` (recommended) or "
            "`SUPABASE_DB_URL` in Streamlit Secrets or `.env`."
        )
        st.stop()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        tx = pd.read_sql("SELECT * FROM cleaned_transactions", engine)
        seg = pd.read_sql("SELECT * FROM customer_segments", engine)
        coh = pd.read_sql("SELECT * FROM cohort_retention", engine)
        aff = pd.read_sql("SELECT * FROM product_affinity", engine)
    except SQLAlchemyError as exc:
        st.error(f"Supabase PostgreSQL connection failed: {exc}")
        st.stop()

    tx["invoice_date"] = pd.to_datetime(tx["invoice_date"])
    return tx, seg, coh, aff


tx_df, seg_df, coh_df, aff_df = load_data()

with st.sidebar:
    st.markdown("### Transaction & Segment Filters")
    st.success("Connected: **Supabase PostgreSQL**")
    st.caption(
        "**Filter scope:** Date, Country & Segment filter **KPIs** and **Executive Overview**. "
        "Country & Segment also filter **Customer Segmentation**."
    )

    min_date = tx_df["invoice_date"].min().date()
    max_date = tx_df["invoice_date"].max().date()
    date_range = st.date_input(
        "Invoice Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    countries = sorted(tx_df["country"].dropna().unique().tolist())
    selected_countries = st.multiselect(
        "Country",
        options=countries,
        default=[],
        placeholder="All countries",
    )

    segments = sorted(seg_df["rfm_segment"].dropna().unique().tolist())
    selected_segments = st.multiselect(
        "RFM Segment",
        options=segments,
        default=[],
        placeholder="All segments",
    )

filtered_tx = tx_df.copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered_tx = filtered_tx[
        (filtered_tx["invoice_date"] >= start_dt) & (filtered_tx["invoice_date"] <= end_dt)
    ]

if selected_countries:
    filtered_tx = filtered_tx[filtered_tx["country"].isin(selected_countries)]

if selected_segments:
    seg_customers = seg_df.loc[seg_df["rfm_segment"].isin(selected_segments), "customer_id"]
    filtered_tx = filtered_tx[filtered_tx["customer_id"].isin(seg_customers)]

filtered_seg = seg_df.copy()
if selected_countries:
    filtered_seg = filtered_seg[filtered_seg["country"].isin(selected_countries)]
if selected_segments:
    filtered_seg = filtered_seg[filtered_seg["rfm_segment"].isin(selected_segments)]

st.title("Consumer-360 Retail Analytics")
st.caption(
    "Transaction performance, RFM & K-Means segmentation, cohort retention, and market basket intelligence."
)

total_revenue = filtered_tx["line_revenue"].sum()
total_orders = filtered_tx["invoice"].nunique()
total_customers = filtered_tx["customer_id"].nunique()
total_units = filtered_tx["quantity"].sum()
aov = total_revenue / total_orders if total_orders else 0.0
basket_size = total_units / total_orders if total_orders else 0.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Net Revenue", f"£{total_revenue:,.2f}")
k2.metric("Total Orders", f"{total_orders:,}")
k3.metric("Unique Customers", f"{total_customers:,}")
k4.metric("Avg Order Value", f"£{aov:,.2f}")
k5.metric("Avg Basket Size", f"{basket_size:,.1f} units")

st.write("")

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Executive Overview",
        "Customer Segmentation",
        "Cohort Retention",
        "Market Basket",
    ]
)

with tab1:
    monthly = (
        filtered_tx.groupby("year_month", as_index=False)
        .agg(
            revenue=("line_revenue", "sum"),
            orders=("invoice", "nunique"),
        )
        .sort_values("year_month")
    )

    with st.container(border=True):
        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(
            go.Bar(
                x=monthly["year_month"],
                y=monthly["revenue"],
                name="Revenue (£)",
                marker_color="#0f766e",
                opacity=0.88,
            ),
            secondary_y=False,
        )
        fig_trend.add_trace(
            go.Scatter(
                x=monthly["year_month"],
                y=monthly["orders"],
                name="Orders",
                mode="lines+markers",
                line={"color": "#f59e0b", "width": 3},
                marker={"size": 7},
            ),
            secondary_y=True,
        )
        fig_trend.update_layout(
            template="plotly_white",
            title={"text": "Monthly Net Revenue & Order Volume", "x": 0, "y": 0.96},
            hovermode="x unified",
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            margin={"t": 75, "b": 30, "l": 10, "r": 10},
            height=410,
        )
        fig_trend.update_yaxes(title_text="Revenue (£)", secondary_y=False, showgrid=True)
        fig_trend.update_yaxes(title_text="Orders", secondary_y=True, showgrid=False)
        st.plotly_chart(fig_trend, width="stretch")

    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        top_countries = (
            filtered_tx.groupby("country", as_index=False)["line_revenue"]
            .sum()
            .nlargest(10, "line_revenue")
            .sort_values("line_revenue", ascending=True)
        )
        fig_country = px.bar(
            top_countries,
            x="line_revenue",
            y="country",
            orientation="h",
            title="Top 10 Countries by Net Revenue",
            labels={"line_revenue": "Net Revenue (£)", "country": ""},
            color_discrete_sequence=["#2563eb"],
            template="plotly_white",
        )
        fig_country.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 15}, height=370)
        st.plotly_chart(fig_country, width="stretch")

    with c2, st.container(border=True):
        hourly = (
            filtered_tx.groupby("hour", as_index=False)["invoice"]
            .nunique()
            .rename(columns={"invoice": "orders"})
            .sort_values("hour")
        )
        fig_hour = px.bar(
            hourly,
            x="hour",
            y="orders",
            title="Order Volume by Hour of Day",
            labels={"hour": "Hour of Day", "orders": "Orders"},
            color_discrete_sequence=["#1e293b"],
            template="plotly_white",
        )
        fig_hour.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 15}, height=370)
        st.plotly_chart(fig_hour, width="stretch")

with tab2:
    st.caption("RFM & K-Means metrics reflect full 13-month customer history, filtered by Country and RFM Segment.")
    c1, c2 = st.columns([1.2, 1])
    with c1, st.container(border=True):
        seg_summary = (
            filtered_seg.groupby("rfm_segment", as_index=False)
            .agg(
                customers=("customer_id", "nunique"),
                revenue=("monetary", "sum"),
            )
            .sort_values("revenue", ascending=True)
        )
        fig_seg = px.bar(
            seg_summary,
            x="revenue",
            y="rfm_segment",
            orientation="h",
            text="customers",
            title="RFM Segment Revenue & Customer Count",
            labels={"revenue": "Total Revenue (£)", "rfm_segment": ""},
            color_discrete_sequence=["#0f766e"],
            template="plotly_white",
        )
        fig_seg.update_traces(texttemplate="%{text:,} customers", textposition="outside")
        fig_seg.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 75}, height=370)
        st.plotly_chart(fig_seg, width="stretch")

    with c2, st.container(border=True):
        cluster_summary = (
            filtered_seg.groupby("kmeans_cluster", as_index=False)
            .agg(
                customers=("customer_id", "nunique"),
                avg_recency=("recency", "mean"),
                avg_frequency=("frequency", "mean"),
                avg_monetary=("monetary", "mean"),
                total_revenue=("monetary", "sum"),
            )
            .sort_values("total_revenue", ascending=False)
        )
        cluster_summary["avg_recency"] = cluster_summary["avg_recency"].round(1)
        cluster_summary["avg_frequency"] = cluster_summary["avg_frequency"].round(1)
        cluster_summary["avg_monetary"] = cluster_summary["avg_monetary"].round(2)
        cluster_summary["total_revenue"] = cluster_summary["total_revenue"].round(2)
        st.markdown("#### K-Means Cluster Profiles")
        st.dataframe(cluster_summary, width="stretch", hide_index=True, height=320)

    with st.container(border=True):
        scatter_df = filtered_seg.copy()
        scatter_df["kmeans_cluster"] = scatter_df["kmeans_cluster"].astype(str)
        fig_scatter = px.scatter(
            scatter_df,
            x="recency",
            y="monetary",
            color="kmeans_cluster",
            log_y=True,
            hover_data=["customer_id", "country", "frequency", "rfm_segment"],
            title="Customer Distribution: Recency vs. Monetary Value (Log Scale)",
            labels={
                "recency": "Recency (Days Since Last Purchase)",
                "monetary": "Monetary Value (£)",
                "kmeans_cluster": "Cluster",
            },
            color_discrete_sequence=["#2563eb", "#0f766e", "#f59e0b", "#64748b"],
            template="plotly_white",
        )
        fig_scatter.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 10}, height=400)
        st.plotly_chart(fig_scatter, width="stretch")

    with st.container(border=True):
        st.markdown("#### Customer Segment Explorer")
        st.dataframe(
            filtered_seg.sort_values("monetary", ascending=False).head(500),
            width="stretch",
            hide_index=True,
        )
        st.download_button(
            "Download Filtered Segments (CSV)",
            data=filtered_seg.to_csv(index=False).encode("utf-8"),
            file_name="filtered_customer_segments.csv",
            mime="text/csv",
        )

with tab3:
    st.info("Scope: Pre-aggregated across the full 13-month dataset (2009-12 to 2010-12, all countries).")
    with st.container(border=True):
        pivot_ret = coh_df.pivot(
            index="cohort_month", columns="cohort_index", values="retention_pct"
        ).sort_index()

        fig_heat = px.imshow(
            pivot_ret,
            text_auto=".0f",
            aspect="auto",
            color_continuous_scale="YlGnBu",
            zmin=0,
            zmax=60,
            title="Monthly Customer Cohort Retention (%)",
            labels={
                "x": "Months Since Acquisition (M+N)",
                "y": "Acquisition Cohort",
                "color": "%",
            },
            template="plotly_white",
        )
        fig_heat.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 10}, height=460)
        st.plotly_chart(fig_heat, width="stretch")

    with st.container(border=True):
        avg_ret = (
            coh_df[coh_df["cohort_index"] > 0]
            .groupby("cohort_index", as_index=False)["retention_pct"]
            .mean()
            .sort_values("cohort_index")
        )
        fig_curve = px.line(
            avg_ret,
            x="cohort_index",
            y="retention_pct",
            markers=True,
            title="Average Retention Curve (M+1 to M+12)",
            labels={
                "cohort_index": "Months Since Acquisition",
                "retention_pct": "Avg Retention (%)",
            },
            color_discrete_sequence=["#0f766e"],
            template="plotly_white",
        )
        fig_curve.update_traces(line={"width": 3}, marker={"size": 8})
        fig_curve.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 10}, height=350)
        st.plotly_chart(fig_curve, width="stretch")

with tab4:
    st.info("Scope: Pre-aggregated market basket rules across all 18,966 orders (all dates and countries).")
    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            sku_query = st.text_input(
                "Search Product Description",
                placeholder="e.g. HEART, CAKE CASES, JUMBO BAG",
            ).strip()
        with f2:
            min_pair_count = st.slider("Min Co-Purchased Baskets", 20, 400, 50, step=10)
        with f3:
            min_lift = st.slider("Min Lift", 1.0, 15.0, 2.0, step=0.5)

        filtered_aff = aff_df[
            (aff_df["pair_count"] >= min_pair_count) & (aff_df["lift"] >= min_lift)
        ].copy()

        if sku_query:
            mask = filtered_aff["description_a"].str.contains(sku_query, case=False, na=False) | (
                filtered_aff["description_b"].str.contains(sku_query, case=False, na=False)
            )
            filtered_aff = filtered_aff[mask]

        st.caption(f"Showing **{len(filtered_aff):,}** qualifying SKU pairs")

    top_pairs = filtered_aff.nlargest(15, "pair_count").copy()
    if not top_pairs.empty:
        with st.container(border=True):
            top_pairs["pair_label"] = (
                top_pairs["description_a"].str.slice(0, 26)
                + " + "
                + top_pairs["description_b"].str.slice(0, 26)
            )
            top_pairs = top_pairs.sort_values("pair_count", ascending=True)
            fig_pairs = px.bar(
                top_pairs,
                x="pair_count",
                y="pair_label",
                color="lift",
                orientation="h",
                title="Top 15 Co-Purchased Product Pairs",
                labels={"pair_count": "Shared Baskets", "pair_label": "", "lift": "Lift"},
                color_continuous_scale="Teal",
                template="plotly_white",
            )
            fig_pairs.update_layout(margin={"t": 55, "b": 25, "l": 10, "r": 10}, height=440)
            st.plotly_chart(fig_pairs, width="stretch")

    with st.container(border=True):
        st.dataframe(
            filtered_aff[
                [
                    "description_a",
                    "description_b",
                    "pair_count",
                    "support_pct",
                    "confidence_a_to_b_pct",
                    "confidence_b_to_a_pct",
                    "lift",
                ]
            ].head(500),
            width="stretch",
            hide_index=True,
        )
        st.download_button(
            "Download Filtered Pairs (CSV)",
            data=filtered_aff.to_csv(index=False).encode("utf-8"),
            file_name="filtered_product_affinity.csv",
            mime="text/csv",
        )