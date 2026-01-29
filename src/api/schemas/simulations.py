"""
Pydantic schemas for simulation-related API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SimulationStartRequest(BaseModel):
    """Request to start a simulation."""
    profile_id: str = Field(..., description="Industry profile ID")
    num_calls: int = Field(default=100, ge=1, le=10000, description="Number of calls to make")
    threads: int = Field(default=5, ge=1, le=50, description="Number of concurrent threads")
    delay: float = Field(default=0.5, ge=0, le=10, description="Delay between calls in seconds")
    simulation_type: str = Field(default="operations", description="Type: operations, guardrails, or both")


class SimulationStatusResponse(BaseModel):
    """Simulation status response."""
    is_running: bool
    progress: int = 0
    total: int = 0
    current_message: str = ""


class SimulationMetrics(BaseModel):
    """Simulation metrics summary."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0


class SimulationResultsResponse(BaseModel):
    """Simulation results response."""
    success: bool
    metrics: SimulationMetrics
    completed_at: Optional[str] = None


class DaemonStartRequest(BaseModel):
    """Request to start the daemon."""
    profile_id: str = Field(..., description="Industry profile ID")
    interval_seconds: int = Field(default=60, ge=10, le=3600)
    calls_per_batch_min: int = Field(default=5, ge=1, le=1000)
    calls_per_batch_max: int = Field(default=15, ge=1, le=1000)
    threads: int = Field(default=3, ge=1, le=50)
    operations_weight: int = Field(default=80, ge=0, le=100)


class DaemonMetricsResponse(BaseModel):
    """Daemon metrics response."""
    total_calls: int = 0
    scheduled_calls: int = 0
    started_calls: int = 0
    dropped_calls: int = 0
    inflight_calls: int = 0
    queue_depth: int = 0
    target_calls_per_minute: float = 0.0
    successful_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    total_operations: int = 0
    total_guardrails: int = 0
    blocked_guardrails: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    calls_per_minute: float = 0.0
    started_calls_per_minute: float = 0.0
    batches_completed: int = 0
    runtime: str = "0s"
    current_load_profile: str = ""
    recent_errors: List[str] = []


class DaemonStatusResponse(BaseModel):
    """Daemon status response."""
    is_running: bool
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    metrics: Optional[DaemonMetricsResponse] = None


class DaemonHistoryPoint(BaseModel):
    """Single history data point."""
    timestamp: str
    total_calls: int
    total_operations: int
    total_guardrails: int


class DaemonHistoryResponse(BaseModel):
    """Daemon history response."""
    history: List[DaemonHistoryPoint]
