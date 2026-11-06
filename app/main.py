from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import engine, Base
from app.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from app.routers import transactions, budgets, subscriptions, analytics

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static and Templates paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include Routers
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(subscriptions.router)
app.include_router(analytics.router)


@app.get("/", include_in_schema=False)
def serve_home():
    """Serve the single-page dashboard application."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        return {"message": "FinTrack Pro API is active. Open /docs for Swagger documentation."}
    return FileResponse(str(index_file))


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker / orchestration."""
    return {"status": "healthy", "version": APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
