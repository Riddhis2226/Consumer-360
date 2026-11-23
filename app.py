"""
Consumer-360 | Executive Retail & Customer Intelligence Dashboard
Portable Streamlit application supporting Supabase, Local PostgreSQL, and Local CSV fallback,
with full Dark & Light UI themes inspired by modern SaaS analytics interfaces.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consumer-360 | Retail Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. PORTABLE ENV & PATH RESOLUTION
# -----------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    for candidate in [start, start.parent, Path.cwd()]:
        if (candidate / "data" / "supabase_db").exists() or (candidate / ".env").exists():
            return candidate
    return start


PROJECT_ROOT = find_project_root(APP_DIR)
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "supabase_db"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Zero-dependency .env parser that strips surrounding quotes."""
    env_vars: Dict[str, str] = {}
    if not env_path.exists():
        return env_vars
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and (
            (val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]
        env_vars[key] = val
    return env_vars


def get_config(key: str, env_map: Dict[str, str], default: str = "") -> str:
    """Priority: st.secrets -> os.environ -> .env file -> default."""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    return env_map.get(key, default)


ENV_MAP = load_env_file(DEFAULT_ENV_FILE)


# -----------------------------------------------------------------------------
# 3. THEME DEFINITIONS (DARK & LIGHT)
# -----------------------------------------------------------------------------
THEMES = {
    "Dark": {
        "bg_app": "#0B1120",
        "bg_nav": "#0F172A",
        "bg_card": "#11192C",
        "bg_card_hover": "#162038",
        "bg_table_head": "#0E1526",
        "bg_pill": "#1E293B",
        "border": "rgba(148, 163, 184, 0.16)",
        "border_strong": "rgba(148, 163, 184, 0.28)",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "accent": "#6366F1",
        "accent_soft": "rgba(99, 102, 241, 0.16)",
        "green": "#34D399",
        "green_soft": "rgba(52, 211, 153, 0.14)",
        "amber": "#F59E0B",
        "amber_soft": "rgba(245, 158, 11, 0.14)",
        "red": "#FB7185",
        "red_soft": "rgba(251, 113, 133, 0.14)",
        "sky": "#38BDF8",
        "sky_soft": "rgba(56, 189, 248, 0.14)",
        "grid": "rgba(148, 163, 184, 0.10)",
        "plotly_template": "plotly_dark",
        "series": ["#34D399", "#F59E0B", "#818CF8", "#38BDF8", "#FB7185", "#A78BFA", "#2DD4BF"],
        "shadow": "0 4px 20px rgba(0, 0, 0, 0.35)",
    },
    "Light": {
        "bg_app": "#F8FAFC",
        "bg_nav": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "bg_card_hover": "#F1F5F9",
        "bg_table_head": "#F8FAFC",
        "bg_pill": "#F1F5F9",
        "border": "#E2E8F0",
        "border_strong": "#CBD5E1",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_muted": "#64748B",
        "accent": "#4F46E5",
        "accent_soft": "rgba(79, 70, 229, 0.10)",
        "green": "#059669",
        "green_soft": "rgba(5, 150, 105, 0.10)",
        "amber": "#D97706",
        "amber_soft": "rgba(217, 119, 6, 0.10)",
        "red": "#E11D48",
        "red_soft": "rgba(225, 29, 72, 0.10)",
        "sky": "#0284C7",
        "sky_soft": "rgba(2, 132, 199, 0.10)",
        "grid": "rgba(15, 23, 42, 0.08)",
        "plotly_template": "plotly_white",
        "series": ["#059669", "#D97706", "#4F46E5", "#0284C7", "#E11D48", "#7C3AED", "#0D9488"],
        "shadow": "0 2px 12px rgba(15, 23, 42, 0.05)",
    },
}


# -----------------------------------------------------------------------------
# 4. SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "Dark"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Overview"
if "show_raw_modal" not in st.session_state:
    st.session_state.show_raw_modal = False
if "data_source_pref" not in st.session_state:
    st.session_state.data_source_pref = "Auto (Supabase → Local PG → CSV)"


def inject_css(t: Dict[str, str]) -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}

        .stApp {{
            background-color: {t['bg_app']};
            color: {t['text_primary']};
        }}

        /* Hide default Streamlit chrome for clean SaaS look */
        #MainMenu, footer, header[data-testid="stHeader"] {{
            visibility: hidden;
            height: 0;
        }}

        .block-container {{
            padding-top: 1.2rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1480px;
        }}

        /* Top Navbar */
        .c360-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: {t['bg_nav']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 0.75rem 1.25rem;
            margin-bottom: 1.1rem;
            box-shadow: {t['shadow']};
        }}
        .c360-brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .c360-logo {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {t['text_primary']};
            letter-spacing: -0.02em;
        }}
        .c360-badge {{
            background: {t['bg_pill']};
            border: 1px solid {t['border']};
            color: {t['text_secondary']};
            font-size: 0.75rem;
            font-weight: 500;
            padding: 0.22rem 0.65rem;
            border-radius: 6px;
        }}
        .c360-source-pill {{
            background: {t['green_soft']};
            color: {t['green']};
            border: 1px solid {t['border']};
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.22rem 0.65rem;
            border-radius: 999px;
        }}

        /* Card containers */
        .c360-card {{
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
            box-shadow: {t['shadow']};
            margin-bottom: 1rem;
        }}
        .c360-card-title {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_secondary']};
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        /* KPI Cards */
        .c360-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1.1rem;
        }}
        @media (max-width: 1100px) {{
            .c360-kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
        .c360-kpi {{
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 0.95rem 1.1rem;
            box-shadow: {t['shadow']};
        }}
        .c360-kpi-label {{
            font-size: 0.70rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: {t['text_muted']};
            margin-bottom: 0.35rem;
        }}
        .c360-kpi-val {{
            font-size: 1.45rem;
            font-weight: 700;
            color: {t['text_primary']};
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }}
        .c360-kpi-sub {{
            font-size: 0.74rem;
            color: {t['text_secondary']};
            margin-top: 0.3rem;
        }}

        /* Custom SaaS Performance Table (Screenshot-inspired) */
        .c360-table-wrap {{
            width: 100%;
            overflow-x: auto;
        }}
        table.c360-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.84rem;
            font-variant-numeric: tabular-nums;
        }}
        table.c360-table thead th {{
            text-align: left;
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_muted']};
            padding: 0.7rem 0.85rem;
            border-bottom: 1px solid {t['border_strong']};
            background: {t['bg_table_head']};
            white-space: nowrap;
        }}
        table.c360-table thead th.num {{
            text-align: right;
        }}
        table.c360-table tbody tr {{
            border-bottom: 1px solid {t['border']};
            transition: background-color 0.15s ease;
        }}
        table.c360-table tbody tr:last-child {{
            border-bottom: none;
        }}
        table.c360-table tbody tr:hover {{
            background-color: {t['bg_card_hover']};
        }}
        table.c360-table tbody td {{
            padding: 0.78rem 0.85rem;
            color: {t['text_primary']};
            vertical-align: middle;
            white-space: nowrap;
        }}
        table.c360-table tbody td.num {{
            text-align: right;
            font-weight: 500;
        }}
        table.c360-table tbody td.name-cell {{
            font-weight: 600;
            color: {t['text_primary']};
        }}
        .c360-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.18rem 0.55rem;
            border-radius: 6px;
            font-size: 0.74rem;
            font-weight: 600;
        }}
        .pill-green {{ background: {t['green_soft']}; color: {t['green']}; }}
        .pill-amber {{ background: {t['amber_soft']}; color: {t['amber']}; }}
        .pill-red   {{ background: {t['red_soft']};   color: {t['red']}; }}
        .pill-sky   {{ background: {t['sky_soft']};   color: {t['sky']}; }}
        .pill-accent {{ background: {t['accent_soft']}; color: {t['accent']}; }}

        .c360-bar-track {{
            width: 88px;
            height: 6px;
            border-radius: 999px;
            background: {t['bg_pill']};
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 0.45rem;
        }}
        .c360-bar-fill {{
            height: 100%;
            border-radius: 999px;
        }}

        /* Streamlit widget theming adjustments */
        div[data-testid="stRadio"] > div {{
            flex-direction: row;
            gap: 0.35rem;
        }}
        .stButton > button {{
            background: {t['bg_card']};
            color: {t['text_secondary']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 500;
            padding: 0.4rem 0.85rem;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            border-color: {t['accent']};
            color: {t['text_primary']};
        }}
        .stButton > button[kind="primary"] {{
            background: {t['accent_soft']};
            border: 1px solid {t['accent']};
            color: {t['text_primary']};
            font-weight: 600;
        }}
        div[data-testid="stSelectbox"] label,
        div[data-testid="stMultiSelect"] label,
        div[data-testid="stSlider"] label,
        div[data-testid="stTextInput"] label {{
            color: {t['text_secondary']} !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 5. PORTABLE DATA LOADING (SUPABASE -> LOCAL POSTGRES -> LOCAL CSV FALLBACK)
# -----------------------------------------------------------------------------
TABLE_FILES = {
    "cohort_retention": "cohort_retention.csv",
    "product_bundles": "product_bundles.csv",
    "customer_segments": "customer_segments.csv",
    "customer_rfm_metrics": "customer_rfm_metrics.csv",
    "retail_transactions": "retail_transactions.csv",
}


def build_pg_uri(host: str, port: str, db: str, user: str, password: str, sslmode: str) -> str:
    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}?sslmode={sslmode}"
    )


@st.cache_data(ttl=600, show_spinner=False)
def load_all_data(source_pref: str) -> Tuple[Dict[str, pd.DataFrame], str]:
    """Load all 5 tables from Supabase, Local PostgreSQL, or Local CSVs."""
    from sqlalchemy import create_engine, text

    def try_postgres(uri: str, label: str) -> Optional[Tuple[Dict[str, pd.DataFrame], str]]:
        try:
            engine = create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 5})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                dfs = {}
                for tbl in TABLE_FILES:
                    dfs[tbl] = pd.read_sql(f'SELECT * FROM public."{tbl}"', conn)
            return dfs, label
        except Exception:
            return None

    def try_csv() -> Optional[Tuple[Dict[str, pd.DataFrame], str]]:
        if not DEFAULT_DATA_DIR.exists():
            return None
        dfs = {}
        for tbl, fname in TABLE_FILES.items():
            fpath = DEFAULT_DATA_DIR / fname
            if not fpath.exists():
                return None
            dfs[tbl] = pd.read_csv(fpath)
        return dfs, "Local CSVs (data/supabase_db)"

    supa_host = get_config("SUPABASE_DB_HOST", ENV_MAP)
    supa_port = get_config("SUPABASE_DB_PORT", ENV_MAP, "5432")
    supa_db = get_config("SUPABASE_DB_NAME", ENV_MAP, "postgres")
    supa_user = get_config("SUPABASE_DB_USER", ENV_MAP)
    supa_pass = get_config("SUPABASE_DB_PASSWORD", ENV_MAP)

    pg_host = get_config("PG_HOST", ENV_MAP, "localhost")
    pg_port = get_config("PG_PORT", ENV_MAP, "5432")
    pg_db = get_config("PG_DB", ENV_MAP, "retail_analytics")
    pg_user = get_config("PG_USER", ENV_MAP, "postgres")
    pg_pass = get_config("PG_PASSWORD", ENV_MAP)

    order = []
    if source_pref == "Supabase":
        order = ["supabase", "csv"]
    elif source_pref == "Local PostgreSQL":
        order = ["local", "csv"]
    elif source_pref == "Local CSVs":
        order = ["csv"]
    else:
        order = ["supabase", "local", "csv"]

    for target in order:
        if target == "supabase" and supa_host and supa_user and supa_pass:
            res = try_postgres(
                build_pg_uri(supa_host, supa_port, supa_db, supa_user, supa_pass, "require"),
                "Supabase PostgreSQL",
            )
            if res is not None:
                return res
        elif target == "local" and pg_host and pg_user and pg_pass:
            res = try_postgres(
                build_pg_uri(pg_host, pg_port, pg_db, pg_user, pg_pass, "prefer"),
                "Local PostgreSQL",
            )
            if res is not None:
                return res
        elif target == "csv":
            res = try_csv()
            if res is not None:
                return res

    raise FileNotFoundError(
        "Could not connect to Supabase/Local PostgreSQL and could not find CSVs in data/supabase_db."
    )


