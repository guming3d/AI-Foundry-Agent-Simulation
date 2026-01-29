"""
Status and health check endpoints.
"""

from fastapi import APIRouter

from ..schemas.common import StatusResponse
from src.core.model_manager import ModelManager
from src.core.agent_manager import AgentManager
from src.core.workflow_manager import WorkflowManager
from src.core.daemon_service import DaemonService
from src.templates.template_loader import TemplateLoader

router = APIRouter(tags=["status"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status with counts."""
    try:
        model_manager = ModelManager()
        models = model_manager.list_available_models()
        models_count = len(models)
    except Exception:
        models_count = 0

    try:
        agent_manager = AgentManager()
        agents = agent_manager.list_agents()
        agents_count = len(agents)
    except Exception:
        agents_count = 0

    try:
        workflow_manager = WorkflowManager()
        workflows = workflow_manager.list_workflows()
        workflows_count = len(workflows)
    except Exception:
        workflows_count = 0

    try:
        daemon_service = DaemonService()
        daemon_running = daemon_service.is_running()
    except Exception:
        daemon_running = False

    try:
        template_loader = TemplateLoader()
        templates = template_loader.list_templates()
        templates_count = len(templates)
    except Exception:
        templates_count = 0

    return StatusResponse(
        status="ok",
        models_count=models_count,
        agents_count=agents_count,
        workflows_count=workflows_count,
        daemon_running=daemon_running,
        templates_count=templates_count,
    )
