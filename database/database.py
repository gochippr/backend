import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from utils.constants import SUPABASE_DB_URL

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.engine: AsyncEngine
        self.async_session_factory: async_sessionmaker[AsyncSession]
        self._setup_database()
    
    def _setup_database(self):
        """Initialize the database engine and session factory."""
        if not SUPABASE_DB_URL:
            raise RuntimeError("SUPABASE_DB_URL environment variable not set")
        
        # Convert PostgreSQL URL to async format
        if SUPABASE_DB_URL.startswith("postgresql://"):
            database_url = SUPABASE_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
        elif SUPABASE_DB_URL.startswith("sqlite://"):
            database_url = SUPABASE_DB_URL.replace("sqlite://", "sqlite+aiosqlite://")
        else:
            database_url = SUPABASE_DB_URL
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all tables defined by SQLAlchemy models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def close(self):
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI - this is what your routes will use
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async for session in db_manager.get_session():
        yield session