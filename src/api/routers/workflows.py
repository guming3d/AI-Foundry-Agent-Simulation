"""
Workflow endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.workflow_manager import WorkflowManager
from src.templates.template_loader import TemplateLoader

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Track creation progress
_creation_progress = {"current": 0, "total": 0, "message": "", "running": False}

# Track deletion progress
_deletion_progress = {"current": 0, "total": 0, "message": "", "running": False}


class WorkflowResponse(BaseModel):
    """Single workflow response."""
    name: str
    id: str
    version: Optional[int] = None


class WorkflowListResponse(BaseModel):
    """List of workflows response."""
    workflows: List[WorkflowResponse]
    count: int


class WorkflowTemplateRole(BaseModel):
    """Role in a workflow template."""
    id: str
    name: str
    agent_type_id: Optional[str] = None
    agent_type_name: Optional[str] = None


class WorkflowTemplate(BaseModel):
    """Workflow template definition."""
    id: str
    name: str
    description: Optional[str] = None
    pattern: str
    roles: List[WorkflowTemplateRole]


class WorkflowTemplatesResponse(BaseModel):
    """List of workflow templates response."""
    templates: List[WorkflowTemplate]
    count: int


class CreateWorkflowsRequest(BaseModel):
    """Request to create workflows."""
    profile_id: str
    template_ids: List[str]
    workflows_per_template: int = 1
    org_count: int = 1
    models: List[str]


class CreatedWorkflowInfo(BaseModel):
    """Info about a created workflow."""
    name: str
    azure_id: str
    version: int
    org_id: str
    template_id: str
    template_name: str
    agent_names: List[str]


class CreateWorkflowsResponse(BaseModel):
    """Response from workflow creation."""
    success: bool
    created: List[CreatedWorkflowInfo] = []
    failed: List[Dict[str, Any]] = []
    created_count: int
    failed_count: int


class DeleteWorkflowsResponse(BaseModel):
    """Response from workflow deletion."""
    success: bool
    deleted_count: int
    failed_count: int
    total: int
    message: str


def _progress_callback(current: int, total: int, message: str):
    """Callback for workflow creation progress."""
    _creation_progress["current"] = current
    _creation_progress["total"] = total
    _creation_progress["message"] = message


def _deletion_progress_callback(current: int, total: int, message: str):
    """Callback for workflow deletion progress."""
    _deletion_progress["current"] = current
    _deletion_progress["total"] = total
    _deletion_progress["message"] = message


@router.get("", response_model=WorkflowListResponse)
async def list_workflows():
    """List all workflows in the project."""
    try:
        manager = WorkflowManager()
        workflows = manager.list_workflows()

        workflow_responses = [
            WorkflowResponse(
                name=w.get("name", ""),
                id=w.get("id", ""),
                version=w.get("version"),
            )
            for w in workflows
        ]

        return WorkflowListResponse(
            workflows=workflow_responses,
            count=len(workflow_responses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=WorkflowTemplatesResponse)
async def get_workflow_templates(profile_id: str):
    """Get available workflow templates for a profile."""
    try:
        loader = TemplateLoader()
        profile = loader.load_template(profile_id)

        manager = WorkflowManager()
        templates = manager.build_templates(profile)

        template_responses = []
        for t in templates:
            roles = [
                WorkflowTemplateRole(
                    id=r.id,
                    name=r.name,
                    agent_type_id=r.agent_type.id if r.agent_type else None,
                    agent_type_name=r.agent_type.name if r.agent_type else None,
                )
                for r in t.roles
            ]
            template_responses.append(WorkflowTemplate(
                id=t.id,
                name=t.name,
                description=t.description,
                pattern=t.pattern,
                roles=roles,
            ))

        return WorkflowTemplatesResponse(
            templates=template_responses,
            count=len(template_responses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=CreateWorkflowsResponse)
async def create_workflows(request: CreateWorkflowsRequest):
    """Create workflows from templates."""
    if _creation_progress["running"]:
        raise HTTPException(status_code=409, detail="Workflow creation already in progress")

    try:
        loader = TemplateLoader()
        profile = loader.load_template(request.profile_id)

        _creation_progress["running"] = True

        manager = WorkflowManager(models=request.models)
        result = manager.create_workflows_from_profile(
            profile=profile,
            template_ids=request.template_ids,
            workflows_per_template=request.workflows_per_template,
            org_count=request.org_count,
            models=request.models,
            progress_callback=_progress_callback,
        )

        _creation_progress["running"] = False

        created_info = [
            CreatedWorkflowInfo(
                name=w.name,
                azure_id=w.azure_id,
                version=w.version,
                org_id=w.org_id,
                template_id=w.template_id,
                template_name=w.template_name,
                agent_names=w.agent_names,
            )
            for w in result.created
        ]

        return CreateWorkflowsResponse(
            success=len(result.failed) == 0,
            created=created_info,
            failed=result.failed,
            created_count=len(result.created),
            failed_count=len(result.failed),
        )

    except Exception as e:
        _creation_progress["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
async def get_creation_progress():
    """Get workflow creation progress."""
    return {
        "running": _creation_progress["running"],
        "current": _creation_progress["current"],
        "total": _creation_progress["total"],
        "message": _creation_progress["message"],
    }


@router.get("/deletion-progress")
async def get_deletion_progress():
    """Get workflow deletion progress."""
    return {
        "running": _deletion_progress["running"],
        "current": _deletion_progress["current"],
        "total": _deletion_progress["total"],
        "message": _deletion_progress["message"],
    }


@router.delete("", response_model=DeleteWorkflowsResponse)
async def delete_all_workflows():
    """Delete all workflow agents in the project."""
    if _deletion_progress["running"]:
        raise HTTPException(status_code=409, detail="Workflow deletion already in progress")

    try:
        _deletion_progress["running"] = True
        _deletion_progress["current"] = 0
        _deletion_progress["total"] = 0

        manager = WorkflowManager()
        result = manager.delete_all_workflows(progress_callback=_deletion_progress_callback)

        _deletion_progress["running"] = False

        return DeleteWorkflowsResponse(
            success=result["failed_count"] == 0,
            deleted_count=result["deleted_count"],
            failed_count=result["failed_count"],
            total=result["total"],
            message=f"Deleted {result['deleted_count']} of {result['total']} workflows",
        )
    except Exception as e:
        _deletion_progress["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workflow_name}")
async def delete_workflow(workflow_name: str):
    """Delete a specific workflow by name."""
    try:
        manager = WorkflowManager()
        success = manager.delete_workflow(workflow_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to delete workflow: {workflow_name}")

        return {"success": True, "message": f"Workflow {workflow_name} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
