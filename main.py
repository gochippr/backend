# main.py - Updated main file with async database
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import db_manager
from database.migrations import run_migrations, run_migrations_sync
from routers import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This outputs to console
    ],
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    
    try:
        # Run migrations - keeping your existing migration system for now
        logger.info("Running database migrations...")
        run_migrations_sync()  # Use your existing migrations
        
        # Create any additional SQLAlchemy tables
        await db_manager.create_tables()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        # Add timeout to prevent hanging on close
        await asyncio.wait_for(db_manager.close(), timeout=5.0)
        logger.info("Database connections closed successfully")
    except asyncio.TimeoutError:
        logger.warning("Database close timed out - forcing shutdown")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shutdown completed")

# Create FastAPI app with lifespan events
app = FastAPI(
    title="Your Financial API",
    description="API with Plaid integration and async database",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your existing router
app.include_router(router, tags=["API v1"])

@app.get("/")
async def read_root() -> dict:
    return {"message": "Hello, World!"}

@app.get("/health")
async def health_check():
    """Enhanced health check with database connectivity test."""
    db_status = "unknown"
    try:
        # Test database connection
        async for db in db_manager.get_session():
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            db_status = "connected" if result else "disconnected"
            break
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"
    
    return {
        "status": "healthy",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "development")
    }