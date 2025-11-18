import logging
import os
import sqlite3

import psycopg2

from utils.constants import MIGRATIONS_DIR, SUPABASE_DB_URL

logger = logging.getLogger(__name__)


def get_connection():
    """Get database connection - supports both PostgreSQL and SQLite for testing."""
    if not SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL environment variable not set")
    
    if SUPABASE_DB_URL.startswith("sqlite://"):
        # SQLite connection for testing
        db_path = SUPABASE_DB_URL.replace("sqlite://", "")
        return sqlite3.connect(db_path)
    else:
        # PostgreSQL connection for production
        return psycopg2.connect(SUPABASE_DB_URL)


def run_migrations() -> None:
    logger.info("Starting database migrations...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if this is SQLite or PostgreSQL
    is_sqlite = SUPABASE_DB_URL and SUPABASE_DB_URL.startswith("sqlite://")

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
                # Convert PostgreSQL SQL to SQLite-compatible SQL
                sql_code = _convert_postgres_to_sqlite(sql_code)
            
            try:
                if is_sqlite:
                    # SQLite doesn't support executing multiple statements at once
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
    logger.info("Finished executing migrations.")


def _convert_postgres_to_sqlite(sql_code: str) -> str:
    """Convert PostgreSQL-specific SQL to SQLite-compatible SQL."""
    # Basic conversions for testing
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
    
    # Remove PostgreSQL-specific syntax that SQLite doesn't support
    sql_code = sql_code.replace("ON DELETE CASCADE", "")
    
    # Remove INDEX statements as they're not supported in CREATE TABLE for SQLite
    lines = sql_code.split('\n')
    filtered_lines = []
    for line in lines:
        if not line.strip().startswith('INDEX '):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)
