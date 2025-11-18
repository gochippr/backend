import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.supabase import orm
from routers import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # This outputs to console
    ],
)

# Run migrations on startup (now works with test database)
orm.run_migrations()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, tags=["API v1"])


@app.get("/")
async def read_root() -> dict:
    return {"message": "Hello, World!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}