"""
Agent CRUD endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..schemas.agents import (
    AgentResponse,
    AgentListResponse,
    CreateAgentsRequest,
    CreateAgentsResponse,
    CreatedAgentInfo,
    FailedAgentInfo,
    DeleteAgentsResponse,
)
from ..websocket import manager as ws_manager
from src.core.agent_manager import AgentManager
from src.templates.template_loader import TemplateLoader

router = APIRouter(prefix="/agents", tags=["agents"])

# Track creation progress
_creation_progress = {"current": 0, "total": 0, "message": "", "running": False}

# Track deletion progress
_deletion_progress = {"current": 0, "total": 0, "message": "", "running": False}


def _progress_callback(current: int, total: int, message: str):
    """Callback for agent creation progress."""
    _creation_progress["current"] = current
    _creation_progress["total"] = total
    _creation_progress["message"] = message


def _deletion_progress_callback(current: int, total: int, message: str):
    """Callback for agent deletion progress."""
    _deletion_progress["current"] = current
    _deletion_progress["total"] = total
    _deletion_progress["message"] = message


@router.get("", response_model=AgentListResponse)
async def list_agents():
    """List all agents in the project."""
    try:
        manager = AgentManager()
        agents = manager.list_agents()

        agent_responses = [
            AgentResponse(
                name=a.get("name", ""),
                id=a.get("id", ""),
                version=a.get("version"),
                model=a.get("model"),
            )
            for a in agents
        ]

        return AgentListResponse(
            agents=agent_responses,
            count=len(agent_responses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=CreateAgentsResponse)
async def create_agents(request: CreateAgentsRequest, background_tasks: BackgroundTasks):
    """
    Create agents from an industry profile.

    This is a blocking operation that creates agents synchronously.
    """
    if _creation_progress["running"]:
        raise HTTPException(status_code=409, detail="Agent creation already in progress")

    try:
        # Load the profile
        loader = TemplateLoader()
        profile = loader.load_template(request.profile_id)

        # Create agents
        _creation_progress["running"] = True
        _creation_progress["current"] = 0
        _creation_progress["total"] = len(profile.agent_types) * request.agent_count * request.org_count

        manager = AgentManager(models=request.models)
        result = manager.create_agents_from_profile(
            profile=profile,
            agent_count=request.agent_count,
            org_count=request.org_count,
            models=request.models,
            progress_callback=_progress_callback,
        )

        _creation_progress["running"] = False

        # Save to CSV
        if result.created:
            manager.save_agents_to_csv(result.created)
        if result.failed:
            manager.save_failed_to_csv(result.failed)

        created_info = [
            CreatedAgentInfo(
                agent_id=a.agent_id,
                name=a.name,
                azure_id=a.azure_id,
                version=a.version,
                model=a.model,
                org_id=a.org_id,
            )
            for a in result.created
        ]

        failed_info = [
            FailedAgentInfo(
                agent_id=f.get("agent_id", ""),
                name=f.get("name", ""),
                org_id=f.get("org_id", ""),
                agent_type=f.get("agent_type", ""),
                error=f.get("error", ""),
            )
            for f in result.failed
        ]

        return CreateAgentsResponse(
            success=len(result.failed) == 0,
            created=created_info,
            failed=failed_info,
            total_attempted=result.total_attempted,
            created_count=len(result.created),
            failed_count=len(result.failed),
        )

    except Exception as e:
        _creation_progress["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
async def get_creation_progress():
    """Get agent creation progress."""
    return {
        "running": _creation_progress["running"],
        "current": _creation_progress["current"],
        "total": _creation_progress["total"],
        "message": _creation_progress["message"],
    }


@router.get("/deletion-progress")
async def get_deletion_progress():
    """Get agent deletion progress."""
    return {
        "running": _deletion_progress["running"],
        "current": _deletion_progress["current"],
        "total": _deletion_progress["total"],
        "message": _deletion_progress["message"],
    }


@router.delete("", response_model=DeleteAgentsResponse)
async def delete_all_agents():
    """Delete all agents in the project."""
    if _deletion_progress["running"]:
        raise HTTPException(status_code=409, detail="Agent deletion already in progress")

    try:
        _deletion_progress["running"] = True
        _deletion_progress["current"] = 0
        _deletion_progress["total"] = 0

        manager = AgentManager()
        result = manager.delete_all_agents(progress_callback=_deletion_progress_callback)

        _deletion_progress["running"] = False

        return DeleteAgentsResponse(
            success=result["failed_count"] == 0,
            deleted_count=result["deleted_count"],
            failed_count=result["failed_count"],
            total=result["total"],
            message=f"Deleted {result['deleted_count']} of {result['total']} agents",
        )
    except Exception as e:
        _deletion_progress["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_name}")
async def delete_agent(agent_name: str):
    """Delete a specific agent by name."""
    try:
        manager = AgentManager()
        success = manager.delete_agent(agent_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to delete agent: {agent_name}")

        return {"success": True, "message": f"Agent {agent_name} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
