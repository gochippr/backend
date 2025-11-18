import logging
import os

import psycopg2

from utils.constants import MIGRATIONS_DIR, SUPABASE_DB_URL

logger = logging.getLogger(__name__)


def get_connection() -> psycopg2.extensions.connection:
    if not SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL environment variable not set")
    return psycopg2.connect(SUPABASE_DB_URL)


def run_migrations() -> None:
    logger.info("Starting database migrations...")
    conn = get_connection()
    cur = conn.cursor()

    migration_files = sorted(
        [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")]
    )

    if not migration_files:
        logger.info("No migration files found.")
        return

    for filename in migration_files:
        logger.info(f"Executing migration: {filename}")
        with open(os.path.join(MIGRATIONS_DIR, filename), "r") as f:
            sql_code = f.read()
            try:
                cur.execute(sql_code)
                conn.commit()
                logger.info(f"✓ Successfully executed migration: {filename}")
            except Exception as e:
                conn.rollback()
                logger.error(f"✗ Migration {filename} failed: {e}")

    cur.close()
    conn.close()
    logger.info("Finished executing migrations.")
