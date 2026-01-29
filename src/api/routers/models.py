"""
Model listing endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.model_manager import ModelManager, ModelInfo

router = APIRouter(prefix="/models", tags=["models"])


class ModelResponse(BaseModel):
    """Single model response."""
    name: str
    deployment_name: str
    status: str
    capabilities: List[str] = []
    version: Optional[str] = None
    model_name: Optional[str] = None
    model_publisher: Optional[str] = None


class ModelListResponse(BaseModel):
    """List of models response."""
    models: List[ModelResponse]
    count: int


@router.get("", response_model=ModelListResponse)
async def list_models(refresh: bool = False):
    """
    List available model deployments.

    Args:
        refresh: Force refresh of cached models
    """
    try:
        manager = ModelManager()
        models = manager.list_available_models(refresh=refresh)

        model_responses = [
            ModelResponse(
                name=m.name,
                deployment_name=m.deployment_name,
                status=m.status.value,
                capabilities=m.capabilities,
                version=m.version,
                model_name=m.model_name,
                model_publisher=m.model_publisher,
            )
            for m in models
        ]

        return ModelListResponse(
            models=model_responses,
            count=len(model_responses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_name}", response_model=ModelResponse)
async def get_model(model_name: str):
    """Get details for a specific model."""
    try:
        manager = ModelManager()
        model = manager.get_model(model_name)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        return ModelResponse(
            name=model.name,
            deployment_name=model.deployment_name,
            status=model.status.value,
            capabilities=model.capabilities,
            version=model.version,
            model_name=model.model_name,
            model_publisher=model.model_publisher,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
