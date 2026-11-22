import argparse
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "online_retail_II_2009-10.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
LOG_DIR = PROJECT_ROOT / "logs"

NON_PROD_CODES = {
    "POST",
    "DOT",
    "M",
    "m",
    "D",
    "C2",
    "BANK CHARGES",
    "ADJUST",
    "ADJUST2",
    "TEST001",
    "TEST002",
    "S",
    "B",
    "AMAZONFEE",
}


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "etl.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger("consumer360_etl")


def clean_transactions(raw_path: Path, logger: logging.Logger) -> pd.DataFrame:
    if not raw_path.exists():
        msg = f"Raw dataset not found: {raw_path}"
        raise FileNotFoundError(msg)

    df = pd.read_csv(
        raw_path,
        dtype={"Invoice": str, "StockCode": str, "Customer ID": str},
    )
    df["InvoiceDate_dt"] = pd.to_datetime(
        df["InvoiceDate"], format="mixed", dayfirst=True, errors="coerce"
    )
    df["LineRevenue"] = df["Quantity"] * df["Price"]

    clean = df.drop_duplicates().copy()
    clean = clean[~clean["Invoice"].str.startswith("C", na=False)]
    clean = clean[(clean["Quantity"] > 0) & (clean["Price"] > 0)]
    clean = clean[~clean["StockCode"].isin(NON_PROD_CODES)]
    clean = clean.dropna(subset=["Customer ID", "InvoiceDate_dt"]).copy()
    clean["Customer ID"] = clean["Customer ID"].str.replace(r"\.0$", "", regex=True)

    clean["year_month"] = clean["InvoiceDate_dt"].dt.to_period("M").astype(str)
    clean["hour"] = clean["InvoiceDate_dt"].dt.hour

    clean_pg = clean.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "Price": "price",
            "Customer ID": "customer_id",
            "Country": "country",
            "InvoiceDate_dt": "invoice_date",
            "LineRevenue": "line_revenue",
        }
    )[
        [
            "invoice",
            "stock_code",
            "description",
            "quantity",
            "price",
            "customer_id",
            "country",
            "invoice_date",
            "line_revenue",
            "year_month",
            "hour",
        ]
    ]
    clean_pg["customer_id"] = clean_pg["customer_id"].astype(int)
    logger.info("Cleaned transactions: %s rows", f"{len(clean_pg):,}")
    return clean_pg


def build_rfm_and_segments(
    clean_pg: pd.DataFrame, logger: logging.Logger
) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshot_date = clean_pg["invoice_date"].max() + pd.Timedelta(days=1)
    rfm = clean_pg.groupby("customer_id", as_index=False).agg(
        last_purchase=("invoice_date", "max"),
        frequency=("invoice", "nunique"),
        monetary=("line_revenue", "sum"),
        total_units=("quantity", "sum"),
        country=("country", "first"),
    )
    rfm["recency"] = (snapshot_date - rfm["last_purchase"]).dt.days
    rfm["avg_order_value"] = (rfm["monetary"] / rfm["frequency"]).round(2)

    rfm["r_score"] = pd.qcut(rfm["recency"], q=4, labels=[4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), q=4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"], q=4, labels=[1, 2, 3, 4]).astype(int)
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def assign_segment(row: pd.Series) -> str:
        if row["r_score"] >= 4 and row["f_score"] >= 4 and row["m_score"] >= 4:
            return "Champions"
        if row["f_score"] >= 3 and row["m_score"] >= 3:
            return "Loyal Customers"
        if row["r_score"] >= 3 and row["f_score"] <= 2:
            return "Potential Loyalists"
        if row["r_score"] <= 2 and row["m_score"] >= 3:
            return "At Risk"
        return "Hibernating / Lost"

    rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)

    features = np.log1p(rfm[["recency", "frequency", "monetary"]])
    scaled = StandardScaler().fit_transform(features)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    rfm["kmeans_cluster"] = kmeans.fit_predict(scaled)

    rfm_cols = [
        "customer_id",
        "last_purchase",
        "frequency",
        "monetary",
        "total_units",
        "country",
        "recency",
        "avg_order_value",
        "r_score",
        "f_score",
        "m_score",
        "rfm_score",
    ]
    seg_cols = [
        "customer_id",
        "country",
        "last_purchase",
        "recency",
        "frequency",
        "monetary",
        "total_units",
        "avg_order_value",
        "r_score",
        "f_score",
        "m_score",
        "rfm_score",
        "rfm_segment",
        "kmeans_cluster",
    ]
    logger.info("Built RFM & K-Means segments for %s customers", f"{len(rfm):,}")
    return rfm[rfm_cols], rfm[seg_cols]


