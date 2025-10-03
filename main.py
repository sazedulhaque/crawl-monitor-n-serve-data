from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import auth, books
from core.config import settings
from db.mongodb import db

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A web crawling, monitoring, and data serving application",
    version=settings.VERSION,
)

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


@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    await db.connect_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection"""
    await db.close_db()


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