# -----------------------------------------------------------------------------
# 6. PLOTLY & HTML TABLE HELPERS
# -----------------------------------------------------------------------------
def style_plotly(fig: go.Figure, t: Dict[str, str], height: int = 340) -> go.Figure:
    fig.update_layout(
        template=t["plotly_template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=t["text_secondary"], size=11),
        margin=dict(l=12, r=12, t=12, b=12),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color=t["text_secondary"]),
        ),
        xaxis=dict(
            gridcolor=t["grid"],
            zerolinecolor=t["grid"],
            tickfont=dict(size=10, color=t["text_muted"]),
        ),
        yaxis=dict(
            gridcolor=t["grid"],
            zerolinecolor=t["grid"],
            tickfont=dict(size=10, color=t["text_muted"]),
        ),
        hoverlabel=dict(
            bgcolor=t["bg_card"],
            bordercolor=t["border_strong"],
            font=dict(color=t["text_primary"], size=12),
        ),
    )
    return fig


def render_html_table(headers: list[Tuple[str, str]], rows_html: str) -> str:
    th_parts = []
    for label, align in headers:
        cls = ' class="num"' if align == "right" else ""
        th_parts.append(f"<th{cls}>{html.escape(label)}</th>")
    return (
        '<div class="c360-table-wrap"><table class="c360-table">'
        f"<thead><tr>{''.join(th_parts)}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )


def fmt_currency(val: float) -> str:
    return f"£{val:,.0f}" if abs(val) >= 100 else f"£{val:,.2f}"


# -----------------------------------------------------------------------------
# 7. LOAD DATA & APPLY THEME
# -----------------------------------------------------------------------------
theme_name = st.session_state.ui_theme
T = THEMES[theme_name]
inject_css(T)

try:
    with st.spinner("Connecting to Consumer-360 data store..."):
        data, active_source = load_all_data(st.session_state.data_source_pref)
except Exception as exc:
    st.error(f"Data loading failed: {exc}")
    st.stop()

df_cohort = data["cohort_retention"].copy()
df_bundles = data["product_bundles"].copy()
df_segments = data["customer_segments"].copy()
df_rfm = data["customer_rfm_metrics"].copy()
df_tx = data["retail_transactions"].copy()

# Normalize datetime columns safely
df_tx["Order Date"] = pd.to_datetime(df_tx["Order Date"], errors="coerce")
df_segments["Last Purchase"] = pd.to_datetime(df_segments["Last Purchase"], errors="coerce")
df_rfm["Last Purchase"] = pd.to_datetime(df_rfm["Last Purchase"], errors="coerce")


# -----------------------------------------------------------------------------
# 8. TOP NAVBAR (BRAND + RAW DATA + NAVIGATION + THEME SWITCHER)
# -----------------------------------------------------------------------------
nav_tabs = ["Overview", "Customers & RFM", "Cohort Retention", "Product Bundles", "Geography & Timing"]

top_left, top_mid, top_right = st.columns([3.2, 5.2, 2.6], vertical_alignment="center")

with top_left:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.65rem; flex-wrap:wrap;">
            <span class="c360-logo">⚡ Consumer-360</span>
            <span class="c360-badge">Retail Analytics</span>
            <span class="c360-source-pill">● {html.escape(active_source)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_mid:
    tab_cols = st.columns(len(nav_tabs))
    for i, tab_name in enumerate(nav_tabs):
        btn_type = "primary" if st.session_state.active_tab == tab_name else "secondary"
        if tab_cols[i].button(tab_name, key=f"nav_{tab_name}", type=btn_type, use_container_width=True):
            st.session_state.active_tab = tab_name
            st.session_state.show_raw_modal = False
            st.rerun()

with top_right:
    c_raw, c_theme, c_src = st.columns([1.2, 1.0, 1.3])
    raw_btn_type = "primary" if st.session_state.show_raw_modal else "secondary"
    if c_raw.button("Raw Data", key="btn_raw_data", type=raw_btn_type, use_container_width=True):
        st.session_state.show_raw_modal = not st.session_state.show_raw_modal
        st.rerun()
    theme_label = "☀ Light" if theme_name == "Dark" else "🌙 Dark"
    if c_theme.button(theme_label, key="btn_theme_toggle", use_container_width=True):
        st.session_state.ui_theme = "Light" if theme_name == "Dark" else "Dark"
        st.rerun()
    chosen_src = c_src.selectbox(
        "Source",
        ["Auto (Supabase → Local PG → CSV)", "Supabase", "Local PostgreSQL", "Local CSVs"],
        index=["Auto (Supabase → Local PG → CSV)", "Supabase", "Local PostgreSQL", "Local CSVs"].index(
            st.session_state.data_source_pref
        ),
        label_visibility="collapsed",
    )
    if chosen_src != st.session_state.data_source_pref:
        st.session_state.data_source_pref = chosen_src
        st.cache_data.clear()
        st.rerun()


# -----------------------------------------------------------------------------
# 9. RAW DATA EXPLORER (WHEN TOGGLED)
# -----------------------------------------------------------------------------
if st.session_state.show_raw_modal:
    st.markdown('<div class="c360-card"><div class="c360-card-title">RAW DATABASE TABLE EXPLORER</div>', unsafe_allow_html=True)
    r_col1, r_col2, r_col3 = st.columns([2, 2, 1])
    selected_tbl = r_col1.selectbox("Select Table", list(TABLE_FILES.keys()))
    row_limit = r_col2.slider("Preview Rows", min_value=50, max_value=2000, value=250, step=50)
    raw_df = data[selected_tbl]
    csv_bytes = raw_df.head(row_limit).to_csv(index=False).encode("utf-8")
    r_col3.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"{selected_tbl}_preview.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.dataframe(raw_df.head(row_limit), use_container_width=True, height=460)
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 10. TAB VIEWS
# -----------------------------------------------------------------------------
tab = st.session_state.active_tab

if tab == "Overview":
    total_rev = float(df_tx["Line Revenue"].sum())
    total_customers = int(df_segments["Customer ID"].nunique())
    total_orders = int(df_tx["Invoice No"].nunique())
    aov = total_rev / total_orders if total_orders else 0.0
    m1_ret = df_cohort[df_cohort["Months Since First Purchase"] == 1]["Retention Rate (%)"].mean()

    st.markdown(
        f"""
        <div class="c360-kpi-grid">
            <div class="c360-kpi">
                <div class="c360-kpi-label">Total Revenue</div>
                <div class="c360-kpi-val">{fmt_currency(total_rev)}</div>
                <div class="c360-kpi-sub">{len(df_tx):,} line items</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Active Customers</div>
                <div class="c360-kpi-val">{total_customers:,}</div>
                <div class="c360-kpi-sub">{df_segments['Country'].nunique()} countries</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Total Orders</div>
                <div class="c360-kpi-val">{total_orders:,}</div>
                <div class="c360-kpi-sub">Avg {total_orders / max(total_customers, 1):.1f} orders / customer</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Avg Order Value</div>
                <div class="c360-kpi-val">{fmt_currency(aov)}</div>
                <div class="c360-kpi-sub">Per unique invoice</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Avg Month-1 Retention</div>
                <div class="c360-kpi-val">{m1_ret:.1f}%</div>
                <div class="c360-kpi-sub">Across {df_cohort['First Purchase Month'].nunique()} cohorts</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2, gap="medium")

    # Left Chart: Customer Tier Monthly Revenue Trend (multi-line like screenshot)
    with col_left:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>CUSTOMER TIER REVENUE TREND</span><span>MONTHLY (£)</span></div>', unsafe_allow_html=True)
        tx_tiered = df_tx.merge(
            df_segments[["Customer ID", "Customer Tier"]],
            on="Customer ID",
            how="left",
        )
        top_tiers = (
            tx_tiered.groupby("Customer Tier")["Line Revenue"]
            .sum()
            .nlargest(5)
            .index.tolist()
        )
        monthly_tier = (
            tx_tiered[tx_tiered["Customer Tier"].isin(top_tiers)]
            .groupby(["Year-Month", "Customer Tier"], as_index=False)["Line Revenue"]
            .sum()
            .sort_values("Year-Month")
        )
        fig_trend = px.line(
            monthly_tier,
            x="Year-Month",
            y="Line Revenue",
            color="Customer Tier",
            color_discrete_sequence=T["series"],
            line_shape="spline",
        )
        fig_trend.update_traces(line=dict(width=2.4))
        fig_trend.update_yaxes(tickprefix="£", title="")
        fig_trend.update_xaxes(title="", tickangle=-35)
        st.plotly_chart(style_plotly(fig_trend, T, height=330), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Right Chart: Segment Bubble Chart (Avg Order Value vs Days Inactive, sized by Total Spend)
    with col_right:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>BUYER GROUP VALUE VS RECENCY</span><span>BUBBLE = TOTAL SPEND</span></div>', unsafe_allow_html=True)
        seg_agg = (
            df_segments.groupby("Buyer Group", as_index=False)
            .agg(
                Customers=("Customer ID", "count"),
                Total_Spend=("Total Spend", "sum"),
                Avg_Order_Value=("Avg Order Value", "mean"),
                Avg_Days_Inactive=("Days Inactive", "mean"),
                Avg_Orders=("Total Orders", "mean"),
            )
        )
        fig_bubble = px.scatter(
            seg_agg,
            x="Avg_Days_Inactive",
            y="Avg_Order_Value",
            size="Total_Spend",
            color="Buyer Group",
            hover_name="Buyer Group",
            size_max=52,
            color_discrete_sequence=T["series"],
        )
        fig_bubble.update_traces(marker=dict(opacity=0.82, line=dict(width=1.5, color=T["bg_card"])))
        fig_bubble.update_xaxes(title="Avg Days Inactive (Lower = More Recent)", autorange="reversed")
        fig_bubble.update_yaxes(title="Avg Order Value (£)", tickprefix="£")
        st.plotly_chart(style_plotly(fig_bubble, T, height=330), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Bottom Card: Custom HTML Customer Tier Performance Table (matching screenshot bottom panel)
    st.markdown('<div class="c360-card"><div class="c360-card-title"><span>CUSTOMER TIER PERFORMANCE</span><span>SORTED BY TOTAL SPEND</span></div>', unsafe_allow_html=True)
    tier_perf = (
        df_segments.groupby("Customer Tier", as_index=False)
        .agg(
            Customers=("Customer ID", "count"),
            Total_Spend=("Total Spend", "sum"),
            Avg_Spend=("Total Spend", "mean"),
            Avg_Order=("Avg Order Value", "mean"),
            Avg_Days=("Days Inactive", "mean"),
            Avg_Score=("Overall Score", "mean"),
        )
        .sort_values("Total_Spend", ascending=False)
    )
    grand_spend = tier_perf["Total_Spend"].sum() or 1.0
    rows_html = []
    for _, r in tier_perf.iterrows():
        share_pct = (r["Total_Spend"] / grand_spend) * 100
        days = r["Avg_Days"]
        if days <= 45:
            status_cls, status_txt = "pill-green", "Active"
        elif days <= 110:
            status_cls, status_txt = "pill-amber", "At Risk"
        else:
            status_cls, status_txt = "pill-red", "Dormant"

        rows_html.append(
            f"<tr>"
            f"<td class='name-cell'>{html.escape(str(r['Customer Tier']))}</td>"
            f"<td class='num'>{fmt_currency(r['Total_Spend'])}</td>"
            f"<td class='num'>"
            f"<span class='c360-bar-track'><span class='c360-bar-fill' style='width:{min(share_pct, 100):.1f}%;background:{T['accent']};'></span></span>"
            f"{share_pct:.1f}%</td>"
            f"<td class='num'>{int(r['Customers']):,}</td>"
            f"<td class='num'>{fmt_currency(r['Avg_Order'])}</td>"
            f"<td class='num'>{r['Avg_Score']:.1f} / 12</td>"
            f"<td class='num'>{days:.0f} d</td>"
            f"<td class='num'><span class='c360-pill {status_cls}'>{status_txt}</span></td>"
            f"</tr>"
        )

    table_html = render_html_table(
        [
            ("Customer Tier", "left"),
            ("Total Spend", "right"),
            ("Revenue Share", "right"),
            ("Customers", "right"),
            ("Avg Order", "right"),
            ("Avg RFM", "right"),
            ("Days Inactive", "right"),
            ("Health", "right"),
        ],
        "".join(rows_html),
    )
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


elif tab == "Customers & RFM":
    f1, f2, f3 = st.columns([1.5, 1.5, 1.5])
    tiers = ["All"] + sorted(df_segments["Customer Tier"].dropna().unique().tolist())
    groups = ["All"] + sorted(df_segments["Buyer Group"].dropna().unique().tolist())
    countries = ["All"] + sorted(df_segments["Country"].dropna().unique().tolist())

    sel_tier = f1.selectbox("Customer Tier", tiers)
    sel_group = f2.selectbox("Buyer Group", groups)
    sel_country = f3.selectbox("Country", countries)

    filtered = df_segments.copy()
    if sel_tier != "All":
        filtered = filtered[filtered["Customer Tier"] == sel_tier]
    if sel_group != "All":
        filtered = filtered[filtered["Buyer Group"] == sel_group]
    if sel_country != "All":
        filtered = filtered[filtered["Country"] == sel_country]

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>RFM OVERALL SCORE DISTRIBUTION</span><span>CUSTOMERS</span></div>', unsafe_allow_html=True)
        score_dist = filtered.groupby("Overall Score", as_index=False)["Customer ID"].count().rename(columns={"Customer ID": "Customers"})
        fig_rfm = px.bar(score_dist, x="Overall Score", y="Customers", color_discrete_sequence=[T["accent"]])
        fig_rfm.update_xaxes(dtick=1, title="Overall RFM Score (3–12)")
        fig_rfm.update_yaxes(title="Customers")
        st.plotly_chart(style_plotly(fig_rfm, T, height=300), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>SPEND VS ORDER FREQUENCY</span><span>TOP 1,500 SAMPLE</span></div>', unsafe_allow_html=True)
        sample_df = filtered.nlargest(1500, "Total Spend")
        fig_sc = px.scatter(
            sample_df,
            x="Total Orders",
            y="Total Spend",
            color="Customer Tier",
            hover_data=["Customer ID", "Country", "Days Inactive"],
            color_discrete_sequence=T["series"],
            opacity=0.75,
        )
        fig_sc.update_yaxes(tickprefix="£", title="Total Spend (£)")
        fig_sc.update_xaxes(title="Total Orders")
        st.plotly_chart(style_plotly(fig_sc, T, height=300), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="c360-card"><div class="c360-card-title"><span>TOP CUSTOMERS LEADERBOARD</span><span>TOP 25 BY SPEND</span></div>', unsafe_allow_html=True)
    top_cust = filtered.nlargest(25, "Total Spend")
    c_rows = []
    for _, r in top_cust.iterrows():
        score = int(r["Overall Score"])
        pill_cls = "pill-green" if score >= 9 else ("pill-amber" if score >= 6 else "pill-red")
        c_rows.append(
            f"<tr>"
            f"<td class='name-cell'>#{int(r['Customer ID'])}</td>"
            f"<td>{html.escape(str(r['Country']))}</td>"
            f"<td>{html.escape(str(r['Customer Tier']))}</td>"
            f"<td>{html.escape(str(r['Buyer Group']))}</td>"
            f"<td class='num'>{fmt_currency(r['Total Spend'])}</td>"
            f"<td class='num'>{int(r['Total Orders']):,}</td>"
            f"<td class='num'>{fmt_currency(r['Avg Order Value'])}</td>"
            f"<td class='num'>{int(r['Days Inactive'])} d</td>"
            f"<td class='num'><span class='c360-pill {pill_cls}'>{score} / 12</span></td>"
            f"</tr>"
        )
    st.markdown(
        render_html_table(
            [
                ("Customer ID", "left"),
                ("Country", "left"),
                ("Tier", "left"),
                ("Buyer Group", "left"),
                ("Total Spend", "right"),
                ("Orders", "right"),
                ("Avg Order", "right"),
                ("Inactive", "right"),
                ("RFM Score", "right"),
            ],
            "".join(c_rows),
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


elif tab == "Cohort Retention":
    c1, c2 = st.columns([1.3, 1.0], gap="medium")

    with c1:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>COHORT RETENTION MATRIX (%)</span><span>MONTHS SINCE FIRST PURCHASE</span></div>', unsafe_allow_html=True)
        piv = df_cohort.pivot(
            index="First Purchase Month",
            columns="Months Since First Purchase",
            values="Retention Rate (%)",
        )
        fig_hm = px.imshow(
            piv,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="Teal" if theme_name == "Light" else "Viridis",
        )
        fig_hm.update_coloraxes(showscale=False)
        fig_hm.update_xaxes(title="Months Since First Purchase", dtick=1)
        fig_hm.update_yaxes(title="Cohort Month")
        st.plotly_chart(style_plotly(fig_hm, T, height=380), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>RETENTION DECAY CURVE</span><span>TOP 6 COHORTS</span></div>', unsafe_allow_html=True)
        top_cohorts = sorted(df_cohort["First Purchase Month"].unique())[:6]
        sub_coh = df_cohort[df_cohort["First Purchase Month"].isin(top_cohorts)]
        fig_dec = px.line(
            sub_coh,
            x="Months Since First Purchase",
            y="Retention Rate (%)",
            color="First Purchase Month",
            color_discrete_sequence=T["series"],
            markers=True,
        )
        fig_dec.update_yaxes(ticksuffix="%", title="Retention Rate")
        fig_dec.update_xaxes(dtick=1, title="Month Index")
        st.plotly_chart(style_plotly(fig_dec, T, height=380), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="c360-card"><div class="c360-card-title"><span>COHORT PERFORMANCE SUMMARY</span><span>M+0 TO M+3</span></div>', unsafe_allow_html=True)
    coh_summary = (
        df_cohort.groupby("First Purchase Month", as_index=False)
        .agg(Cohort_Size=("Cohort Size", "max"), Months_Tracked=("Months Since First Purchase", "max"))
        .sort_values("First Purchase Month")
    )
    m_lookup = df_cohort.set_index(["First Purchase Month", "Months Since First Purchase"])["Retention Rate (%)"].to_dict()
    coh_rows = []
    for _, r in coh_summary.iterrows():
        cm = r["First Purchase Month"]
        m1 = m_lookup.get((cm, 1), np.nan)
        m2 = m_lookup.get((cm, 2), np.nan)
        m3 = m_lookup.get((cm, 3), np.nan)
        m1_pill = "pill-green" if pd.notna(m1) and m1 >= 25 else ("pill-amber" if pd.notna(m1) and m1 >= 15 else "pill-sky")
        coh_rows.append(
            f"<tr>"
            f"<td class='name-cell'>{html.escape(str(cm))}</td>"
            f"<td class='num'>{int(r['Cohort_Size']):,}</td>"
            f"<td class='num'>{int(r['Months_Tracked'])} mo</td>"
            f"<td class='num'><span class='c360-pill {m1_pill}'>{f'{m1:.1f}%' if pd.notna(m1) else '—'}</span></td>"
            f"<td class='num'>{f'{m2:.1f}%' if pd.notna(m2) else '—'}</td>"
            f"<td class='num'>{f'{m3:.1f}%' if pd.notna(m3) else '—'}</td>"
            f"</tr>"
        )
    st.markdown(
        render_html_table(
            [
                ("Cohort Month", "left"),
                ("Cohort Size", "right"),
                ("Horizon", "right"),
                ("Month 1", "right"),
                ("Month 2", "right"),
                ("Month 3", "right"),
            ],
            "".join(coh_rows),
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


elif tab == "Product Bundles":
    b1, b2, b3 = st.columns([2, 1, 1])
    search_prod = b1.text_input("Search Product Name", placeholder="e.g., Heart, Cake, Lantern...")
    min_orders = b2.slider("Min Orders Together", 10, 500, 50, step=10)
    min_lift = b3.slider("Min Bundle Lift", 1.0, 20.0, 2.0, step=0.5)

    bf = df_bundles[(df_bundles["Orders Together"] >= min_orders) & (df_bundles["Bundle Lift"] >= min_lift)].copy()
    if search_prod.strip():
        q = search_prod.strip().lower()
        bf = bf[
            bf["Product A"].str.lower().str.contains(q, na=False)
            | bf["Product B"].str.lower().str.contains(q, na=False)
        ]

    col_b1, col_b2 = st.columns(2, gap="medium")
    with col_b1:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>BUNDLE LIFT VS ORDER SHARE</span><span>TOP 150 PAIRS</span></div>', unsafe_allow_html=True)
        top_b = bf.nlargest(150, "Orders Together")
        fig_b = px.scatter(
            top_b,
            x="Order Share (%)",
            y="Bundle Lift",
            size="Orders Together",
            color="Buy A -> Buy B (%)",
            hover_data=["Product A", "Product B", "Orders Together"],
            color_continuous_scale="Teal" if theme_name == "Light" else "Mint",
            size_max=34,
        )
        fig_b.update_xaxes(ticksuffix="%", title="Order Share (%)")
        fig_b.update_yaxes(title="Bundle Lift (x)")
        st.plotly_chart(style_plotly(fig_b, T, height=320), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b2:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>TOP 10 HIGHEST-CO-OCCURRENCE BUNDLES</span><span>ORDERS TOGETHER</span></div>', unsafe_allow_html=True)
        top10_b = bf.nlargest(10, "Orders Together").copy()
        top10_b["Pair"] = top10_b["Product A"].str[:24] + " + " + top10_b["Product B"].str[:24]
        fig_bar = px.bar(
            top10_b.sort_values("Orders Together"),
            x="Orders Together",
            y="Pair",
            orientation="h",
            color_discrete_sequence=[T["green"]],
        )
        fig_bar.update_yaxes(title="")
        fig_bar.update_xaxes(title="Orders Together")
        st.plotly_chart(style_plotly(fig_bar, T, height=320), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="c360-card"><div class="c360-card-title"><span>CROSS-SELL BUNDLE PERFORMANCE</span><span>TOP 25 MATCHING PAIRS</span></div>', unsafe_allow_html=True)
    b_rows = []
    for _, r in bf.nlargest(25, "Bundle Lift").iterrows():
        lift = float(r["Bundle Lift"])
        lift_cls = "pill-green" if lift >= 8 else ("pill-sky" if lift >= 4 else "pill-amber")
        b_rows.append(
            f"<tr>"
            f"<td class='name-cell'>{html.escape(str(r['Product A'])[:38])}</td>"
            f"<td class='name-cell'>{html.escape(str(r['Product B'])[:38])}</td>"
            f"<td class='num'>{int(r['Orders Together']):,}</td>"
            f"<td class='num'>{r['Order Share (%)']:.2f}%</td>"
            f"<td class='num'>{r['Buy A -> Buy B (%)']:.1f}%</td>"
            f"<td class='num'>{r['Buy B -> Buy A (%)']:.1f}%</td>"
            f"<td class='num'><span class='c360-pill {lift_cls}'>{lift:.2f}x</span></td>"
            f"</tr>"
        )
    st.markdown(
        render_html_table(
            [
                ("Product A", "left"),
                ("Product B", "left"),
                ("Orders Together", "right"),
                ("Order Share", "right"),
                ("A → B", "right"),
                ("B → A", "right"),
                ("Bundle Lift", "right"),
            ],
            "".join(b_rows),
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


elif tab == "Geography & Timing":
    g1, g2 = st.columns(2, gap="medium")

    with g1:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>TOP COUNTRIES BY REVENUE</span><span>EXCLUDING / INCLUDING UK</span></div>', unsafe_allow_html=True)
        inc_uk = st.checkbox("Include United Kingdom", value=False)
        geo_df = df_tx if inc_uk else df_tx[df_tx["Country"] != "United Kingdom"]
        geo_agg = (
            geo_df.groupby("Country", as_index=False)
            .agg(Revenue=("Line Revenue", "sum"), Orders=("Invoice No", "nunique"), Customers=("Customer ID", "nunique"))
            .nlargest(12, "Revenue")
        )
        fig_geo = px.bar(
            geo_agg.sort_values("Revenue"),
            x="Revenue",
            y="Country",
            orientation="h",
            color_discrete_sequence=[T["sky"]],
        )
        fig_geo.update_xaxes(tickprefix="£", title="Revenue (£)")
        fig_geo.update_yaxes(title="")
        st.plotly_chart(style_plotly(fig_geo, T, height=330), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="c360-card"><div class="c360-card-title"><span>REVENUE BY ORDER HOUR</span><span>HOURLY TRAFFIC</span></div>', unsafe_allow_html=True)
        hr_agg = (
            df_tx.groupby("Order Hour", as_index=False)
            .agg(Revenue=("Line Revenue", "sum"), Orders=("Invoice No", "nunique"))
            .sort_values("Order Hour")
        )
        fig_hr = px.area(
            hr_agg,
            x="Order Hour",
            y="Revenue",
            color_discrete_sequence=[T["amber"]],
        )
        fig_hr.update_xaxes(dtick=1, title="Hour of Day (24h)")
        fig_hr.update_yaxes(tickprefix="£", title="Revenue (£)")
        st.plotly_chart(style_plotly(fig_hr, T, height=330), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="c360-card"><div class="c360-card-title"><span>COUNTRY PERFORMANCE BREAKDOWN</span><span>TOP 15 MARKETS</span></div>', unsafe_allow_html=True)
    all_geo = (
        df_tx.groupby("Country", as_index=False)
        .agg(Revenue=("Line Revenue", "sum"), Orders=("Invoice No", "nunique"), Customers=("Customer ID", "nunique"), Units=("Quantity", "sum"))
        .nlargest(15, "Revenue")
    )
    tot_geo_rev = df_tx["Line Revenue"].sum() or 1.0
    g_rows = []
    for _, r in all_geo.iterrows():
        aov_c = r["Revenue"] / r["Orders"] if r["Orders"] else 0.0
        share = (r["Revenue"] / tot_geo_rev) * 100
        g_rows.append(
            f"<tr>"
            f"<td class='name-cell'>{html.escape(str(r['Country']))}</td>"
            f"<td class='num'>{fmt_currency(r['Revenue'])}</td>"
            f"<td class='num'>{share:.1f}%</td>"
            f"<td class='num'>{int(r['Customers']):,}</td>"
            f"<td class='num'>{int(r['Orders']):,}</td>"
            f"<td class='num'>{fmt_currency(aov_c)}</td>"
            f"<td class='num'>{int(r['Units']):,}</td>"
            f"</tr>"
        )
    st.markdown(
        render_html_table(
            [
                ("Country", "left"),
                ("Revenue", "right"),
                ("Share", "right"),
                ("Customers", "right"),
                ("Orders", "right"),
                ("Avg Order", "right"),
                ("Units Sold", "right"),
            ],
            "".join(g_rows),
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)