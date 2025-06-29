"""
Simple main.py for testing basic FastAPI functionality
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from simple_config import settings

app = FastAPI(
    title=settings.app_name,
    description="Testing Phase 3 - Executive Dashboard",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Project Management Dashboard API - Phase 3 Test", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": "1.0.0",
        "config_loaded": True,
        "openai_configured": bool(settings.openai_api_key),
        "jira_configured": bool(settings.jira_url),
        "tempo_configured": bool(settings.tempo_api_token)
    }

@app.get("/api/config")
async def get_config():
    """Get configuration status"""
    return {
        "jira_url": settings.jira_url,
        "confluence_url": settings.confluence_url,
        "openai_model": settings.openai_model,
        "debug": settings.debug
    }

if __name__ == "__main__":
    uvicorn.run(
        "simple_main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )