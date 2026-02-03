"""
Co-Teacher: Multi-agent AI system for special education teachers.
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.config import get_settings

# Create FastAPI app
app = FastAPI(
    title="Co-Teacher API",
    description="Multi-agent AI system for special education teachers",
    version="1.0.0"
)

# Get settings
settings = get_settings()

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serve the frontend UI."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Co-Teacher API is running", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy"}


# Import and include routers
from app.api.routes import team_info, agent_info, model_architecture, execute, students, predictions, schedule

app.include_router(team_info.router, prefix="/api", tags=["Team Info"])
app.include_router(agent_info.router, prefix="/api", tags=["Agent Info"])
app.include_router(model_architecture.router, prefix="/api", tags=["Architecture"])
app.include_router(execute.router, prefix="/api", tags=["Execute"])
app.include_router(students.router, prefix="/api", tags=["Students"])
app.include_router(predictions.router, prefix="/api", tags=["Predictions"])
app.include_router(schedule.router, prefix="/api", tags=["Schedule"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
