"""
Consumer-360 | Lightweight Business Intelligence & Retail Analytics Platform
Ultra-fast portable Streamlit app with SQL-side aggregation, lazy tab loading,
automatic Supabase -> Local PostgreSQL -> Local CSV fallback, Dark & Light UI themes,
responsive desktop/mobile layout, distinct-color world map, and custom HTML tables.
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
# 1. PAGE CONFIG (auto sidebar = expanded on desktop, collapsed on mobile)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consumer-360 | Business Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto",
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
# 3. THEME DEFINITIONS (DARK & LIGHT — PRESERVED PALETTE)
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
    st.session_state.active_tab = "Executive Overview"
if "show_export_panel" not in st.session_state:
    st.session_state.show_export_panel = False


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
            padding-top: 0.9rem !important;
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

        /* Brand & Topbar */
        .c360-brand-row {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
            flex-wrap: wrap;
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
        .c360-live-pill {{
            background: {t['green_soft']};
            color: {t['green']};
            border: 1px solid {t['border']};
            font-size: 0.70rem;
            font-weight: 600;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
        }}

        /* Sleek Pill Navigation */
        div[data-testid="stRadio"] > div[role="radiogroup"] {{
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 0.4rem !important;
            align-items: center;
        }}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
            background: {t['bg_pill']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 8px !important;
            padding: 0.36rem 0.85rem !important;
            margin: 0 !important;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
            border-color: {t['accent']} !important;
        }}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"],
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {{
            background: {t['accent_soft']} !important;
            border: 1px solid {t['accent']} !important;
        }}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {{
            display: none !important;
        }}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label p {{
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: {t['text_primary']} !important;
            margin: 0 !important;
        }}

        /* Executive BI Insight Strip */
        .c360-insight {{
            display: flex;
            align-items: center;
            gap: 0.65rem;
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-left: 3px solid {t['accent']};
            border-radius: 10px;
            padding: 0.68rem 1rem;
            margin-bottom: 0.9rem;
            font-size: 0.83rem;
            color: {t['text_secondary']};
            line-height: 1.45;
        }}
        .c360-insight strong {{
            color: {t['text_primary']};
            font-weight: 600;
        }}
        .c360-insight-tag {{
            background: {t['accent_soft']};
            color: {t['accent']};
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            padding: 0.18rem 0.5rem;
            border-radius: 5px;
            white-space: nowrap;
        }}

        /* Active Filter Banner */
        .c360-filter-bar {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
            background: {t['accent_soft']};
            border: 1px solid {t['border_strong']};
            border-radius: 10px;
            padding: 0.5rem 0.85rem;
            margin-bottom: 0.85rem;
            font-size: 0.76rem;
            color: {t['text_primary']};
        }}
        .c360-filter-chip {{
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 999px;
            padding: 0.15rem 0.55rem;
            font-size: 0.72rem;
            font-weight: 600;
            color: {t['text_secondary']};
        }}

        .c360-card-header {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_secondary']};
            margin-bottom: 0.45rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .c360-card-sub {{
            font-size: 0.68rem;
            font-weight: 600;
            color: {t['text_muted']};
        }}

        /* Responsive KPI Grid */
        .c360-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 0.25rem;
            margin-bottom: 0.9rem;
        }}
        .c360-kpi-grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin-bottom: 0.75rem;
        }}
        .c360-kpi {{
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 0.95rem 1.05rem;
            box-shadow: {t['shadow']};
        }}
        .c360-kpi-label {{
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['text_muted']};
            margin-bottom: 0.32rem;
        }}
        .c360-kpi-val {{
            font-size: 1.45rem;
            font-weight: 700;
            color: {t['text_primary']};
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }}
        .c360-kpi-sub {{
            font-size: 0.73rem;
            color: {t['text_secondary']};
            margin-top: 0.28rem;
        }}

        /* Custom SaaS Performance Table */
        .c360-table-wrap {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
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
            padding: 0.75rem 0.85rem;
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
            height: 7px;
            border-radius: 999px;
            background: {t['border']};
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 0.45rem;
            text-align: left;
        }}
        .c360-bar-fill {{
            display: block;
            height: 100%;
            border-radius: 999px;
        }}

        /* Empty State & App Footer */
        .c360-empty {{
            text-align: center;
            padding: 2.2rem 1rem;
            color: {t['text_secondary']};
            font-size: 0.9rem;
        }}
        .c360-footer {{
            margin-top: 1.5rem;
            padding-top: 0.85rem;
            border-top: 1px solid {t['border']};
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
            font-size: 0.73rem;
            color: {t['text_muted']};
        }}

        /* Buttons */
        .stButton > button {{
            background: {t['bg_card']};
            color: {t['text_secondary']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            font-size: 0.80rem;
            font-weight: 500;
            padding: 0.36rem 0.65rem;
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

        /* Tablet breakpoint */
        @media (max-width: 1199px) {{
            .c360-kpi-grid {{
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }}
            .c360-kpi-grid-4 {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .block-container {{
                padding-left: 1.1rem !important;
                padding-right: 1.1rem !important;
            }}
        }}

        /* Mobile breakpoint */
        @media (max-width: 767px) {{
            .block-container {{
                padding-top: 0.55rem !important;
                padding-left: 0.65rem !important;
                padding-right: 0.65rem !important;
            }}
            div[data-testid="stVerticalBlockBorderWrapper"] {{
                padding: 0.78rem 0.85rem !important;
                border-radius: 10px !important;
            }}
            .c360-kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.6rem;
            }}
            .c360-kpi-grid > .c360-kpi:last-child:nth-child(odd) {{
                grid-column: 1 / -1;
            }}
            .c360-kpi-val {{
                font-size: 1.22rem;
            }}
            .c360-logo {{
                font-size: 1.02rem;
            }}
            .c360-insight {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.35rem;
                font-size: 0.79rem;
            }}
            div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
                padding: 0.3rem 0.65rem !important;
            }}
            div[data-testid="stRadio"] > div[role="radiogroup"] > label p {{
                font-size: 0.75rem !important;
            }}
            table.c360-table {{
                font-size: 0.78rem;
            }}
            table.c360-table thead th,
            table.c360-table tbody td {{
                padding: 0.58rem 0.65rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 5. LIGHTWEIGHT DATA ENGINE (SQL-SIDE AGGREGATION + LAZY TAB LOADING)
# -----------------------------------------------------------------------------
def build_pg_uri(host: str, port: str, db: str, user: str, password: str, sslmode: str) -> str:
    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}?sslmode={sslmode}"
    )


@st.cache_resource(show_spinner=False)
def get_db_engine():
    """Return a cached SQLAlchemy engine (Supabase -> Local PG), or None for CSV fallback."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    candidates: list[tuple[str, str]] = []
    supa_host = get_config("SUPABASE_DB_HOST", ENV_MAP)
    supa_user = get_config("SUPABASE_DB_USER", ENV_MAP)
    supa_pass = get_config("SUPABASE_DB_PASSWORD", ENV_MAP)
    if supa_host and supa_user and supa_pass:
        candidates.append(
            (
                build_pg_uri(
                    supa_host,
                    get_config("SUPABASE_DB_PORT", ENV_MAP, "5432"),
                    get_config("SUPABASE_DB_NAME", ENV_MAP, "postgres"),
                    supa_user,
                    supa_pass,
                    "require",
                ),
                "supabase",
            )
        )

    pg_host = get_config("PG_HOST", ENV_MAP, "localhost")
    pg_user = get_config("PG_USER", ENV_MAP, "postgres")
    pg_pass = get_config("PG_PASSWORD", ENV_MAP)
    if pg_host and pg_user and pg_pass:
        candidates.append(
            (
                build_pg_uri(
                    pg_host,
                    get_config("PG_PORT", ENV_MAP, "5432"),
                    get_config("PG_DB", ENV_MAP, "retail_analytics"),
                    pg_user,
                    pg_pass,
                    "prefer",
                ),
                "local",
            )
        )

    for uri, _label in candidates:
        try:
            engine = create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 5})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except (SQLAlchemyError, OSError):
            continue
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def load_core_bi_data() -> dict[str, pd.DataFrame]:
    """
    Ultra-lightweight startup loader (~7,000 rows total instead of ~460,000 rows).
    Aggregates retail_transactions in SQL so cold starts finish in seconds with minimal RAM.
    """
    engine = get_db_engine()
    if engine is not None:
        sql_summary = """
            SELECT
                t."Year-Month",
                t."Country",
                COALESCE(s."Customer Tier", 'Other') AS "Customer Tier",
                COALESCE(s."Buyer Group", 'Other') AS "Buyer Group",
                SUM(t."Line Revenue") AS "Revenue",
                COUNT(DISTINCT t."Invoice No") AS "Orders",
                COUNT(DISTINCT t."Customer ID") AS "Customers",
                SUM(t."Quantity") AS "Units",
                COUNT(*) AS "Lines"
            FROM public.retail_transactions t
            LEFT JOIN public.customer_segments s ON t."Customer ID" = s."Customer ID"
            GROUP BY 1, 2, 3, 4
        """
        sql_timing = """
            SELECT
                t."Year-Month",
                t."Country",
                COALESCE(s."Customer Tier", 'Other') AS "Customer Tier",
                COALESCE(s."Buyer Group", 'Other') AS "Buyer Group",
                TO_CHAR(t."Order Date", 'FMDay') AS "Weekday",
                t."Order Hour",
                SUM(t."Line Revenue") AS "Revenue"
            FROM public.retail_transactions t
            LEFT JOIN public.customer_segments s ON t."Customer ID" = s."Customer ID"
            WHERE t."Order Date" IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6
        """
        with engine.connect() as conn:
            return {
                "cohort_retention": pd.read_sql("SELECT * FROM public.cohort_retention", conn),
                "customer_segments": pd.read_sql("SELECT * FROM public.customer_segments", conn),
                "tx_summary": pd.read_sql(sql_summary, conn),
                "tx_timing": pd.read_sql(sql_timing, conn),
            }

    # Portable CSV fallback (aggregates once in cache, then discards 400k-row raw table)
    if not DEFAULT_DATA_DIR.exists():
        raise FileNotFoundError(
            "Unable to connect to database and data/supabase_db CSVs were not found."
        )
    df_cohort = pd.read_csv(DEFAULT_DATA_DIR / "cohort_retention.csv")
    df_seg = pd.read_csv(DEFAULT_DATA_DIR / "customer_segments.csv")
    tx = pd.read_csv(
        DEFAULT_DATA_DIR / "retail_transactions.csv",
        usecols=[
            "Invoice No",
            "Quantity",
            "Customer ID",
            "Country",
            "Order Date",
            "Line Revenue",
            "Year-Month",
            "Order Hour",
        ],
    )
    tx = tx.merge(df_seg[["Customer ID", "Customer Tier", "Buyer Group"]], on="Customer ID", how="left")
    tx["Customer Tier"] = tx["Customer Tier"].fillna("Other")
    tx["Buyer Group"] = tx["Buyer Group"].fillna("Other")

    tx_summary = (
        tx.groupby(["Year-Month", "Country", "Customer Tier", "Buyer Group"], as_index=False)
        .agg(
            Revenue=("Line Revenue", "sum"),
            Orders=("Invoice No", "nunique"),
            Customers=("Customer ID", "nunique"),
            Units=("Quantity", "sum"),
            Lines=("Line Revenue", "size"),
        )
    )
    dt = pd.to_datetime(tx["Order Date"], errors="coerce")
    tx["Weekday"] = dt.dt.day_name()
    tx_timing = (
        tx.dropna(subset=["Weekday"])
        .groupby(["Year-Month", "Country", "Customer Tier", "Buyer Group", "Weekday", "Order Hour"], as_index=False)
        .agg(Revenue=("Line Revenue", "sum"))
    )
    return {
        "cohort_retention": df_cohort,
        "customer_segments": df_seg,
        "tx_summary": tx_summary,
        "tx_timing": tx_timing,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_bundles_data() -> pd.DataFrame:
    """Lazy-loaded only when the Merchandising & Bundles tab or Export panel is opened."""
    engine = get_db_engine()
    if engine is not None:
        sql = """
            SELECT *
            FROM public.product_bundles
            ORDER BY "Orders Together" DESC
            LIMIT 8000
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)
    return pd.read_csv(DEFAULT_DATA_DIR / "product_bundles.csv").nlargest(8000, "Orders Together")


@st.cache_data(ttl=600, show_spinner=False)
def load_customer_top_products(customer_id: int, month_start: str, month_end: str) -> tuple[list[str], int]:
    """On-demand 3-row query for the selected Customer 360 account."""
    from sqlalchemy import text

    engine = get_db_engine()
    if engine is not None:
        sql = text(
            """
            SELECT "Product Name", SUM("Line Revenue") AS rev, COUNT(*) AS cnt
            FROM public.retail_transactions
            WHERE "Customer ID" = :cid
              AND "Year-Month" BETWEEN :m_start AND :m_end
            GROUP BY "Product Name"
            ORDER BY rev DESC
            LIMIT 3
            """
        )
        sql_cnt = text(
            """
            SELECT COUNT(*) FROM public.retail_transactions
            WHERE "Customer ID" = :cid
              AND "Year-Month" BETWEEN :m_start AND :m_end
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(sql, {"cid": customer_id, "m_start": month_start, "m_end": month_end}).fetchall()
            total_items = int(
                conn.execute(sql_cnt, {"cid": customer_id, "m_start": month_start, "m_end": month_end}).scalar() or 0
            )
        return [str(r[0]) for r in rows], total_items

    fpath = DEFAULT_DATA_DIR / "retail_transactions.csv"
    if not fpath.exists():
        return [], 0
    tx = pd.read_csv(fpath, usecols=["Customer ID", "Product Name", "Line Revenue", "Year-Month"])
    sub = tx[
        (tx["Customer ID"] == customer_id)
        & (tx["Year-Month"] >= month_start)
        & (tx["Year-Month"] <= month_end)
    ]
    top = sub.groupby("Product Name")["Line Revenue"].sum().nlargest(3).index.tolist()
    return [str(p) for p in top], len(sub)


# -----------------------------------------------------------------------------
# 6. PLOTLY & BI PRESENTATION HELPERS
# -----------------------------------------------------------------------------
PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


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


def style_plotly(
    fig: go.Figure,
    t: dict[str, str],
    height: int = 340,
    bottom_margin: int = 64,
    grid: str = "y",
) -> go.Figure:
    font_family = "Inter, sans-serif"
    fig.update_layout(
        template=t["plotly_template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": font_family, "color": t["text_secondary"], "size": 11},
        margin={"l": 12, "r": 12, "t": 12, "b": bottom_margin},
        bargap=0.28,
        legend_title_text="",
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
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


def render_insight(tag: str, body_html: str) -> None:
    st.markdown(
        f'<div class="c360-insight"><span class="c360-insight-tag">{html.escape(tag)}</span><span>{body_html}</span></div>',
        unsafe_allow_html=True,
    )


def render_empty_state(message: str = "No records match the current sidebar filters.") -> None:
    st.markdown(
        f'<div class="c360-empty">No data to display — {html.escape(message)} Try resetting filters in the sidebar.</div>',
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
# 7. LOAD CORE BI DATA & APPLY THEME
# -----------------------------------------------------------------------------
theme_name = st.session_state.ui_theme
T = THEMES[theme_name]
inject_css(T)

try:
    with st.spinner("Loading Consumer-360 analytics..."):
        core = load_core_bi_data()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

df_cohort = core["cohort_retention"]
df_segments_raw = core["customer_segments"]
df_tx_sum_raw = core["tx_summary"]
df_tx_time_raw = core["tx_timing"]


# -----------------------------------------------------------------------------
# 8. SIDEBAR BI SLICERS
# -----------------------------------------------------------------------------
all_months = sorted(df_tx_sum_raw["Year-Month"].dropna().unique().tolist())
tiers = sorted(df_segments_raw["Customer Tier"].dropna().unique().tolist())
groups = sorted(df_segments_raw["Buyer Group"].dropna().unique().tolist())
countries = sorted(df_segments_raw["Country"].dropna().unique().tolist())


def reset_filters() -> None:
    st.session_state.flt_months = (all_months[0], all_months[-1])
    st.session_state.flt_tiers = []
    st.session_state.flt_groups = []
    st.session_state.flt_countries = []
    st.session_state.flt_prod = ""
    st.session_state.flt_min_orders = 50
    st.session_state.flt_min_lift = 2.0
    st.session_state.flt_inc_uk = False


with st.sidebar:
    st.markdown("### ⚡ Analytics Filters")
    st.caption(f"Reporting Window: {all_months[0]} to {all_months[-1]}")

    sel_months = st.select_slider(
        "Order Month Range",
        options=all_months,
        value=st.session_state.get("flt_months", (all_months[0], all_months[-1])),
        key="flt_months",
    )
    sel_tiers = st.multiselect("Customer Tier", tiers, key="flt_tiers")
    sel_groups = st.multiselect("Buyer Group", groups, key="flt_groups")
    sel_countries = st.multiselect("Market / Country", countries, key="flt_countries")

    st.markdown("---")
    st.markdown("**Merchandising & Bundles**")
    search_prod = st.text_input(
        "Search Product Name",
        placeholder="e.g., Heart, Cake, Lantern...",
        key="flt_prod",
    )
    min_orders = st.slider("Min Orders Together", 10, 500, 50, step=10, key="flt_min_orders")
    min_lift = st.slider("Min Bundle Lift (x)", 1.0, 20.0, 2.0, step=0.5, key="flt_min_lift")

    st.markdown("---")
    st.markdown("**Market Comparison**")
    inc_uk = st.checkbox("Include UK in Market Bar Chart", value=False, key="flt_inc_uk")

    st.markdown("---")
    st.button("Reset All Filters", on_click=reset_filters, use_container_width=True)

# Fast boolean mask filtering on compact aggregates
seg_mask = pd.Series(True, index=df_segments_raw.index)
if sel_tiers:
    seg_mask &= df_segments_raw["Customer Tier"].isin(sel_tiers)
if sel_groups:
    seg_mask &= df_segments_raw["Buyer Group"].isin(sel_groups)
if sel_countries:
    seg_mask &= df_segments_raw["Country"].isin(sel_countries)
df_segments = df_segments_raw.loc[seg_mask]

sum_mask = (df_tx_sum_raw["Year-Month"] >= sel_months[0]) & (df_tx_sum_raw["Year-Month"] <= sel_months[1])
if sel_tiers:
    sum_mask &= df_tx_sum_raw["Customer Tier"].isin(sel_tiers)
if sel_groups:
    sum_mask &= df_tx_sum_raw["Buyer Group"].isin(sel_groups)
if sel_countries:
    sum_mask &= df_tx_sum_raw["Country"].isin(sel_countries)
df_tx_sum = df_tx_sum_raw.loc[sum_mask]

time_mask = (df_tx_time_raw["Year-Month"] >= sel_months[0]) & (df_tx_time_raw["Year-Month"] <= sel_months[1])
if sel_tiers:
    time_mask &= df_tx_time_raw["Customer Tier"].isin(sel_tiers)
if sel_groups:
    time_mask &= df_tx_time_raw["Buyer Group"].isin(sel_groups)
if sel_countries:
    time_mask &= df_tx_time_raw["Country"].isin(sel_countries)
df_tx_time = df_tx_time_raw.loc[time_mask]

tier_order = (
    df_segments_raw.groupby("Customer Tier")["Total Spend"].sum().sort_values(ascending=False).index.tolist()
)
TIER_COLORS = {n: T["series"][i % len(T["series"])] for i, n in enumerate(tier_order)}


# -----------------------------------------------------------------------------
# 9. RESPONSIVE TOP NAVIGATION BAR
# -----------------------------------------------------------------------------
nav_tabs = [
    "Executive Overview",
    "Customer Intelligence",
    "Retention & Cohorts",
    "Merchandising & Bundles",
    "Markets & Timing",
]

with st.container(border=True):
    hdr_left, hdr_right = st.columns([3.5, 1.5], vertical_alignment="center")
    with hdr_left:
        st.markdown(
            f"""
            <div class="c360-brand-row">
                <span class="c360-logo">⚡ Consumer-360</span>
                <span class="c360-badge">Business Intelligence</span>
                <span class="c360-live-pill">● {html.escape(sel_months[0])} – {html.escape(sel_months[1])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_right:
        a1, a2 = st.columns(2)
        exp_btn_type = "primary" if st.session_state.show_export_panel else "secondary"
        if a1.button("Export Data", key="btn_export_data", type=exp_btn_type, use_container_width=True):
            st.session_state.show_export_panel = not st.session_state.show_export_panel
            st.rerun()
        theme_label = "☀ Light" if theme_name == "Dark" else "🌙 Dark"
        if a2.button(theme_label, key="btn_theme_toggle", use_container_width=True):
            st.session_state.ui_theme = "Light" if theme_name == "Dark" else "Dark"
            st.rerun()

    selected_tab = st.radio(
        "Navigation",
        nav_tabs,
        index=nav_tabs.index(st.session_state.active_tab),
        horizontal=True,
        label_visibility="collapsed",
    )
    if selected_tab != st.session_state.active_tab:
        st.session_state.active_tab = selected_tab
        st.session_state.show_export_panel = False
        st.rerun()

# Active filter summary banner
active_chips: list[str] = []
if sel_months != (all_months[0], all_months[-1]):
    active_chips.append(f"Period: {sel_months[0]} → {sel_months[1]}")
if sel_tiers:
    active_chips.append(f"Tiers: {', '.join(sel_tiers[:3])}" + ("…" if len(sel_tiers) > 3 else ""))
if sel_groups:
    active_chips.append(f"Groups: {', '.join(sel_groups[:2])}" + ("…" if len(sel_groups) > 2 else ""))
if sel_countries:
    active_chips.append(f"Markets: {', '.join(sel_countries[:3])}" + ("…" if len(sel_countries) > 3 else ""))

if active_chips:
    chips_html = "".join(f'<span class="c360-filter-chip">{html.escape(c)}</span>' for c in active_chips)
    st.markdown(
        f'<div class="c360-filter-bar"><strong>Active Scope:</strong> {chips_html}</div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 10. BI DATA EXPORT PANEL (LAZY-LOADED ON DEMAND)
# -----------------------------------------------------------------------------
if st.session_state.show_export_panel:
    with st.container(border=True):
        card_header("BI DATASET PREVIEW & CSV EXPORT", "FILTERED ANALYTICAL VIEWS")
        e1, e2, e3 = st.columns([2, 2, 1])
        chosen_label = e1.selectbox(
            "Dataset",
            ["Customer Segments", "Monthly Revenue Summary", "Cohort Retention", "Product Bundles (Top 8k)"],
        )
        row_limit = e2.slider("Preview Rows", min_value=50, max_value=2000, value=250, step=50)
        if chosen_label == "Customer Segments":
            exp_df, fname = df_segments, "customer_segments.csv"
        elif chosen_label == "Monthly Revenue Summary":
            exp_df, fname = df_tx_sum, "monthly_revenue_summary.csv"
        elif chosen_label == "Cohort Retention":
            exp_df, fname = df_cohort, "cohort_retention.csv"
        else:
            exp_df, fname = load_bundles_data(), "product_bundles.csv"

        e3.download_button(
            "Download CSV",
            data=exp_df.head(row_limit).to_csv(index=False).encode("utf-8"),
            file_name=fname,
            mime="text/csv",
            use_container_width=True,
        )
        st.dataframe(exp_df.head(row_limit), use_container_width=True, height=380)


# -----------------------------------------------------------------------------
# 11. BI ANALYTICS VIEWS
# -----------------------------------------------------------------------------
tab = st.session_state.active_tab

if tab == "Executive Overview":
    total_rev = float(df_tx_sum["Revenue"].sum())
    total_orders = int(df_tx_sum["Orders"].sum())
    total_lines = int(df_tx_sum["Lines"].sum())
    total_customers = int(df_segments["Customer ID"].nunique())
    aov = total_rev / total_orders if total_orders else 0.0
    arpu = total_rev / total_customers if total_customers else 0.0
    repeat_pct = (
        float((df_segments["Total Orders"] > 1).mean() * 100) if not df_segments.empty else 0.0
    )
    risk_mask = df_segments["Days Inactive"] > 45
    rev_at_risk = float(df_segments.loc[risk_mask, "Total Spend"].sum())
    tot_seg_spend = float(df_segments["Total Spend"].sum()) or 1.0
    risk_share = rev_at_risk / tot_seg_spend * 100

    st.markdown(
        f"""
        <div class="c360-kpi-grid">
            <div class="c360-kpi">
                <div class="c360-kpi-label">Total Revenue</div>
                <div class="c360-kpi-val">{fmt_currency(total_rev)}</div>
                <div class="c360-kpi-sub">{total_orders:,} orders · {total_lines:,} line items</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Active Customers</div>
                <div class="c360-kpi-val">{total_customers:,}</div>
                <div class="c360-kpi-sub">{repeat_pct:.1f}% repeat buyers</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Revenue / Customer</div>
                <div class="c360-kpi-val">{fmt_currency(arpu)}</div>
                <div class="c360-kpi-sub">Avg {total_orders / max(total_customers, 1):.1f} orders / buyer</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Avg Order Value</div>
                <div class="c360-kpi-val">{fmt_currency(aov)}</div>
                <div class="c360-kpi-sub">Per unique invoice</div>
            </div>
            <div class="c360-kpi">
                <div class="c360-kpi-label">Revenue at Risk</div>
                <div class="c360-kpi-val">{fmt_currency(rev_at_risk)}</div>
                <div class="c360-kpi-sub">{risk_share:.1f}% of lifetime spend (&gt;45d inactive)</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df_tx_sum.empty or df_segments.empty:
        render_empty_state()
    else:
        top_tier_agg = (
            df_segments.groupby("Customer Tier", as_index=False)
            .agg(Customers=("Customer ID", "count"), Spend=("Total Spend", "sum"))
            .sort_values("Spend", ascending=False)
        )
        lead_tier = top_tier_agg.iloc[0]
        lead_c_pct = lead_tier["Customers"] / max(total_customers, 1) * 100
        lead_r_pct = lead_tier["Spend"] / tot_seg_spend * 100
        render_insight(
            "Executive Summary",
            f"<strong>{html.escape(str(lead_tier['Customer Tier']))}</strong> represent "
            f"<strong>{lead_c_pct:.1f}%</strong> of the customer base yet generate "
            f"<strong>{lead_r_pct:.1f}%</strong> of lifetime spend ({fmt_currency(float(lead_tier['Spend']))}). "
            f"Meanwhile, <strong>{fmt_currency(rev_at_risk)}</strong> ({risk_share:.1f}%) sits in accounts inactive for over 45 days.",
        )

        col_left, col_right = st.columns([1.25, 1.0], gap="medium")

        with col_left, st.container(border=True):
            card_header("MONTHLY REVENUE & ORDER VOLUME", "EXECUTIVE TRAJECTORY")
            view_mode = st.selectbox(
                "Trend View",
                ["Total Revenue & Orders", "Stacked Revenue by Customer Tier"],
                label_visibility="collapsed",
            )
            if view_mode == "Total Revenue & Orders":
                monthly_agg = (
                    df_tx_sum.groupby("Year-Month", as_index=False)
                    .agg(Revenue=("Revenue", "sum"), Orders=("Orders", "sum"))
                    .sort_values("Year-Month")
                )
                monthly_agg["MoM %"] = monthly_agg["Revenue"].pct_change() * 100
                fig_rev = go.Figure()
                fig_rev.add_trace(
                    go.Bar(
                        x=monthly_agg["Year-Month"],
                        y=monthly_agg["Revenue"],
                        name="Revenue (£)",
                        marker_color=hex_to_rgba(T["accent"], 0.82),
                        customdata=monthly_agg["MoM %"].fillna(0),
                        hovertemplate="<b>%{x}</b><br>Revenue: £%{y:,.0f}<br>MoM: %{customdata:+.1f}%<extra></extra>",
                    )
                )
                fig_rev.add_trace(
                    go.Scatter(
                        x=monthly_agg["Year-Month"],
                        y=monthly_agg["Orders"],
                        name="Unique Orders",
                        yaxis="y2",
                        mode="lines+markers",
                        line={"color": T["green"], "width": 2.6, "shape": "spline", "smoothing": 0.7},
                        marker={"size": 6, "color": T["green"], "line": {"width": 1.5, "color": T["bg_card"]}},
                        hovertemplate="Orders: %{y:,}<extra></extra>",
                    )
                )
                style_plotly(fig_rev, T, height=340, bottom_margin=72, grid="y")
                fig_rev.update_layout(
                    hovermode="x unified",
                    yaxis={
                        "tickprefix": "£",
                        "tickformat": "~s",
                        "title": "Revenue (£)",
                        "rangemode": "tozero",
                    },
                    yaxis2={
                        "title": "Orders",
                        "overlaying": "y",
                        "side": "right",
                        "showgrid": False,
                        "zeroline": False,
                        "tickfont": {"size": 10, "color": T["text_muted"]},
                        "title_font": {"size": 11, "color": T["text_secondary"]},
                        "rangemode": "tozero",
                    },
                )
                fig_rev.update_xaxes(title="", tickangle=-25)
                st.plotly_chart(fig_rev, use_container_width=True, config=PLOT_CONFIG)
            else:
                monthly_tier = (
                    df_tx_sum.groupby(["Year-Month", "Customer Tier"], as_index=False)["Revenue"]
                    .sum()
                    .sort_values("Year-Month")
                )
                fig_stack = go.Figure()
                for tier_name in tier_order:
                    sub = monthly_tier[monthly_tier["Customer Tier"] == tier_name]
                    if sub.empty:
                        continue
                    col_hex = TIER_COLORS.get(tier_name, T["series"][0])
                    fig_stack.add_trace(
                        go.Scatter(
                            x=sub["Year-Month"],
                            y=sub["Revenue"],
                            name=tier_name,
                            mode="lines",
                            stackgroup="one",
                            line={"color": col_hex, "width": 1.6, "shape": "spline", "smoothing": 0.6},
                            fillcolor=hex_to_rgba(col_hex, 0.45),
                            hovertemplate="<b>%{fullData.name}</b>: £%{y:,.0f}<extra></extra>",
                        )
                    )
                fig_stack.update_layout(hovermode="x unified")
                fig_stack.update_yaxes(tickprefix="£", tickformat="~s", title="Revenue (£)", rangemode="tozero")
                fig_stack.update_xaxes(title="", tickangle=-25)
                st.plotly_chart(
                    style_plotly(fig_stack, T, height=340, bottom_margin=78, grid="y"),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

        with col_right, st.container(border=True):
            card_header("REVENUE VS CUSTOMER CONCENTRATION", "PARETO SHARE BY TIER (%)")
            tier_conc = top_tier_agg.sort_values("Spend", ascending=True).copy()
            tot_c = tier_conc["Customers"].sum() or 1
            tier_conc["Customer Share (%)"] = tier_conc["Customers"] / tot_c * 100
            tier_conc["Revenue Share (%)"] = tier_conc["Spend"] / tot_seg_spend * 100

            fig_conc = go.Figure()
            fig_conc.add_trace(
                go.Bar(
                    y=tier_conc["Customer Tier"],
                    x=tier_conc["Customer Share (%)"],
                    name="% of Customers",
                    orientation="h",
                    marker_color=hex_to_rgba(T["sky"], 0.78),
                    text=tier_conc["Customer Share (%)"].map(lambda v: f"{v:.1f}%"),
                    textposition="outside",
                    textfont={"size": 10, "color": T["text_muted"]},
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Customer Share: %{x:.1f}%<extra></extra>",
                )
            )
            fig_conc.add_trace(
                go.Bar(
                    y=tier_conc["Customer Tier"],
                    x=tier_conc["Revenue Share (%)"],
                    name="% of Revenue",
                    orientation="h",
                    marker_color=T["green"],
                    text=tier_conc["Revenue Share (%)"].map(lambda v: f"{v:.1f}%"),
                    textposition="outside",
                    textfont={"size": 10, "color": T["text_primary"]},
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Revenue Share: %{x:.1f}%<extra></extra>",
                )
            )
            max_share = max(
                float(tier_conc["Customer Share (%)"].max()),
                float(tier_conc["Revenue Share (%)"].max()),
                10.0,
            )
            fig_conc.update_layout(barmode="group")
            fig_conc.update_xaxes(ticksuffix="%", range=[0, max_share * 1.24], title="Share of Total (%)")
            fig_conc.update_yaxes(title="")
            st.plotly_chart(
                style_plotly(fig_conc, T, height=378, bottom_margin=64, grid="x"),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

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


elif tab == "Customer Intelligence":
    if df_segments.empty:
        render_empty_state()
    else:
        avg_rfm = float(df_segments["Overall Score"].mean())
        high_val_pct = float((df_segments["Overall Score"] >= 9).mean() * 100)
        median_inactive = float(df_segments["Days Inactive"].median())
        render_insight(
            "Segmentation Insight",
            f"Average RFM score is <strong>{avg_rfm:.1f} / 12</strong> with "
            f"<strong>{high_val_pct:.1f}%</strong> of customers in the high-value band (9–12) and a median inactivity window of "
            f"<strong>{median_inactive:.0f} days</strong>.",
        )

        with st.container(border=True):
            card_header("CUSTOMER 360 ACCOUNT LOOKUP", "INDIVIDUAL BUYER PROFILE")
            top_ids = df_segments.nlargest(200, "Total Spend")["Customer ID"].astype(int).tolist()
            sel_cid = st.selectbox(
                "Select Account (Top 200 by Spend in current scope)",
                options=top_ids,
                format_func=lambda cid: f"Account #{cid}",
            )
            cust_row = df_segments[df_segments["Customer ID"] == sel_cid].iloc[0]
            top_prods, item_count = load_customer_top_products(int(sel_cid), sel_months[0], sel_months[1])
            fav_text = ", ".join(p[:28] for p in top_prods) if top_prods else "No orders in selected period"

            st.markdown(
                f"""
                <div class="c360-kpi-grid-4">
                    <div class="c360-kpi">
                        <div class="c360-kpi-label">Lifetime Value</div>
                        <div class="c360-kpi-val">{fmt_currency(float(cust_row['Total Spend']))}</div>
                        <div class="c360-kpi-sub">{int(cust_row['Total Orders']):,} orders · AOV {fmt_currency(float(cust_row['Avg Order Value']))}</div>
                    </div>
                    <div class="c360-kpi">
                        <div class="c360-kpi-label">Tier & Buyer Group</div>
                        <div class="c360-kpi-val" style="font-size:1.1rem;">{html.escape(str(cust_row['Customer Tier']))}</div>
                        <div class="c360-kpi-sub">{html.escape(str(cust_row['Buyer Group']))}</div>
                    </div>
                    <div class="c360-kpi">
                        <div class="c360-kpi-label">RFM & Recency</div>
                        <div class="c360-kpi-val">{int(cust_row['Overall Score'])} / 12</div>
                        <div class="c360-kpi-sub">{int(cust_row['Days Inactive'])} days inactive · {html.escape(str(cust_row['Country']))}</div>
                    </div>
                    <div class="c360-kpi">
                        <div class="c360-kpi-label">Top Purchased Items</div>
                        <div class="c360-kpi-val" style="font-size:0.86rem;line-height:1.35;">{html.escape(fav_text)}</div>
                        <div class="c360-kpi-sub">{item_count:,} line items in window</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        c1, c2 = st.columns(2, gap="medium")

        with c1, st.container(border=True):
            card_header("CUSTOMER PORTFOLIO HIERARCHY", "TREEMAP · CLICK TO DRILL DOWN")
            tree_agg = (
                df_segments.groupby(["Customer Tier", "Buyer Group"], as_index=False)
                .agg(
                    Total_Spend=("Total Spend", "sum"),
                    Customers=("Customer ID", "count"),
                    Avg_Days=("Days Inactive", "mean"),
                )
            )
            fig_tree = px.treemap(
                tree_agg,
                path=["Customer Tier", "Buyer Group"],
                values="Total_Spend",
                color="Customer Tier",
                color_discrete_map=TIER_COLORS,
                custom_data=["Customers", "Avg_Days"],
            )
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>£%{value:,.0f}",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Total Spend: £%{value:,.0f}<br>"
                    "Customers: %{customdata[0]:,}<br>"
                    "Avg Inactive: %{customdata[1]:.0f} d<extra></extra>"
                ),
                marker={"line": {"width": 1.5, "color": T["bg_card"]}},
            )
            fig_tree.update_layout(
                template=T["plotly_template"],
                height=340,
                paper_bgcolor="rgba(0,0,0,0)",
                margin={"l": 4, "r": 4, "t": 6, "b": 6},
                font={"family": "Inter, sans-serif", "size": 11},
            )
            st.plotly_chart(fig_tree, use_container_width=True, config=PLOT_CONFIG)

        with c2, st.container(border=True):
            card_header("RFM SCORE DISTRIBUTION", "RED ≤5 · AMBER 6–8 · GREEN 9+")
            score_dist = (
                df_segments.groupby("Overall Score", as_index=False)["Customer ID"]
                .count()
                .rename(columns={"Customer ID": "Customers"})
            )
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
            fig_rfm.update_yaxes(range=[0, max(1, float(score_dist["Customers"].max())) * 1.16], title="Customers")
            fig_rfm.update_xaxes(dtick=1, title="Overall RFM Score (3–12)")
            st.plotly_chart(
                style_plotly(fig_rfm, T, height=340, bottom_margin=55, grid="y"),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        with st.container(border=True):
            card_header("TOP CUSTOMERS LEADERBOARD", "TOP 25 ACCOUNTS BY SPEND")
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


elif tab == "Retention & Cohorts":
    m1_df = df_cohort[df_cohort["Months Since First Purchase"] == 1]
    m3_df = df_cohort[df_cohort["Months Since First Purchase"] == 3]
    avg_m1 = float(m1_df["Retention Rate (%)"].mean()) if not m1_df.empty else 0.0
    avg_m3 = float(m3_df["Retention Rate (%)"].mean()) if not m3_df.empty else 0.0
    best_m1_row = m1_df.loc[m1_df["Retention Rate (%)"].idxmax()] if not m1_df.empty else None
    best_txt = (
        f"<strong>{html.escape(str(best_m1_row['First Purchase Month']))}</strong> leads Month-1 retention at "
        f"<strong>{float(best_m1_row['Retention Rate (%)']):.1f}%</strong>."
        if best_m1_row is not None
        else ""
    )
    render_insight(
        "Retention Insight",
        f"Average retention is <strong>{avg_m1:.1f}%</strong> in Month 1 and <strong>{avg_m3:.1f}%</strong> by Month 3. {best_txt}",
    )

    c1, c2 = st.columns([1.25, 1.0], gap="medium")

    with c1, st.container(border=True):
        card_header("COHORT RETENTION MATRIX (%)", "SCALE TUNED TO M+1 ONWARDS")
        piv = df_cohort.pivot(
            index="First Purchase Month",
            columns="Months Since First Purchase",
            values="Retention Rate (%)",
        )
        later = piv.drop(columns=[0], errors="ignore")
        if later.size and later.notna().to_numpy().any():
            z_cap = max(5.0, float(np.ceil(float(np.nanmax(later.to_numpy(dtype=float))) / 5.0) * 5.0))
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
        fig_hm.update_xaxes(title="Months Since First Purchase", dtick=1, side="bottom")
        fig_hm.update_yaxes(title="Cohort Month", type="category", autorange="reversed")
        st.plotly_chart(
            style_plotly(fig_hm, T, height=395, bottom_margin=55, grid="none"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )

    with c2, st.container(border=True):
        card_header("RETENTION DECAY BENCHMARK", "MEAN + P25–P75 IQR BAND")
        cohort_opts = ["Benchmark Only", *sorted(df_cohort["First Purchase Month"].unique().tolist())]
        overlay_cm = st.selectbox("Compare Specific Cohort", cohort_opts, label_visibility="collapsed")

        bench = (
            df_cohort.groupby("Months Since First Purchase")["Retention Rate (%)"]
            .agg(
                mean="mean",
                p25=lambda s: float(np.percentile(s, 25)),
                p75=lambda s: float(np.percentile(s, 75)),
            )
            .reset_index()
            .sort_values("Months Since First Purchase")
        )
        fig_bench = go.Figure()
        fig_bench.add_trace(
            go.Scatter(
                x=bench["Months Since First Purchase"],
                y=bench["p75"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig_bench.add_trace(
            go.Scatter(
                x=bench["Months Since First Purchase"],
                y=bench["p25"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=hex_to_rgba(T["accent"], 0.18),
                name="P25–P75 Range",
                hovertemplate="P25: %{y:.1f}%<extra></extra>",
            )
        )
        fig_bench.add_trace(
            go.Scatter(
                x=bench["Months Since First Purchase"],
                y=bench["mean"],
                name="All-Cohort Mean",
                mode="lines+markers",
                line={"color": T["accent"], "width": 2.8, "shape": "spline", "smoothing": 0.7},
                marker={"size": 6, "color": T["accent"], "line": {"width": 1.5, "color": T["bg_card"]}},
                hovertemplate="<b>Mean</b>: %{y:.1f}%<extra></extra>",
            )
        )
        if overlay_cm != "Benchmark Only":
            sel_s = df_cohort[df_cohort["First Purchase Month"] == overlay_cm].sort_values(
                "Months Since First Purchase"
            )
            fig_bench.add_trace(
                go.Scatter(
                    x=sel_s["Months Since First Purchase"],
                    y=sel_s["Retention Rate (%)"],
                    name=f"Cohort {overlay_cm}",
                    mode="lines+markers",
                    line={"color": T["green"], "width": 2.6},
                    marker={"size": 6, "color": T["green"], "line": {"width": 1.5, "color": T["bg_card"]}},
                    hovertemplate=f"<b>{html.escape(str(overlay_cm))}</b>: %{{y:.1f}}%<extra></extra>",
                )
            )
        fig_bench.update_layout(hovermode="x unified")
        fig_bench.update_yaxes(ticksuffix="%", title="Retention Rate", rangemode="tozero")
        fig_bench.update_xaxes(dtick=1, title="Months Since First Purchase")
        st.plotly_chart(
            style_plotly(fig_bench, T, height=348, bottom_margin=72, grid="y"),
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


elif tab == "Merchandising & Bundles":
    with st.spinner("Loading product bundle affinity..."):
        df_bundles = load_bundles_data()

    bf = df_bundles[(df_bundles["Orders Together"] >= min_orders) & (df_bundles["Bundle Lift"] >= min_lift)]
    if search_prod.strip():
        q = search_prod.strip().lower()
        bf = bf[
            bf["Product A"].str.lower().str.contains(q, na=False)
            | bf["Product B"].str.lower().str.contains(q, na=False)
        ]

    if bf.empty:
        render_empty_state("No product bundles match your sidebar thresholds.")
    else:
        top_pair = bf.nlargest(1, "Orders Together").iloc[0]
        max_lift_pair = bf.nlargest(1, "Bundle Lift").iloc[0]
        render_insight(
            "Merchandising Insight",
            f"<strong>{len(bf):,}</strong> qualifying cross-sell pairs found. Most frequent pair: "
            f"<strong>{html.escape(str(top_pair['Product A'])[:28])} + {html.escape(str(top_pair['Product B'])[:28])}</strong> "
            f"({int(top_pair['Orders Together']):,} orders). Highest affinity lift: "
            f"<strong>{float(max_lift_pair['Bundle Lift']):.1f}x</strong>.",
        )

        col_b1, col_b2 = st.columns(2, gap="medium")

        with col_b1, st.container(border=True):
            card_header("CROSS-SELL RECOMMENDER", "ATTACHMENT RATE (BUY A → BUY B)")
            anchor_prods = (
                bf.groupby("Product A")["Orders Together"]
                .sum()
                .nlargest(60)
                .index.tolist()
            )
            sel_anchor = st.selectbox("Select Anchor Product", anchor_prods, label_visibility="collapsed")
            recs = (
                bf[bf["Product A"] == sel_anchor]
                .nlargest(8, "Buy A -> Buy B (%)")
                .sort_values("Buy A -> Buy B (%)")
            )
            fig_rec = go.Figure(
                go.Bar(
                    x=recs["Buy A -> Buy B (%)"],
                    y=recs["Product B"].str.slice(0, 32),
                    orientation="h",
                    marker_color=T["accent"],
                    marker_line_width=0,
                    text=[f"{p:.1f}% ({lift:.1f}x)" for p, lift in zip(recs["Buy A -> Buy B (%)"], recs["Bundle Lift"])],
                    textposition="outside",
                    textfont={"size": 10, "color": T["text_secondary"]},
                    cliponaxis=False,
                    customdata=np.stack([recs["Product B"], recs["Orders Together"], recs["Bundle Lift"]], axis=-1),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Attachment Rate: %{x:.1f}%<br>"
                        "Orders Together: %{customdata[1]:,}<br>"
                        "Bundle Lift: %{customdata[2]:.2f}x<extra></extra>"
                    ),
                )
            )
            max_conf = float(recs["Buy A -> Buy B (%)"].max()) if not recs.empty else 50.0
            fig_rec.update_xaxes(ticksuffix="%", range=[0, min(115.0, max_conf * 1.32)], title="Probability Buyer Adds Item (%)")
            fig_rec.update_yaxes(title="")
            st.plotly_chart(
                style_plotly(fig_rec, T, height=340, bottom_margin=55, grid="x"),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        with col_b2, st.container(border=True):
            card_header("TOP 10 CO-OCCURRING BUNDLES", "ORDERS TOGETHER")
            top10_b = bf.nlargest(10, "Orders Together").sort_values("Orders Together").reset_index(drop=True)
            pair_labels = [
                f"{html.escape(str(a)[:22])}<br>+ {html.escape(str(b)[:22])}"
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
            fig_bar.update_xaxes(title="Orders Together", range=[0, float(top10_b["Orders Together"].max()) * 1.18])
            st.plotly_chart(
                style_plotly(fig_bar, T, height=388, bottom_margin=55, grid="x"),
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


elif tab == "Markets & Timing":
    if df_tx_sum.empty:
        render_empty_state()
    else:
        tot_geo_rev = float(df_tx_sum["Revenue"].sum()) or 1.0
        intl_rev = float(df_tx_sum.loc[df_tx_sum["Country"] != "United Kingdom", "Revenue"].sum())
        intl_share = intl_rev / tot_geo_rev * 100
        peak_slot = (
            df_tx_time.groupby(["Weekday", "Order Hour"], as_index=False)["Revenue"]
            .sum()
            .nlargest(1, "Revenue")
        )
        peak_txt = (
            f"Peak trading window is <strong>{html.escape(str(peak_slot.iloc[0]['Weekday']))} at "
            f"{int(peak_slot.iloc[0]['Order Hour'])}:00</strong> ({fmt_currency(float(peak_slot.iloc[0]['Revenue']))})."
            if not peak_slot.empty
            else ""
        )
        render_insight(
            "Market Insight",
            f"International markets (ex-UK) contribute <strong>{fmt_currency(intl_rev)}</strong> "
            f"(<strong>{intl_share:.1f}%</strong> of revenue across {df_tx_sum['Country'].nunique()} active markets). {peak_txt}",
        )

        # World Map Card (PRESERVED — every country marked in a distinct color)
        with st.container(border=True):
            card_header("GLOBAL MARKET FOOTPRINT", "EACH ACTIVE COUNTRY MARKED IN A DISTINCT COLOR")
            map_agg = (
                df_tx_sum[df_tx_sum["Country"] != "Not Specified"]
                .groupby("Country", as_index=False)
                .agg(
                    Revenue=("Revenue", "sum"),
                    Orders=("Orders", "sum"),
                    Customers=("Customers", "sum"),
                    Units=("Units", "sum"),
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
                height=420,
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
            card_header("TOP MARKETS BY REVENUE", "GEOGRAPHIC DISTRIBUTION")
            geo_df = df_tx_sum if inc_uk else df_tx_sum[df_tx_sum["Country"] != "United Kingdom"]
            geo_agg = (
                geo_df.groupby("Country", as_index=False)
                .agg(Revenue=("Revenue", "sum"), Orders=("Orders", "sum"))
                .nlargest(12, "Revenue")
                .sort_values("Revenue")
            )
            if geo_agg.empty:
                render_empty_state("Enable 'Include UK in Market Bar Chart' in the sidebar or adjust Market filters.")
            else:
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
                        customdata=geo_agg["Orders"],
                        hovertemplate="<b>%{y}</b><br>Revenue: £%{x:,.0f}<br>Orders: %{customdata:,}<extra></extra>",
                    )
                )
                fig_geo.update_xaxes(
                    range=[0, float(geo_agg["Revenue"].max()) * 1.2],
                    tickprefix="£",
                    tickformat="~s",
                    title="Revenue (£)",
                )
                fig_geo.update_yaxes(title="")
                st.plotly_chart(
                    style_plotly(fig_geo, T, height=345, bottom_margin=55, grid="x"),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

        with g2, st.container(border=True):
            card_header("PEAK TRADING HEATMAP", "DAY OF WEEK × ORDER HOUR (£)")
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            hm_piv = (
                df_tx_time.pivot_table(
                    index="Weekday",
                    columns="Order Hour",
                    values="Revenue",
                    aggfunc="sum",
                    fill_value=0.0,
                )
                .reindex(day_order)
                .fillna(0.0)
            )
            fig_time = go.Figure(
                go.Heatmap(
                    z=hm_piv.to_numpy(dtype=float),
                    x=[f"{int(h)}:00" for h in hm_piv.columns],
                    y=hm_piv.index.tolist(),
                    colorscale="YlGnBu" if theme_name == "Light" else "Plasma",
                    xgap=2,
                    ygap=2,
                    hovertemplate="<b>%{y} · %{x}</b><br>Revenue: £%{z:,.0f}<extra></extra>",
                    colorbar={
                        "thickness": 8,
                        "len": 0.8,
                        "outlinewidth": 0,
                        "tickprefix": "£",
                        "tickformat": "~s",
                        "tickfont": {"size": 9, "color": T["text_muted"]},
                    },
                )
            )
            fig_time.update_yaxes(title="", autorange="reversed")
            fig_time.update_xaxes(title="Hour of Day (24h)", tickangle=-35)
            st.plotly_chart(
                style_plotly(fig_time, T, height=345, bottom_margin=65, grid="none"),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        with st.container(border=True):
            card_header("MARKET PERFORMANCE BREAKDOWN", "TOP 15 MARKETS")
            cust_by_country = (
                df_segments.groupby("Country")["Customer ID"].nunique().to_dict()
            )
            all_geo = (
                df_tx_sum.groupby("Country", as_index=False)
                .agg(
                    Revenue=("Revenue", "sum"),
                    Orders=("Orders", "sum"),
                    Units=("Units", "sum"),
                )
                .nlargest(15, "Revenue")
            )
            g_rows = []
            for _, r in all_geo.iterrows():
                aov_c = r["Revenue"] / r["Orders"] if r["Orders"] else 0.0
                share = (r["Revenue"] / tot_geo_rev) * 100
                c_cnt = int(cust_by_country.get(r["Country"], 0))
                g_rows.append(
                    f"<tr>"
                    f"<td class='name-cell'>{html.escape(str(r['Country']))}</td>"
                    f"<td class='num'>{fmt_currency(r['Revenue'])}</td>"
                    f"<td class='num'>{share:.1f}%</td>"
                    f"<td class='num'>{c_cnt:,}</td>"
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


# -----------------------------------------------------------------------------
# 12. BI APP FOOTER
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="c360-footer">
        <span>⚡ Consumer-360 · Business Intelligence &amp; Retail Analytics</span>
        <span>Active Scope: {int(df_tx_sum['Lines'].sum()):,} line items · {df_segments['Customer ID'].nunique():,} accounts · {df_tx_sum['Country'].nunique()} markets</span>
    </div>
    """,
    unsafe_allow_html=True,
)