"""
Consumer-360 | Executive Retail & Customer Intelligence Dashboard
Portable Streamlit application supporting Supabase, Local PostgreSQL, and Local CSV fallback,
with Dark & Light UI themes, sidebar slicers, top navigation tabs, distinct-color world map,
presentation-grade Plotly visualizations, and custom HTML performance tables.
"""

from __future__ import annotations

import contextlib
import html
import os
from pathlib import Path
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
    initial_sidebar_state="expanded",
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


def load_env_file(env_path: Path) -> dict[str, str]:
    """Zero-dependency .env parser that strips surrounding quotes."""
    env_vars: dict[str, str] = {}
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


def get_config(key: str, env_map: dict[str, str], default: str = "") -> str:
    """Priority: st.secrets -> os.environ -> .env file -> default."""
    with contextlib.suppress(FileNotFoundError, KeyError, RuntimeError):
        if key in st.secrets:
            return str(st.secrets[key])
    if env_val := os.environ.get(key):
        return env_val
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
        "map_land": "#1E293B",
        "map_ocean": "#0B1120",
        "border": "rgba(148, 163, 184, 0.16)",
        "border_strong": "rgba(148, 163, 184, 0.28)",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "accent": "#6366F1",
        "accent_soft": "rgba(99, 102, 241, 0.18)",
        "green": "#34D399",
        "green_soft": "rgba(52, 211, 153, 0.14)",
        "amber": "#F59E0B",
        "amber_soft": "rgba(245, 158, 11, 0.14)",
        "red": "#FB7185",
        "red_soft": "rgba(251, 113, 133, 0.14)",
        "sky": "#38BDF8",
        "sky_soft": "rgba(56, 189, 248, 0.14)",
        "grid": "rgba(148, 163, 184, 0.09)",
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
        "map_land": "#E2E8F0",
        "map_ocean": "#F8FAFC",
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
        "grid": "rgba(15, 23, 42, 0.07)",
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
    st.session_state.data_source_pref = "Auto"


