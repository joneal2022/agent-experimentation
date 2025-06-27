"""
Main API router for the application
"""
from fastapi import APIRouter

# Import all route modules
from api.endpoints import jira, confluence, tempo, alerts, dashboard, analytics

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    jira.router,
    prefix="/jira",
    tags=["jira"]
)

api_router.include_router(
    confluence.router,
    prefix="/confluence",
    tags=["confluence"]
)

api_router.include_router(
    tempo.router,
    prefix="/tempo",
    tags=["tempo"]
)

api_router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["alerts"]
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)