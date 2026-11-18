"""PostgreSQL connection configuration for Consumer360."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def get_database_url() -> URL:
    """Build a PostgreSQL connection URL from environment variables."""
    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise RuntimeError(
            f"Missing database environment variables: {missing}"
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )


def get_engine() -> Engine:
    """Create a SQLAlchemy engine with connection health checks."""
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
    )


def test_connection() -> None:
    """Verify connectivity and print database metadata."""
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS username,
                        version() AS server_version
                    """
                )
            ).mappings().one()

            print("Database connection successful.")
            print("Database:", result["database_name"])
            print("User:", result["username"])
            print("Server:", result["server_version"])

    finally:
        engine.dispose()


if __name__ == "__main__":
    test_connection()
