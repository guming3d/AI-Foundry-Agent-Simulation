"""
Industry template endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.templates.template_loader import TemplateLoader, TemplateLoadError, TemplateValidationError

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateAgentType(BaseModel):
    """Agent type in a template."""
    id: str
    name: str
    department: str
    description: Optional[str] = None


class TemplateSummary(BaseModel):
    """Summary of a template."""
    id: str
    name: str
    description: Optional[str] = None
    version: str
    agent_types_count: int
    departments_count: int


class TemplateDetail(BaseModel):
    """Detailed template information."""
    id: str
    name: str
    description: Optional[str] = None
    version: str
    organization_prefix: str
    agent_types: List[TemplateAgentType]
    departments: List[Dict[str, str]]
    preferred_models: List[str]
    allowed_models: List[str]


class TemplateListResponse(BaseModel):
    """List of templates response."""
    templates: List[TemplateSummary]
    count: int


@router.get("", response_model=TemplateListResponse)
async def list_templates():
    """List available industry templates."""
    try:
        loader = TemplateLoader()
        template_ids = loader.list_templates()

        templates = []
        for tid in template_ids:
            try:
                profile = loader.load_template(tid)
                templates.append(TemplateSummary(
                    id=profile.metadata.id,
                    name=profile.metadata.name,
                    description=profile.metadata.description,
                    version=profile.metadata.version,
                    agent_types_count=len(profile.agent_types),
                    departments_count=len(profile.organization.departments),
                ))
            except Exception:
                continue

        return TemplateListResponse(
            templates=templates,
            count=len(templates),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(template_id: str):
    """Get detailed information about a template."""
    try:
        loader = TemplateLoader()
        profile = loader.load_template(template_id)

        agent_types = [
            TemplateAgentType(
                id=at.id,
                name=at.name,
                department=at.department,
                description=at.description,
            )
            for at in profile.agent_types
        ]

        departments = [
            {"name": d.name, "code": d.code}
            for d in profile.organization.departments
        ]

        return TemplateDetail(
            id=profile.metadata.id,
            name=profile.metadata.name,
            description=profile.metadata.description,
            version=profile.metadata.version,
            organization_prefix=profile.organization.prefix,
            agent_types=agent_types,
            departments=departments,
            preferred_models=profile.models.preferred,
            allowed_models=profile.models.allowed,
        )
    except TemplateLoadError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
