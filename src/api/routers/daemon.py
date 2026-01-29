"""
Daemon control endpoints.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..schemas.simulations import (
    DaemonStartRequest,
    DaemonStatusResponse,
    DaemonMetricsResponse,
    DaemonHistoryPoint,
    DaemonHistoryResponse,
)
from src.core.daemon_service import DaemonService
from src.core.daemon_runner import DaemonConfig
from src.core.agent_manager import AgentManager
from src.templates.template_loader import TemplateLoader
from src.core import config as app_config

router = APIRouter(prefix="/daemon", tags=["daemon"])


@router.get("/status", response_model=DaemonStatusResponse)
async def get_daemon_status():
    """Get daemon status and metrics."""
    try:
        service = DaemonService()
        is_running = service.is_running()
        state = service.read_state()
        metrics_data = service.read_metrics()

        metrics = None
        if metrics_data:
            metrics = DaemonMetricsResponse(
                total_calls=metrics_data.get("total_calls", 0),
                scheduled_calls=metrics_data.get("scheduled_calls", 0),
                started_calls=metrics_data.get("started_calls", 0),
                dropped_calls=metrics_data.get("dropped_calls", 0),
                inflight_calls=metrics_data.get("inflight_calls", 0),
                queue_depth=metrics_data.get("queue_depth", 0),
                target_calls_per_minute=metrics_data.get("target_calls_per_minute", 0),
                successful_calls=metrics_data.get("successful_calls", 0),
                failed_calls=metrics_data.get("failed_calls", 0),
                success_rate=metrics_data.get("success_rate", 0),
                total_operations=metrics_data.get("total_operations", 0),
                total_guardrails=metrics_data.get("total_guardrails", 0),
                blocked_guardrails=metrics_data.get("blocked_guardrails", 0),
                avg_latency_ms=metrics_data.get("avg_latency_ms", 0),
                p50_latency_ms=metrics_data.get("p50_latency_ms", 0),
                p95_latency_ms=metrics_data.get("p95_latency_ms", 0),
                max_latency_ms=metrics_data.get("max_latency_ms", 0),
                calls_per_minute=metrics_data.get("calls_per_minute", 0),
                started_calls_per_minute=metrics_data.get("started_calls_per_minute", 0),
                batches_completed=metrics_data.get("batches_completed", 0),
                runtime=metrics_data.get("runtime", "0s"),
                current_load_profile=metrics_data.get("current_load_profile", ""),
                recent_errors=metrics_data.get("recent_errors", []),
            )

        return DaemonStatusResponse(
            is_running=is_running,
            started_at=state.get("started_at") if state else None,
            stopped_at=state.get("stopped_at") if state else None,
            profile_id=state.get("profile_id") if state else None,
            profile_name=state.get("profile_name") if state else None,
            metrics=metrics,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_daemon(request: DaemonStartRequest):
    """Start the daemon process."""
    try:
        service = DaemonService()

        if service.is_running():
            raise HTTPException(status_code=409, detail="Daemon already running")

        # Load profile
        loader = TemplateLoader()
        profile = loader.load_template(request.profile_id)

        # Load agents
        manager = AgentManager()
        agents = manager.load_agents_from_csv(str(app_config.CREATED_AGENTS_CSV))

        if not agents:
            raise HTTPException(
                status_code=400,
                detail="No agents available. Create agents first."
            )

        # Create daemon config
        daemon_config = DaemonConfig(
            interval_seconds=request.interval_seconds,
            calls_per_batch_min=request.calls_per_batch_min,
            calls_per_batch_max=request.calls_per_batch_max,
            threads=request.threads,
            operations_weight=request.operations_weight,
        )

        success, message = service.start(
            daemon_config=daemon_config,
            agents=agents,
            profile_id=request.profile_id,
            profile_name=profile.metadata.name,
        )

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return {"success": True, "message": message}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_daemon():
    """Stop the daemon process."""
    try:
        service = DaemonService()

        if not service.is_running():
            return {"success": False, "message": "Daemon is not running"}

        success, message = service.stop()

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return {"success": True, "message": message}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=DaemonMetricsResponse)
async def get_daemon_metrics():
    """Get daemon metrics."""
    try:
        service = DaemonService()
        metrics_data = service.read_metrics()

        if not metrics_data:
            return DaemonMetricsResponse()

        return DaemonMetricsResponse(
            total_calls=metrics_data.get("total_calls", 0),
            scheduled_calls=metrics_data.get("scheduled_calls", 0),
            started_calls=metrics_data.get("started_calls", 0),
            dropped_calls=metrics_data.get("dropped_calls", 0),
            inflight_calls=metrics_data.get("inflight_calls", 0),
            queue_depth=metrics_data.get("queue_depth", 0),
            target_calls_per_minute=metrics_data.get("target_calls_per_minute", 0),
            successful_calls=metrics_data.get("successful_calls", 0),
            failed_calls=metrics_data.get("failed_calls", 0),
            success_rate=metrics_data.get("success_rate", 0),
            total_operations=metrics_data.get("total_operations", 0),
            total_guardrails=metrics_data.get("total_guardrails", 0),
            blocked_guardrails=metrics_data.get("blocked_guardrails", 0),
            avg_latency_ms=metrics_data.get("avg_latency_ms", 0),
            p50_latency_ms=metrics_data.get("p50_latency_ms", 0),
            p95_latency_ms=metrics_data.get("p95_latency_ms", 0),
            max_latency_ms=metrics_data.get("max_latency_ms", 0),
            calls_per_minute=metrics_data.get("calls_per_minute", 0),
            started_calls_per_minute=metrics_data.get("started_calls_per_minute", 0),
            batches_completed=metrics_data.get("batches_completed", 0),
            runtime=metrics_data.get("runtime", "0s"),
            current_load_profile=metrics_data.get("current_load_profile", ""),
            recent_errors=metrics_data.get("recent_errors", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=DaemonHistoryResponse)
async def get_daemon_history(limit: int = 120):
    """Get daemon history data."""
    try:
        service = DaemonService()
        history = service.read_history(limit=limit)

        history_points = [
            DaemonHistoryPoint(
                timestamp=h.get("timestamp", ""),
                total_calls=h.get("total_calls", 0),
                total_operations=h.get("total_operations", 0),
                total_guardrails=h.get("total_guardrails", 0),
            )
            for h in history
        ]

        return DaemonHistoryResponse(history=history_points)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
