import asyncio
import logging
import os
import sqlite3
from typing import Optional

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
    
    # Use your existing connection logic
    if SUPABASE_DB_URL.startswith("sqlite://"):
        db_path = SUPABASE_DB_URL.replace("sqlite://", "")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        is_sqlite = True
    else:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()
        is_sqlite = False
    
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
            
            if is_sqlite:
                sql_code = _convert_postgres_to_sqlite(sql_code)
            
            try:
                if is_sqlite:
                    statements = [stmt.strip() for stmt in sql_code.split(';') if stmt.strip()]
                    for statement in statements:
                        cur.execute(statement)
                else:
                    cur.execute(sql_code)
                conn.commit()
                logger.info(f"✓ Successfully executed migration: {filename}")
            except Exception as e:
                conn.rollback()
                logger.error(f"✗ Migration {filename} failed: {e}")

    cur.close()
    conn.close()
    logger.info("Finished executing migrations (sync).")

def _convert_postgres_to_sqlite(sql_code: str) -> str:
    """Convert PostgreSQL-specific SQL to SQLite-compatible SQL."""
    # Your existing conversion logic
    sql_code = sql_code.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    sql_code = sql_code.replace("VARCHAR(255)", "TEXT")
    sql_code = sql_code.replace("VARCHAR(100)", "TEXT")
    sql_code = sql_code.replace("VARCHAR(3)", "TEXT")
    sql_code = sql_code.replace("DECIMAL(10, 2)", "REAL")
    sql_code = sql_code.replace("DECIMAL(3, 2)", "REAL")
    sql_code = sql_code.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    sql_code = sql_code.replace("BOOLEAN DEFAULT FALSE", "INTEGER DEFAULT 0")
    sql_code = sql_code.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
    sql_code = sql_code.replace("BOOLEAN", "INTEGER")
    sql_code = sql_code.replace("ON DELETE CASCADE", "")
    
    # Remove INDEX statements
    lines = sql_code.split('\n')
    filtered_lines = []
    for line in lines:
        if not line.strip().startswith('INDEX '):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

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