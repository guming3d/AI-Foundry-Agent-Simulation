"""
Simulation endpoints for one-time simulations.
"""

import threading
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException

from ..schemas.simulations import (
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationMetrics,
    SimulationResultsResponse,
)
from ..websocket import manager as ws_manager
from src.core.simulation_engine import SimulationEngine, SimulationConfig
from src.core.agent_manager import AgentManager
from src.templates.template_loader import TemplateLoader
from src.core import config as app_config

router = APIRouter(prefix="/simulations", tags=["simulations"])

# Track simulation state
_simulation_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "message": "",
    "engine": None,
    "results": None,
    "completed_at": None,
}
_simulation_lock = threading.Lock()


def _progress_callback(current: int, total: int, message: str):
    """Callback for simulation progress."""
    with _simulation_lock:
        _simulation_state["progress"] = current
        _simulation_state["total"] = total
        _simulation_state["message"] = message


def _run_simulation(engine: SimulationEngine, sim_config: SimulationConfig, sim_type: str):
    """Run simulation in background thread."""
    global _simulation_state
    try:
        if sim_type == "operations":
            results = engine.run_operations(config=sim_config, progress_callback=_progress_callback)
        elif sim_type == "guardrails":
            results = engine.run_guardrails(config=sim_config, progress_callback=_progress_callback)
        else:
            # Run both
            op_results = engine.run_operations(config=sim_config, progress_callback=_progress_callback)
            gr_results = engine.run_guardrails(config=sim_config, progress_callback=_progress_callback)
            results = {"operations": op_results, "guardrails": gr_results}

        with _simulation_lock:
            _simulation_state["results"] = results
            _simulation_state["completed_at"] = datetime.now().isoformat()
            _simulation_state["running"] = False

    except Exception as e:
        with _simulation_lock:
            _simulation_state["results"] = {"error": str(e)}
            _simulation_state["running"] = False


@router.post("/start")
async def start_simulation(request: SimulationStartRequest):
    """Start a one-time simulation."""
    with _simulation_lock:
        if _simulation_state["running"]:
            raise HTTPException(status_code=409, detail="Simulation already in progress")

    try:
        # Load profile
        loader = TemplateLoader()
        profile = loader.load_template(request.profile_id)

        # Load agents from CSV
        manager = AgentManager()
        agents = manager.load_agents_from_csv(str(app_config.CREATED_AGENTS_CSV))

        if not agents:
            # Try listing from Azure
            azure_agents = manager.list_agents()
            if not azure_agents:
                raise HTTPException(
                    status_code=400,
                    detail="No agents available. Create agents first."
                )

        # Create engine
        engine = SimulationEngine.from_profile(profile)

        # Create simulation config
        sim_config = SimulationConfig(
            num_calls=request.num_calls,
            threads=request.threads,
            delay=request.delay,
        )

        with _simulation_lock:
            _simulation_state["running"] = True
            _simulation_state["progress"] = 0
            _simulation_state["total"] = request.num_calls
            _simulation_state["message"] = "Starting simulation..."
            _simulation_state["engine"] = engine
            _simulation_state["results"] = None
            _simulation_state["completed_at"] = None

        # Start background thread
        thread = threading.Thread(
            target=_run_simulation,
            args=(engine, sim_config, request.simulation_type),
            daemon=True,
        )
        thread.start()

        return {"success": True, "message": "Simulation started"}

    except HTTPException:
        raise
    except Exception as e:
        with _simulation_lock:
            _simulation_state["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_simulation():
    """Stop the running simulation."""
    with _simulation_lock:
        if not _simulation_state["running"]:
            return {"success": False, "message": "No simulation running"}

        engine = _simulation_state.get("engine")
        if engine:
            engine.stop()

        _simulation_state["running"] = False
        _simulation_state["message"] = "Simulation stopped"

    return {"success": True, "message": "Simulation stop requested"}


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status():
    """Get current simulation status."""
    with _simulation_lock:
        return SimulationStatusResponse(
            is_running=_simulation_state["running"],
            progress=_simulation_state["progress"],
            total=_simulation_state["total"],
            current_message=_simulation_state["message"],
        )


@router.get("/results", response_model=SimulationResultsResponse)
async def get_simulation_results():
    """Get simulation results."""
    with _simulation_lock:
        results = _simulation_state.get("results")
        completed_at = _simulation_state.get("completed_at")

        if results is None:
            return SimulationResultsResponse(
                success=False,
                metrics=SimulationMetrics(),
                completed_at=None,
            )

        if "error" in results:
            return SimulationResultsResponse(
                success=False,
                metrics=SimulationMetrics(),
                completed_at=completed_at,
            )

        # Handle combined results or single result
        if "operations" in results:
            ops = results.get("operations", {})
            metrics = SimulationMetrics(
                total_calls=ops.get("total_calls", 0),
                successful_calls=ops.get("successful_calls", 0),
                failed_calls=ops.get("failed_calls", 0),
                success_rate=ops.get("success_rate", 0),
                avg_latency_ms=ops.get("avg_latency_ms", 0),
                max_latency_ms=ops.get("max_latency_ms", 0),
            )
        else:
            metrics = SimulationMetrics(
                total_calls=results.get("total_calls", 0),
                successful_calls=results.get("successful_calls", 0),
                failed_calls=results.get("failed_calls", 0),
                success_rate=results.get("success_rate", 0),
                avg_latency_ms=results.get("avg_latency_ms", 0),
                max_latency_ms=results.get("max_latency_ms", 0),
            )

        return SimulationResultsResponse(
            success=True,
            metrics=metrics,
            completed_at=completed_at,
        )
