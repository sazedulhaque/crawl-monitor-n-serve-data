from fastapi import FastAPI

from core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A web crawling, monitoring, and data serving application",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "application": "Live",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
