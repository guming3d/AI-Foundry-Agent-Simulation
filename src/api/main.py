"""
FastAPI main application.

Provides REST API and WebSocket endpoints for the web frontend.
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .routers import agents, workflows, simulations, evaluations, templates, models, status, daemon
from .websocket import simulation_websocket_handler, daemon_websocket_handler

# Create FastAPI app
app = FastAPI(
    title="Microsoft Foundry Bootstrap API",
    description="REST API for managing AI agents, workflows, simulations, and evaluations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(status.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(simulations.router, prefix="/api")
app.include_router(daemon.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")


# WebSocket endpoints
@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation updates."""
    await simulation_websocket_handler(websocket)


@app.websocket("/ws/daemon")
async def websocket_daemon(websocket: WebSocket):
    """WebSocket endpoint for real-time daemon metrics."""
    await daemon_websocket_handler(websocket)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Microsoft Foundry Bootstrap API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# Export app for uvicorn
__all__ = ["app"]
