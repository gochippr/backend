import asyncio
import logging
import os

import psycopg2
from sqlalchemy import text

from database.database import db_manager
from utils.constants import MIGRATIONS_DIR, SUPABASE_DB_URL

logger = logging.getLogger(__name__)

def run_migrations_sync():
    """Run your existing migrations synchronously."""
    logger.info("Starting database migrations (sync)...")
    
    if not SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL environment variable not set")
    
    # Connect to PostgreSQL database
    conn = psycopg2.connect(SUPABASE_DB_URL)
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
    logger.info("Finished executing migrations (sync).")


async def run_migrations():
    """Run migrations asynchronously using SQLAlchemy."""
    logger.info("Starting database migrations (async)...")
    
    migration_files = sorted(
        [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")]
    )

    if not migration_files:
        logger.info("No migration files found.")
        return

    async with db_manager.engine.begin() as conn:
        for filename in migration_files:
            logger.info(f"Executing migration: {filename}")
            with open(os.path.join(MIGRATIONS_DIR, filename), "r") as f:
                sql_code = f.read()
                
                try:
                    await conn.execute(text(sql_code))
                    logger.info(f"✓ Successfully executed migration: {filename}")
                except Exception as e:
                    logger.error(f"✗ Migration {filename} failed: {e}")
                    raise

    logger.info("Finished executing migrations (async).")