def inject_css(t: dict[str, str]) -> None:
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

        #MainMenu, footer {{
            visibility: hidden;
            height: 0;
        }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Sidebar styling */
        section[data-testid="stSidebar"] {{
            background-color: {t['bg_nav']} !important;
            border-right: 1px solid {t['border']} !important;
        }}
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] label {{
            color: {t['text_secondary']} !important;
        }}

        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1.75rem !important;
            padding-right: 1.75rem !important;
            max-width: 1500px;
        }}

        /* Card containers via st.container(border=True) */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {t['bg_card']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 12px !important;
            padding: 1rem 1.2rem !important;
            box-shadow: {t['shadow']} !important;
            margin-bottom: 0.75rem !important;
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
            font-size: 0.72rem;
            font-weight: 500;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
        }}
        .c360-source-pill {{
            background: {t['green_soft']};
            color: {t['green']};
            border: 1px solid {t['border']};
            font-size: 0.70rem;
            font-weight: 600;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
        }}

        .c360-card-header {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_secondary']};
            margin-bottom: 0.4rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .c360-card-sub {{
            font-size: 0.68rem;
            font-weight: 600;
            color: {t['text_muted']};
        }}

        /* KPI Cards */
        .c360-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 0.4rem;
            margin-bottom: 1rem;
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
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_muted']};
            margin-bottom: 0.35rem;
        }}
        .c360-kpi-val {{
            font-size: 1.48rem;
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

        /* Custom SaaS Performance Table */
        .c360-table-wrap {{
            width: 100%;
            overflow-x: auto;
            margin-top: 0.35rem;
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
            padding: 0.72rem 0.85rem;
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
            padding: 0.18rem 0.55rem;
            border-radius: 6px;
            font-size: 0.73rem;
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

        /* Buttons & Inputs */
        .stButton > button {{
            background: {t['bg_card']};
            color: {t['text_secondary']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            font-size: 0.80rem;
            font-weight: 500;
            padding: 0.38rem 0.65rem;
            white-space: nowrap !important;
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
def load_all_data(source_pref: str) -> tuple[dict[str, pd.DataFrame], str]:
    """Load all 5 tables from Supabase, Local PostgreSQL, or Local CSVs."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    def try_postgres(uri: str, label: str) -> tuple[dict[str, pd.DataFrame], str] | None:
        try:
            engine = create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 5})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                dfs = {}
                for tbl in TABLE_FILES:
                    dfs[tbl] = pd.read_sql(f'SELECT * FROM public."{tbl}"', conn)
            return dfs, label
        except (SQLAlchemyError, OSError):
            return None

    def try_csv() -> tuple[dict[str, pd.DataFrame], str] | None:
        if not DEFAULT_DATA_DIR.exists():
            return None
        dfs = {}
        for tbl, fname in TABLE_FILES.items():
            fpath = DEFAULT_DATA_DIR / fname
            if not fpath.exists():
                return None
            dfs[tbl] = pd.read_csv(fpath)
        return dfs, "Local CSVs"

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

    if source_pref == "Supabase":
        order = ["supabase", "csv"]
    elif source_pref == "Local PG":
        order = ["local", "csv"]
    elif source_pref == "Local CSV":
        order = ["csv"]
    else:
        order = ["supabase", "local", "csv"]

    for target in order:
        if target == "supabase" and supa_host and supa_user and supa_pass:
            res = try_postgres(
                build_pg_uri(supa_host, supa_port, supa_db, supa_user, supa_pass, "require"),
                "Supabase",
            )
            if res is not None:
                return res
        elif target == "local" and pg_host and pg_user and pg_pass:
            res = try_postgres(
                build_pg_uri(pg_host, pg_port, pg_db, pg_user, pg_pass, "prefer"),
                "Local PG",
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
PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def short_gbp(val: float) -> str:
    a = abs(val)
    if a >= 1_000_000:
        return f"£{val / 1_000_000:,.1f}M"
    if a >= 100_000:
        return f"£{val / 1_000:,.0f}k"
    if a >= 1_000:
        return f"£{val / 1_000:,.1f}k"
    return f"£{val:,.0f}"


def padded_range(values, pad: float = 0.12) -> list[float] | None:
    vals = pd.Series(values).dropna()
    if vals.empty:
        return None
    lo, hi = float(vals.min()), float(vals.max())
    span = (hi - lo) or max(abs(hi), 1.0) * 0.2
    return [lo - span * pad, hi + span * pad]


def spans_orders_of_magnitude(values, ratio: float = 30.0) -> bool:
    vals = pd.Series(values).dropna()
    vals = vals[vals > 0]
    return len(vals) > 1 and float(vals.max()) / float(vals.min()) >= ratio


def style_plotly(
    fig: go.Figure,
    t: dict[str, str],
    height: int = 350,
    bottom_margin: int = 70,
    grid: str = "y",
) -> go.Figure:
    font_family = "Inter, sans-serif"
    fig.update_layout(
        template=t["plotly_template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": font_family, "color": t["text_secondary"], "size": 11},
        margin={"l": 14, "r": 14, "t": 12, "b": bottom_margin},
        bargap=0.3,
        legend_title_text="",
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.24,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11, "color": t["text_secondary"]},
            "itemsizing": "constant",
        },
        hoverlabel={
            "bgcolor": t["bg_nav"],
            "bordercolor": t["border_strong"],
            "font": {"family": font_family, "color": t["text_primary"], "size": 12},
            "align": "left",
        },
    )
    common = {
        "zeroline": False,
        "automargin": True,
        "gridcolor": t["grid"],
        "gridwidth": 1,
        "griddash": "dot",
        "tickfont": {"size": 10, "color": t["text_muted"]},
        "title_font": {"size": 11, "color": t["text_secondary"]},
        "title_standoff": 8,
    }
    fig.update_xaxes(
        showgrid=grid in ("x", "both"),
        showline=True,
        linecolor=t["border_strong"],
        ticks="outside",
        tickcolor=t["border_strong"],
        ticklen=4,
        **common,
    )
    fig.update_yaxes(showgrid=grid in ("y", "both"), showline=False, ticks="", **common)
    return fig


def card_header(title: str, subtitle: str = "") -> None:
    sub_html = f'<span class="c360-card-sub">{html.escape(subtitle)}</span>' if subtitle else ""
    st.markdown(
        f'<div class="c360-card-header"><span>{html.escape(title)}</span>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render_html_table(headers: list[tuple[str, str]], rows_html: str) -> str:
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
except FileNotFoundError as exc:
    st.error(f"Data loading failed: {exc}")
    st.stop()

df_cohort_raw = data["cohort_retention"].copy()
df_bundles_raw = data["product_bundles"].copy()
df_segments_raw = data["customer_segments"].copy()
df_rfm_raw = data["customer_rfm_metrics"].copy()
df_tx_raw = data["retail_transactions"].copy()

df_tx_raw["Order Date"] = pd.to_datetime(df_tx_raw["Order Date"], errors="coerce")
df_segments_raw["Last Purchase"] = pd.to_datetime(df_segments_raw["Last Purchase"], errors="coerce")
df_rfm_raw["Last Purchase"] = pd.to_datetime(df_rfm_raw["Last Purchase"], errors="coerce")


# -----------------------------------------------------------------------------
# 8. SIDEBAR SLICERS (ALL FILTERS LIVE HERE)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Filters & Controls")

    src_opts = ["Auto", "Supabase", "Local PG", "Local CSV"]
    chosen_src = st.selectbox(
        "Data Source",
        src_opts,
        index=src_opts.index(st.session_state.data_source_pref),
    )
    if chosen_src != st.session_state.data_source_pref:
        st.session_state.data_source_pref = chosen_src
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**Customer & Transaction Slicers**")

    all_months = sorted(df_tx_raw["Year-Month"].dropna().unique().tolist())
    sel_months = st.select_slider(
        "Order Month Range",
        options=all_months,
        value=(all_months[0], all_months[-1]),
    )

    tiers = sorted(df_segments_raw["Customer Tier"].dropna().unique().tolist())
    sel_tiers = st.multiselect("Customer Tier", tiers, default=[])

    groups = sorted(df_segments_raw["Buyer Group"].dropna().unique().tolist())
    sel_groups = st.multiselect("Buyer Group", groups, default=[])

    countries = sorted(df_segments_raw["Country"].dropna().unique().tolist())
    sel_countries = st.multiselect("Country", countries, default=[])

    st.markdown("---")
    st.markdown("**Bundle Slicers**")
    search_prod = st.text_input("Search Product Name", placeholder="e.g., Heart, Cake, Lantern...")
    min_orders = st.slider("Min Orders Together", 10, 500, 50, step=10)
    min_lift = st.slider("Min Bundle Lift", 1.0, 20.0, 2.0, step=0.5)

    st.markdown("---")
    st.markdown("**Geography Slicers**")
    inc_uk = st.checkbox("Include UK in Bar Chart", value=False)

# Apply global slicers cleanly
df_segments = df_segments_raw.copy()
if sel_tiers:
    df_segments = df_segments[df_segments["Customer Tier"].isin(sel_tiers)]
if sel_groups:
    df_segments = df_segments[df_segments["Buyer Group"].isin(sel_groups)]
if sel_countries:
    df_segments = df_segments[df_segments["Country"].isin(sel_countries)]

valid_cust_ids = set(df_segments["Customer ID"].unique())
df_tx = df_tx_raw[
    (df_tx_raw["Year-Month"] >= sel_months[0]) & (df_tx_raw["Year-Month"] <= sel_months[1])
].copy()
if sel_tiers or sel_groups or sel_countries:
    df_tx = df_tx[df_tx["Customer ID"].isin(valid_cust_ids)]
if sel_countries:
    df_tx = df_tx[df_tx["Country"].isin(sel_countries)]

df_cohort = df_cohort_raw.copy()
df_bundles = df_bundles_raw.copy()
df_rfm = df_rfm_raw[df_rfm_raw["Customer ID"].isin(valid_cust_ids)].copy()

# Consistent colors across tabs ranked by total spend
tier_order = (
    df_segments_raw.groupby("Customer Tier")["Total Spend"].sum().sort_values(ascending=False).index.tolist()
)
TIER_COLORS = {n: T["series"][i % len(T["series"])] for i, n in enumerate(tier_order)}
group_order = (
    df_segments_raw.groupby("Buyer Group")["Total Spend"].sum().sort_values(ascending=False).index.tolist()
)
GROUP_COLORS = {n: T["series"][i % len(T["series"])] for i, n in enumerate(group_order)}


# -----------------------------------------------------------------------------
# 9. TOP NAVIGATION BAR (TABS + RAW DATA + THEME TOGGLE)
# -----------------------------------------------------------------------------
nav_tabs = ["Overview", "Customers", "Cohorts", "Bundles", "Geography"]

with st.container(border=True):
    top_left, top_mid, top_right = st.columns([3.2, 5.2, 2.0], vertical_alignment="center")

    with top_left:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:0.55rem; flex-wrap:wrap;">
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
        c_raw, c_theme = st.columns([1.05, 0.95])
        raw_btn_type = "primary" if st.session_state.show_raw_modal else "secondary"
        if c_raw.button("Raw Data", key="btn_raw_data", type=raw_btn_type, use_container_width=True):
            st.session_state.show_raw_modal = not st.session_state.show_raw_modal
            st.rerun()
        theme_label = "☀ Light" if theme_name == "Dark" else "🌙 Dark"
        if c_theme.button(theme_label, key="btn_theme_toggle", use_container_width=True):
            st.session_state.ui_theme = "Light" if theme_name == "Dark" else "Dark"
            st.rerun()


# -----------------------------------------------------------------------------
# 10. RAW DATA EXPLORER (WHEN TOGGLED)
# -----------------------------------------------------------------------------
if st.session_state.show_raw_modal:
    with st.container(border=True):
        card_header("RAW DATABASE TABLE EXPLORER", "DIRECT QUERY VIEW")
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
        st.dataframe(raw_df.head(row_limit), use_container_width=True, height=440)


# -----------------------------------------------------------------------------
# 11. TAB VIEWS
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

    with col_left, st.container(border=True):
        card_header("CUSTOMER TIER REVENUE TREND", "MONTHLY (£)")
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
        fig_trend = go.Figure()
        for tier_name in top_tiers:
            sub = monthly_tier[monthly_tier["Customer Tier"] == tier_name]
            col_hex = TIER_COLORS.get(tier_name, T["series"][0])
            fig_trend.add_trace(
                go.Scatter(
                    x=sub["Year-Month"],
                    y=sub["Line Revenue"],
                    name=tier_name,
                    mode="lines+markers",
                    line={"color": col_hex, "width": 2.5, "shape": "spline", "smoothing": 0.8},
                    fill="tozeroy",
                    fillcolor=hex_to_rgba(col_hex, 0.06),
                    marker={"size": 5, "color": col_hex, "line": {"width": 1.5, "color": T["bg_card"]}},
                    hovertemplate="<b>%{fullData.name}</b>: £%{y:,.0f}<extra></extra>",
                )
            )
        fig_trend.update_layout(hovermode="x unified")
        fig_trend.update_yaxes(tickprefix="£", tickformat="~s", title="", rangemode="tozero")
        fig_trend.update_xaxes(title="", tickangle=-25, nticks=8)
        st.plotly_chart(
            style_plotly(fig_trend, T, height=345, bottom_margin=78, grid="y"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with col_right, st.container(border=True):
        card_header("BUYER GROUP VALUE VS RECENCY", "BUBBLE = TOTAL SPEND")
        seg_agg = (
            df_segments.groupby("Buyer Group", as_index=False)
            .agg(
                Customers=("Customer ID", "count"),
                Total_Spend=("Total Spend", "sum"),
                Avg_Order_Value=("Avg Order Value", "mean"),
                Avg_Days_Inactive=("Days Inactive", "mean"),
            )
        )
        max_spend = seg_agg["Total_Spend"].max() or 1.0
        fig_bubble = go.Figure()
        for _, r in seg_agg.iterrows():
            col_hex = GROUP_COLORS.get(r["Buyer Group"], T["series"][0])
            marker_size = max(26, np.sqrt(r["Total_Spend"] / max_spend) * 70)
            fig_bubble.add_trace(
                go.Scatter(
                    x=[r["Avg_Days_Inactive"]],
                    y=[r["Avg_Order_Value"]],
                    name=str(r["Buyer Group"]),
                    mode="markers+text",
                    text=[str(r["Buyer Group"])],
                    textposition="top center",
                    textfont={"size": 10, "color": T["text_secondary"]},
                    cliponaxis=False,
                    marker={
                        "size": marker_size,
                        "color": hex_to_rgba(col_hex, 0.74),
                        "line": {"color": col_hex, "width": 2},
                    },
                    customdata=[[r["Customers"], r["Total_Spend"]]],
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Avg Order Value: £%{y:,.0f}<br>"
                        "Days Inactive: %{x:.0f} d<br>"
                        "Customers: %{customdata[0]:,}<br>"
                        "Total Spend: £%{customdata[1]:,.0f}<extra></extra>"
                    ),
                )
            )
        if not seg_agg.empty:
            fig_bubble.add_hline(
                y=seg_agg["Avg_Order_Value"].mean(),
                line_dash="dash",
                line_color=T["border_strong"],
                line_width=1,
            )
            fig_bubble.add_vline(
                x=seg_agg["Avg_Days_Inactive"].mean(),
                line_dash="dash",
                line_color=T["border_strong"],
                line_width=1,
            )
            x_rng = padded_range(seg_agg["Avg_Days_Inactive"], pad=0.4)
            y_rng = padded_range(seg_agg["Avg_Order_Value"], pad=0.4)
            if x_rng:
                fig_bubble.update_xaxes(range=[x_rng[1], x_rng[0]])
            if y_rng:
                fig_bubble.update_yaxes(range=y_rng)
            for label, ax, ay, xa, ya in [
                ("High value · Lapsing", 0.01, 0.99, "left", "top"),
                ("High value · Recent", 0.99, 0.99, "right", "top"),
                ("Low value · Lapsing", 0.01, 0.01, "left", "bottom"),
                ("Low value · Recent", 0.99, 0.01, "right", "bottom"),
            ]:
                fig_bubble.add_annotation(
                    text=label,
                    xref="paper",
                    yref="paper",
                    x=ax,
                    y=ay,
                    xanchor=xa,
                    yanchor=ya,
                    showarrow=False,
                    font={"size": 9, "color": T["text_muted"]},
                    opacity=0.85,
                )
        fig_bubble.update_layout(showlegend=False)
        fig_bubble.update_xaxes(title="Avg Days Inactive (Right = More Recent)")
        fig_bubble.update_yaxes(title="Avg Order Value (£)", tickprefix="£")
        st.plotly_chart(
            style_plotly(fig_bubble, T, height=345, bottom_margin=55, grid="both"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    # Bottom Card: Custom HTML Customer Tier Performance Table
    with st.container(border=True):
        card_header("CUSTOMER TIER PERFORMANCE", "SORTED BY TOTAL SPEND")
        tier_perf = (
            df_segments.groupby("Customer Tier", as_index=False)
            .agg(
                Customers=("Customer ID", "count"),
                Total_Spend=("Total Spend", "sum"),
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

        st.markdown(
            render_html_table(
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
            ),
            unsafe_allow_html=True,
        )


elif tab == "Customers":
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_header("RFM OVERALL SCORE DISTRIBUTION", "CUSTOMERS")
        score_dist = (
            df_segments.groupby("Overall Score", as_index=False)["Customer ID"]
            .count()
            .rename(columns={"Customer ID": "Customers"})
        )
        if not score_dist.empty:
            full_scores = list(
                range(
                    int(min(3, score_dist["Overall Score"].min())),
                    int(max(12, score_dist["Overall Score"].max())) + 1,
                )
            )
            score_dist = (
                score_dist.set_index("Overall Score")
                .reindex(full_scores, fill_value=0)
                .rename_axis("Overall Score")
                .reset_index()
            )
        total_scored = score_dist["Customers"].sum() or 1
        bar_colors = [
            T["green"] if s >= 9 else (T["amber"] if s >= 6 else T["red"])
            for s in score_dist["Overall Score"]
        ]
        fig_rfm = go.Figure(
            go.Bar(
                x=score_dist["Overall Score"],
                y=score_dist["Customers"],
                marker_color=bar_colors,
                marker_line_width=0,
                text=score_dist["Customers"],
                texttemplate="%{y:,}",
                textposition="outside",
                textfont={"size": 10, "color": T["text_secondary"]},
                cliponaxis=False,
                customdata=score_dist["Customers"] / total_scored * 100,
                hovertemplate="RFM score %{x}<br><b>%{y:,}</b> customers (%{customdata:.1f}%)<extra></extra>",
            )
        )
        if not score_dist.empty:
            fig_rfm.update_yaxes(range=[0, max(1, float(score_dist["Customers"].max())) * 1.15])
        fig_rfm.update_xaxes(dtick=1, title="Overall RFM Score (3–12) · red ≤5 · amber 6–8 · green 9+")
        fig_rfm.update_yaxes(title="Customers")
        st.plotly_chart(
            style_plotly(fig_rfm, T, height=320, bottom_margin=55, grid="y"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with c2, st.container(border=True):
        card_header("SPEND VS ORDER FREQUENCY", "TOP 1,500 CUSTOMERS")
        sample_df = df_segments.nlargest(1500, "Total Spend")
        log_x = spans_orders_of_magnitude(sample_df["Total Orders"], 30)
        log_y = spans_orders_of_magnitude(sample_df["Total Spend"], 30)
        present_tiers = set(sample_df["Customer Tier"].dropna())
        fig_sc = px.scatter(
            sample_df,
            x="Total Orders",
            y="Total Spend",
            color="Customer Tier",
            hover_data={
                "Customer ID": True,
                "Country": True,
                "Days Inactive": ":.0f",
                "Total Spend": ":,.0f",
                "Total Orders": ":,",
            },
            color_discrete_map=TIER_COLORS,
            category_orders={"Customer Tier": [n for n in tier_order if n in present_tiers]},
            opacity=0.75,
            log_x=log_x,
            log_y=log_y,
        )
        fig_sc.update_traces(marker={"size": 7, "line": {"width": 0.6, "color": T["bg_card"]}})
        fig_sc.update_yaxes(tickprefix="£", tickformat="~s", title="Total Spend (£)" + (" · log scale" if log_y else ""))
        fig_sc.update_xaxes(title="Total Orders" + (" · log scale" if log_x else ""))
        st.plotly_chart(
            style_plotly(fig_sc, T, height=320, bottom_margin=72, grid="both"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with st.container(border=True):
        card_header("TOP CUSTOMERS LEADERBOARD", "TOP 25 BY SPEND")
        top_cust = df_segments.nlargest(25, "Total Spend")
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


elif tab == "Cohorts":
    c1, c2 = st.columns([1.3, 1.0], gap="medium")

    with c1, st.container(border=True):
        card_header("COHORT RETENTION MATRIX (%)", "MONTHS SINCE FIRST PURCHASE")
        piv = df_cohort.pivot(
            index="First Purchase Month",
            columns="Months Since First Purchase",
            values="Retention Rate (%)",
        )
        later = piv.drop(columns=[0], errors="ignore")
        if later.size and later.notna().to_numpy().any():
            z_cap = float(np.nanmax(later.to_numpy(dtype=float)))
            z_cap = max(5.0, float(np.ceil(z_cap / 5.0) * 5.0))
        else:
            z_cap = 100.0
        y_labels = [v.strftime("%Y-%m") if hasattr(v, "strftime") else str(v) for v in piv.index]
        fig_hm = go.Figure(
            go.Heatmap(
                z=piv.to_numpy(dtype=float),
                x=piv.columns.tolist(),
                y=y_labels,
                zmin=0,
                zmax=z_cap,
                colorscale="Teal" if theme_name == "Light" else "Viridis",
                xgap=2,
                ygap=2,
                hoverongaps=False,
                texttemplate="%{z:.0f}",
                textfont={"size": 10},
                hovertemplate="Cohort <b>%{y}</b><br>Month +%{x}<br>Retention: <b>%{z:.1f}%</b><extra></extra>",
                colorbar={
                    "thickness": 8,
                    "len": 0.8,
                    "outlinewidth": 0,
                    "ticksuffix": "%",
                    "tickfont": {"size": 9, "color": T["text_muted"]},
                },
            )
        )
        fig_hm.update_xaxes(title="Months Since First Purchase (colour scale excludes M+0)", dtick=1, side="bottom")
        fig_hm.update_yaxes(title="Cohort Month", type="category", autorange="reversed")
        st.plotly_chart(
            style_plotly(fig_hm, T, height=390, bottom_margin=55, grid="none"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with c2, st.container(border=True):
        card_header("RETENTION DECAY CURVE", "TOP 6 COHORTS + ALL-COHORT AVG")
        top_cohorts = sorted(df_cohort["First Purchase Month"].unique())[:6]
        sub_coh = df_cohort[df_cohort["First Purchase Month"].isin(top_cohorts)]
        fig_dec = go.Figure()
        for idx, cm in enumerate(top_cohorts):
            s = sub_coh[sub_coh["First Purchase Month"] == cm].sort_values("Months Since First Purchase")
            col_hex = T["series"][idx % len(T["series"])]
            fig_dec.add_trace(
                go.Scatter(
                    x=s["Months Since First Purchase"],
                    y=s["Retention Rate (%)"],
                    name=str(cm),
                    mode="lines+markers",
                    line={"color": col_hex, "width": 2.2, "shape": "spline", "smoothing": 0.8},
                    marker={"size": 5, "color": col_hex, "line": {"width": 1.2, "color": T["bg_card"]}},
                    hovertemplate="<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>",
                )
            )
        avg_curve = (
            df_cohort.groupby("Months Since First Purchase")["Retention Rate (%)"].mean().sort_index()
        )
        fig_dec.add_trace(
            go.Scatter(
                x=avg_curve.index,
                y=avg_curve.values,
                name="All-cohort avg",
                mode="lines",
                line={"color": T["text_primary"], "width": 2.4, "dash": "dash"},
                hovertemplate="<b>All-cohort avg</b>: %{y:.1f}%<extra></extra>",
            )
        )
        fig_dec.update_layout(hovermode="x unified")
        fig_dec.update_yaxes(ticksuffix="%", title="Retention Rate", rangemode="tozero")
        fig_dec.update_xaxes(dtick=1, title="Months Since First Purchase")
        st.plotly_chart(
            style_plotly(fig_dec, T, height=390, bottom_margin=85, grid="y"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with st.container(border=True):
        card_header("COHORT PERFORMANCE SUMMARY", "M+0 TO M+3")
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


elif tab == "Bundles":
    bf = df_bundles[(df_bundles["Orders Together"] >= min_orders) & (df_bundles["Bundle Lift"] >= min_lift)].copy()
    if search_prod.strip():
        q = search_prod.strip().lower()
        bf = bf[
            bf["Product A"].str.lower().str.contains(q, na=False)
            | bf["Product B"].str.lower().str.contains(q, na=False)
        ]

    col_b1, col_b2 = st.columns(2, gap="medium")
    with col_b1, st.container(border=True):
        card_header("BUNDLE LIFT VS ORDER SHARE", "TOP 150 PAIRS")
        top_b = bf.nlargest(150, "Orders Together")
        log_x = spans_orders_of_magnitude(top_b["Order Share (%)"], 20)
        log_y = spans_orders_of_magnitude(top_b["Bundle Lift"], 20)
        fig_b = px.scatter(
            top_b,
            x="Order Share (%)",
            y="Bundle Lift",
            size="Orders Together",
            color="Buy A -> Buy B (%)",
            custom_data=["Product A", "Product B", "Orders Together", "Buy A -> Buy B (%)"],
            color_continuous_scale="Teal" if theme_name == "Light" else "Mint",
            size_max=30,
            log_x=log_x,
            log_y=log_y,
        )
        fig_b.update_traces(
            marker={"opacity": 0.85, "line": {"width": 0.8, "color": T["bg_card"]}},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>+ %{customdata[1]}<br>"
                "Orders together: %{customdata[2]:,}<br>"
                "Order share: %{x:.2f}%<br>"
                "Lift: %{y:.2f}x<br>"
                "Buy A → B: %{customdata[3]:.1f}%<extra></extra>"
            ),
        )
        fig_b.update_coloraxes(
            colorbar={
                "title": {"text": "Buy A → B", "font": {"size": 10, "color": T["text_secondary"]}},
                "thickness": 8,
                "len": 0.75,
                "outlinewidth": 0,
                "ticksuffix": "%",
                "tickfont": {"size": 9, "color": T["text_muted"]},
            }
        )
        fig_b.update_xaxes(ticksuffix="%", title="Order Share (%)" + (" · log scale" if log_x else ""))
        fig_b.update_yaxes(title="Bundle Lift (x)" + (" · log scale" if log_y else ""))
        st.plotly_chart(
            style_plotly(fig_b, T, height=380, bottom_margin=55, grid="both"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with col_b2, st.container(border=True):
        card_header("TOP 10 CO-OCCURRING BUNDLES", "ORDERS TOGETHER")
        top10_b = bf.nlargest(10, "Orders Together").sort_values("Orders Together").reset_index(drop=True)
        pair_labels = [
            f"{html.escape(str(a)[:24])}<br>+ {html.escape(str(b)[:24])}"
            for a, b in zip(top10_b["Product A"], top10_b["Product B"])
        ]
        fig_bar = go.Figure(
            go.Bar(
                x=top10_b["Orders Together"],
                y=list(range(len(top10_b))),
                orientation="h",
                marker_color=T["green"],
                marker_line_width=0,
                text=top10_b["Orders Together"],
                texttemplate="%{x:,}",
                textposition="outside",
                textfont={"size": 10, "color": T["text_secondary"]},
                cliponaxis=False,
                customdata=np.stack(
                    [top10_b["Product A"].astype(str), top10_b["Product B"].astype(str), top10_b["Bundle Lift"]],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>+ %{customdata[1]}<br>"
                    "%{x:,} orders together · lift %{customdata[2]:.2f}x<extra></extra>"
                ),
            )
        )
        fig_bar.update_yaxes(title="", tickmode="array", tickvals=list(range(len(top10_b))), ticktext=pair_labels)
        fig_bar.update_xaxes(title="Orders Together")
        if not top10_b.empty:
            fig_bar.update_xaxes(range=[0, float(top10_b["Orders Together"].max()) * 1.15])
        st.plotly_chart(
            style_plotly(fig_bar, T, height=380, bottom_margin=55, grid="x"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with st.container(border=True):
        card_header("CROSS-SELL BUNDLE PERFORMANCE", "TOP 25 MATCHING PAIRS")
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


elif tab == "Geography":
    # World Map Card: Every country in the database marked in a distinct color
    with st.container(border=True):
        card_header("GLOBAL MARKET FOOTPRINT", "EACH ACTIVE COUNTRY MARKED IN A DISTINCT COLOR")
        map_agg = (
            df_tx[df_tx["Country"] != "Not Specified"]
            .groupby("Country", as_index=False)
            .agg(
                Revenue=("Line Revenue", "sum"),
                Orders=("Invoice No", "nunique"),
                Customers=("Customer ID", "nunique"),
                Units=("Quantity", "sum"),
            )
        )
        geo_name_fix = {
            "Channel Islands": "Guernsey",
            "West Indies": "Jamaica",
        }
        map_agg["Map_Country"] = map_agg["Country"].replace(geo_name_fix)
        palette_48 = (
            px.colors.qualitative.Alphabet
            + (px.colors.qualitative.Light24 if theme_name == "Dark" else px.colors.qualitative.Dark24)
            + px.colors.qualitative.Bold
            + px.colors.qualitative.Vivid
        )
        fig_map = px.choropleth(
            map_agg,
            locations="Map_Country",
            locationmode="country names",
            color="Country",
            custom_data=["Country", "Revenue", "Orders", "Customers", "Units"],
            color_discrete_sequence=palette_48,
        )
        fig_map.update_traces(
            marker_line_color=T["bg_card"],
            marker_line_width=0.6,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Revenue: £%{customdata[1]:,.0f}<br>"
                "Orders: %{customdata[2]:,}<br>"
                "Customers: %{customdata[3]:,}<br>"
                "Units: %{customdata[4]:,}<extra></extra>"
            ),
        )
        fig_map.update_geos(
            projection_type="natural earth",
            lataxis_range=[-58, 84],
            showcountries=True,
            countrycolor=T["border_strong"],
            countrywidth=0.5,
            showcoastlines=True,
            coastlinecolor=T["border"],
            coastlinewidth=0.5,
            showland=True,
            landcolor=T["map_land"],
            showocean=True,
            oceancolor=T["map_ocean"],
            showlakes=False,
            bgcolor="rgba(0,0,0,0)",
            showframe=False,
        )
        fig_map.update_layout(
            template=T["plotly_template"],
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter, sans-serif", "color": T["text_secondary"], "size": 11},
            margin={"l": 0, "r": 0, "t": 4, "b": 4},
            showlegend=False,
            hoverlabel={
                "bgcolor": T["bg_nav"],
                "bordercolor": T["border_strong"],
                "font": {"family": "Inter, sans-serif", "color": T["text_primary"], "size": 12},
                "align": "left",
            },
        )
        st.plotly_chart(fig_map, use_container_width=True, config=PLOT_CONFIG)

    g1, g2 = st.columns(2, gap="medium")

    with g1, st.container(border=True):
        card_header("TOP COUNTRIES BY REVENUE", "MARKET DISTRIBUTION")
        geo_df = df_tx if inc_uk else df_tx[df_tx["Country"] != "United Kingdom"]
        geo_agg = (
            geo_df.groupby("Country", as_index=False)
            .agg(Revenue=("Line Revenue", "sum"), Orders=("Invoice No", "nunique"), Customers=("Customer ID", "nunique"))
            .nlargest(12, "Revenue")
            .sort_values("Revenue")
        )
        fig_geo = go.Figure(
            go.Bar(
                x=geo_agg["Revenue"],
                y=geo_agg["Country"],
                orientation="h",
                marker_color=T["sky"],
                marker_line_width=0,
                text=geo_agg["Revenue"].map(short_gbp),
                textposition="outside",
                textfont={"size": 10, "color": T["text_secondary"]},
                cliponaxis=False,
                customdata=np.stack([geo_agg["Orders"], geo_agg["Customers"]], axis=-1),
                hovertemplate=(
                    "<b>%{y}</b><br>Revenue: £%{x:,.0f}<br>"
                    "Orders: %{customdata[0]:,}<br>Customers: %{customdata[1]:,}<extra></extra>"
                ),
            )
        )
        if not geo_agg.empty:
            fig_geo.update_xaxes(range=[0, float(geo_agg["Revenue"].max()) * 1.18])
        fig_geo.update_xaxes(tickprefix="£", tickformat="~s", title="Revenue (£)")
        fig_geo.update_yaxes(title="")
        st.plotly_chart(
            style_plotly(fig_geo, T, height=340, bottom_margin=55, grid="x"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with g2, st.container(border=True):
        card_header("REVENUE BY ORDER HOUR", "24-HOUR TRAFFIC CURVE")
        hr_agg = (
            df_tx.groupby("Order Hour", as_index=False)
            .agg(Revenue=("Line Revenue", "sum"), Orders=("Invoice No", "nunique"))
            .sort_values("Order Hour")
        )
        fig_hr = go.Figure(
            go.Scatter(
                x=hr_agg["Order Hour"],
                y=hr_agg["Revenue"],
                mode="lines+markers",
                line={"color": T["amber"], "width": 2.6, "shape": "spline", "smoothing": 0.8},
                fill="tozeroy",
                fillcolor=hex_to_rgba(T["amber"], 0.14),
                marker={"size": 6, "color": T["amber"], "line": {"width": 1.5, "color": T["bg_card"]}},
                customdata=hr_agg["Orders"],
                hovertemplate="<b>%{x}:00</b><br>Revenue: £%{y:,.0f}<br>Orders: %{customdata:,}<extra></extra>",
            )
        )
        if not hr_agg.empty:
            peak = hr_agg.loc[hr_agg["Revenue"].idxmax()]
            fig_hr.add_trace(
                go.Scatter(
                    x=[peak["Order Hour"]],
                    y=[peak["Revenue"]],
                    mode="markers+text",
                    marker={"size": 12, "color": T["amber"], "line": {"width": 2.5, "color": T["bg_card"]}},
                    text=[f"Peak {int(peak['Order Hour'])}:00 · {short_gbp(peak['Revenue'])}"],
                    textposition="top center",
                    textfont={"size": 10, "color": T["text_primary"]},
                    cliponaxis=False,
                    hoverinfo="skip",
                )
            )
            fig_hr.update_xaxes(range=[hr_agg["Order Hour"].min() - 0.6, hr_agg["Order Hour"].max() + 0.6])
            fig_hr.update_yaxes(range=[0, float(hr_agg["Revenue"].max()) * 1.2])
        fig_hr.update_layout(showlegend=False)
        fig_hr.update_xaxes(dtick=3, ticksuffix=":00", title="Hour of Day (24h)")
        fig_hr.update_yaxes(tickprefix="£", tickformat="~s", title="Revenue (£)")
        st.plotly_chart(
            style_plotly(fig_hr, T, height=340, bottom_margin=55, grid="y"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with st.container(border=True):
        card_header("COUNTRY PERFORMANCE BREAKDOWN", "TOP 15 MARKETS")
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