def build_cohorts(clean_pg: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    tx = clean_pg[["customer_id", "invoice_date"]].copy()
    tx["invoice_month"] = tx["invoice_date"].dt.to_period("M")
    tx["cohort_month"] = tx.groupby("customer_id")["invoice_month"].transform("min")
    tx["cohort_index"] = (
        (tx["invoice_month"].dt.year - tx["cohort_month"].dt.year) * 12
        + (tx["invoice_month"].dt.month - tx["cohort_month"].dt.month)
    )

    counts = (
        tx.groupby(["cohort_month", "cohort_index"])["customer_id"]
        .nunique()
        .reset_index(name="active_customers")
    )
    sizes = counts.loc[counts["cohort_index"] == 0, ["cohort_month", "active_customers"]].rename(
        columns={"active_customers": "cohort_size"}
    )
    cohorts = counts.merge(sizes, on="cohort_month", how="left")
    cohorts["retention_pct"] = (cohorts["active_customers"] / cohorts["cohort_size"] * 100).round(2)
    cohorts["cohort_month"] = cohorts["cohort_month"].astype(str)
    logger.info("Built cohort retention matrix: %s rows", f"{len(cohorts):,}")
    return cohorts


def build_local_engine():
    pg_password = os.getenv("PG_PASSWORD")
    if not pg_password:
        return None
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("PG_USER", "postgres"),
        password=pg_password,
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_DB", "retail_analytics"),
    )
    return create_engine(url)


def build_supabase_engine():
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    if not db_password:
        return None
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("SUPABASE_DB_USER", "postgres.jtydikmxeclhrkcpxpyr"),
        password=db_password,
        host=os.getenv("SUPABASE_DB_HOST", "aws-1-ap-south-1.pooler.supabase.com"),
        port=int(os.getenv("SUPABASE_DB_PORT", "5432")),
        database=os.getenv("SUPABASE_DB_NAME", "postgres"),
        query={"sslmode": "require"},
    )
    return create_engine(url, connect_args={"connect_timeout": 10})


def sync_database(
    engine,
    label: str,
    clean_pg: pd.DataFrame,
    rfm_df: pd.DataFrame,
    seg_df: pd.DataFrame,
    coh_df: pd.DataFrame,
    logger: logging.Logger,
) -> pd.DataFrame:
    logger.info("Syncing tables to %s...", label)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for tbl in ["cleaned_transactions", "customer_rfm", "customer_segments", "cohort_retention"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))

    clean_pg.to_sql(
        "cleaned_transactions", engine, if_exists="replace", index=False, chunksize=5000, method="multi"
    )
    rfm_df.to_sql("customer_rfm", engine, if_exists="replace", index=False, chunksize=5000, method="multi")
    seg_df.to_sql(
        "customer_segments", engine, if_exists="replace", index=False, chunksize=5000, method="multi"
    )
    coh_df.to_sql(
        "cohort_retention", engine, if_exists="replace", index=False, chunksize=5000, method="multi"
    )

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for sql_file in ["week2_views.sql", "week2_market_basket.sql"]:
            sql_path = SQL_DIR / sql_file
            if sql_path.exists():
                for stmt in sql_path.read_text(encoding="utf-8").split(";"):
                    if stmt.strip():
                        conn.execute(text(stmt))
                logger.info("Executed %s on %s", sql_file, label)

        for tbl in [
            "cleaned_transactions",
            "customer_segments",
            "cohort_retention",
            "product_affinity",
        ]:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            if not cnt:
                msg = f"Validation failed on {label}: {tbl} has 0 rows"
                raise RuntimeError(msg)
            logger.info("Verified %s.%s: %s rows", label, tbl, f"{cnt:,}")

    return pd.read_sql("SELECT * FROM product_affinity", engine)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consumer-360 Automated ETL Pipeline")
    parser.add_argument(
        "--target",
        choices=["local", "supabase", "both"],
        default="local",
        help="Target PostgreSQL database(s) to refresh",
    )
    args = parser.parse_args()

    logger = setup_logging()
    load_dotenv(PROJECT_ROOT / ".env")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Consumer-360 ETL pipeline (target=%s)", args.target)
    clean_pg = clean_transactions(RAW_PATH, logger)
    rfm_df, seg_df = build_rfm_and_segments(clean_pg, logger)
    coh_df = build_cohorts(clean_pg, logger)

    clean_pg.to_csv(PROCESSED_DIR / "cleaned_retail_week1.csv", index=False)
    rfm_df.to_csv(PROCESSED_DIR / "customer_rfm_week1.csv", index=False)
    seg_df.to_csv(PROCESSED_DIR / "customer_segments_week2.csv", index=False)
    coh_df.to_csv(PROCESSED_DIR / "cohort_retention_week2.csv", index=False)

    targets = []
    if args.target in {"local", "both"}:
        local_eng = build_local_engine()
        if local_eng is not None:
            targets.append(("Local PostgreSQL", local_eng))
    if args.target in {"supabase", "both"}:
        supa_eng = build_supabase_engine()
        if supa_eng is not None:
            targets.append(("Supabase PostgreSQL", supa_eng))

    if not targets:
        logger.warning("No database credentials found; CSV exports completed.")
        return

    for label, eng in targets:
        try:
            aff_df = sync_database(
                engine=eng,
                label=label,
                clean_pg=clean_pg,
                rfm_df=rfm_df,
                seg_df=seg_df,
                coh_df=coh_df,
                logger=logger,
            )
            aff_df.to_csv(PROCESSED_DIR / "product_affinity_week2.csv", index=False)
        except SQLAlchemyError as exc:
            logger.exception("Database sync failed for %s: %s", label, exc)
            raise

    logger.info("Consumer-360 ETL pipeline completed successfully.")


if __name__ == "__main__":
    main()