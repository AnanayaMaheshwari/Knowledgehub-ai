
import asyncio
import logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.chat import router as chat_router  
from fastapi import FastAPI, HTTPException

from app.services.supabase_service import (
    check_supabase_connection,
    check_database_connection
)

from app.services.background_worker import background_worker

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router


# Configure application logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Start background services when FastAPI starts.
    Stop them gracefully when FastAPI shuts down.
    """

    logger.info("Starting KnowledgeHub AI...")

    # Start the document processing worker.
    worker_task = asyncio.create_task(
        background_worker(),
        name="knowledgehub-document-worker"
    )

    app.state.worker_task = worker_task

    logger.info("Background document worker scheduled.")

    yield

    # Gracefully stop the worker.
    logger.info("Shutting down KnowledgeHub AI...")

    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Background worker stopped.")

    logger.info("KnowledgeHub AI shutdown complete.")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="KnowledgeHub AI",
    description="An Enterprise AI Knowledge Assistant",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register API routers.
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)

# ============================================================
# HEALTH CHECKS
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Welcome to KnowledgeHub AI!",
        "status": "Backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "KnowledgeHub AI"
    }


@app.get("/health/supabase")
def supabase_health():
    try:
        check_supabase_connection()

        return {
            "status": "connected",
            "service": "Supabase"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Supabase."
        )


@app.get("/health/database")
def database_health():
    try:
        check_database_connection()

        return {
            "status": "connected",
            "database": "Supabase PostgreSQL",
            "query_test": "successful"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database query failed."
        )
