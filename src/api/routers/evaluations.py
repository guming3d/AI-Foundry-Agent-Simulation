"""
Evaluation endpoints.
"""

import threading
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.evaluation_engine import EvaluationEngine
from src.core.evaluation_templates import EvaluationTemplateLoader
from src.core.agent_manager import AgentManager

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

# Track evaluation progress
_evaluation_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "message": "",
    "results": None,
}
_evaluation_lock = threading.Lock()


class EvaluationTemplateResponse(BaseModel):
    """Evaluation template summary."""
    id: str
    display_name: str
    description: Optional[str] = None
    evaluators: List[str]
    dataset_items_count: int


class EvaluationTemplatesResponse(BaseModel):
    """List of evaluation templates."""
    templates: List[EvaluationTemplateResponse]
    count: int


class RunEvaluationRequest(BaseModel):
    """Request to run evaluations."""
    template_ids: List[str]
    agent_names: List[str]
    model_deployment_name: Optional[str] = None


class EvaluationRunResult(BaseModel):
    """Single evaluation run result."""
    evaluation_id: str
    evaluation_name: str
    agent_name: str
    eval_id: str
    run_id: str
    run_status: Optional[str] = None
    report_url: Optional[str] = None
    result_path: Optional[str] = None


class EvaluationRunResponse(BaseModel):
    """Response from running evaluations."""
    success: bool
    results: List[EvaluationRunResult]


class RecentRunResponse(BaseModel):
    """Recent evaluation run."""
    evaluation_id: str
    evaluation_name: str
    eval_id: str
    agent_name: str
    run_id: str
    run_status: str
    report_url: Optional[str] = None
    created_at: Any = None


class RecentRunsResponse(BaseModel):
    """List of recent evaluation runs."""
    runs: List[RecentRunResponse]
    count: int


def _progress_callback(current: int, total: int, message: str):
    """Callback for evaluation progress."""
    with _evaluation_lock:
        _evaluation_state["progress"] = current
        _evaluation_state["total"] = total
        _evaluation_state["message"] = message


def _log_callback(message: str):
    """Log callback for evaluations."""
    with _evaluation_lock:
        _evaluation_state["message"] = message


@router.get("/templates", response_model=EvaluationTemplatesResponse)
async def list_evaluation_templates():
    """List available evaluation templates."""
    try:
        loader = EvaluationTemplateLoader()
        # list_templates() returns List[EvaluationTemplate] directly
        loaded_templates = loader.list_templates()

        templates = []
        for template in loaded_templates:
            try:
                templates.append(EvaluationTemplateResponse(
                    id=template.id,
                    display_name=template.display_name,
                    description=template.description,
                    evaluators=[e.name for e in template.evaluators],
                    dataset_items_count=len(template.dataset_items),
                ))
            except Exception:
                continue

        return EvaluationTemplatesResponse(
            templates=templates,
            count=len(templates),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=RecentRunsResponse)
async def list_recent_runs(max_evals: int = 20, runs_per_eval: int = 10):
    """List recent evaluation runs."""
    try:
        engine = EvaluationEngine()
        runs = engine.list_recent_runs(max_evals=max_evals, runs_per_eval=runs_per_eval)

        run_responses = [
            RecentRunResponse(
                evaluation_id=r.get("evaluation_id", ""),
                evaluation_name=r.get("evaluation_name", ""),
                eval_id=r.get("eval_id", ""),
                agent_name=r.get("agent_name", ""),
                run_id=r.get("run_id", ""),
                run_status=r.get("run_status", ""),
                report_url=r.get("report_url"),
                created_at=r.get("created_at"),
            )
            for r in runs
        ]

        return RecentRunsResponse(
            runs=run_responses,
            count=len(run_responses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluations(request: RunEvaluationRequest):
    """Run evaluation templates against agents."""
    with _evaluation_lock:
        if _evaluation_state["running"]:
            raise HTTPException(status_code=409, detail="Evaluation already in progress")

    try:
        with _evaluation_lock:
            _evaluation_state["running"] = True
            _evaluation_state["progress"] = 0
            _evaluation_state["total"] = len(request.template_ids) * len(request.agent_names)
            _evaluation_state["message"] = "Starting evaluations..."
            _evaluation_state["results"] = None

        engine = EvaluationEngine()
        results = engine.run(
            template_ids=request.template_ids,
            agent_names=request.agent_names,
            model_deployment_name=request.model_deployment_name,
            progress_callback=_progress_callback,
            log_callback=_log_callback,
        )

        with _evaluation_lock:
            _evaluation_state["running"] = False
            _evaluation_state["results"] = results

        result_responses = [
            EvaluationRunResult(
                evaluation_id=r.get("evaluation_id", ""),
                evaluation_name=r.get("evaluation_name", ""),
                agent_name=r.get("agent_name", ""),
                eval_id=r.get("eval_id", ""),
                run_id=r.get("run_id", ""),
                run_status=r.get("run_status"),
                report_url=r.get("report_url"),
                result_path=r.get("result_path"),
            )
            for r in results
        ]

        return EvaluationRunResponse(
            success=True,
            results=result_responses,
        )

    except Exception as e:
        with _evaluation_lock:
            _evaluation_state["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
async def get_evaluation_progress():
    """Get evaluation progress."""
    with _evaluation_lock:
        return {
            "running": _evaluation_state["running"],
            "progress": _evaluation_state["progress"],
            "total": _evaluation_state["total"],
            "message": _evaluation_state["message"],
        }
