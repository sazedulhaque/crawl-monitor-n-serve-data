import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from apps.api.routes import auth, books
from apps.scheduler import scheduler as scheduler_module
from core.config import settings
from core.limiter import limiter
from db.mongodb import db


def setup_logging():
    """Configure application logging"""
    # Set up root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("scraping_service.log"),
            logging.StreamHandler(),
        ],
    )

    # Disable or reduce httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Only show warnings/errors
    # OR completely disable:
    # logging.getLogger("httpx").setLevel(logging.CRITICAL)

    # Disable httpcore (underlying library) logging too
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Configure logging
setup_logging()

logger = logging.getLogger(__name__)

# Create rate limiter with global default
# Global default: 100 requests per hour as requested


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A web crawling, monitoring, and data serving application",
    version=settings.VERSION,
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/api/v1/books", tags=["Books"])

# Add pagination support
add_pagination(app)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection and start scheduler"""
    logger.info("Starting application...")
    await db.connect_db()
    logger.info("Database connection established")

    # Start the scheduler
    await scheduler_module.start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection and stop scheduler"""
    logger.info("Shutting down application...")

    # Stop the scheduler
    await scheduler_module.stop_scheduler()

    await db.close_db()
    logger.info("Database connection closed")


@app.get("/")
async def root():
    return {
        "application": "Live",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
