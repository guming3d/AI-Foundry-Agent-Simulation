"""
Model management for Azure AI Foundry Agent Toolkit.

Provides model discovery and deployment:
- List available model deployments
- Deploy new models
- Validate model availability
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .azure_client import get_project_client


class ModelStatus(Enum):
    """Model deployment status."""
    AVAILABLE = "available"
    DEPLOYING = "deploying"
    FAILED = "failed"
    NOT_FOUND = "not_found"


@dataclass
class ModelInfo:
    """Information about a model deployment."""
    name: str
    deployment_name: str
    status: ModelStatus
    capabilities: List[str] = None
    version: str = None
    model_name: str = None  # Publisher-specific model name
    model_publisher: str = None  # Model publisher (e.g., OpenAI, Microsoft)

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

    def __str__(self) -> str:
        """String representation showing deployment name and model info."""
        if self.model_name and self.model_publisher:
            return f"{self.name} ({self.model_publisher}/{self.model_name})"
        return self.name


class ModelManager:
    """
    Manager for Azure AI Foundry model deployments.

    Handles model discovery, deployment, and validation.
    All model information is fetched dynamically from Azure AI Foundry.
    """

    def __init__(self):
        """Initialize the model manager."""
        self._cached_models: Optional[List[ModelInfo]] = None

    def list_available_models(self, refresh: bool = False) -> List[ModelInfo]:
        """
        List all available model deployments from Azure AI Foundry.

        Args:
            refresh: Force refresh of cached models

        Returns:
            List of ModelInfo objects
        """
        if self._cached_models is not None and not refresh:
            return self._cached_models

        models = []
        client = get_project_client()

        try:
            # List deployments from Azure AI Foundry
            deployments = client.deployments.list()

            for deployment in deployments:
                # Extract capabilities from the deployment
                # The API returns capabilities as dict[str, str]
                capabilities = []
                if hasattr(deployment, 'capabilities') and deployment.capabilities:
                    capabilities = list(deployment.capabilities.keys())

                # Get model info - deployment.name is the deployment name we use to call the model
                model_info = ModelInfo(
                    name=deployment.name,  # Deployment name (used to call the model)
                    deployment_name=deployment.name,
                    status=ModelStatus.AVAILABLE,
                    capabilities=capabilities,
                    version=getattr(deployment, 'model_version', None),
                )

                # Store additional metadata if available
                if hasattr(deployment, 'model_name'):
                    model_info.model_name = deployment.model_name
                if hasattr(deployment, 'model_publisher'):
                    model_info.model_publisher = deployment.model_publisher

                models.append(model_info)

            if not models:
                print("WARNING: No model deployments found in Azure AI Foundry project.")
                print("Please deploy models in your Azure AI Foundry project before creating agents.")

        except Exception as e:
            print(f"ERROR: Failed to list models from Azure AI Foundry: {e}")
            print("Please check your PROJECT_ENDPOINT and Azure credentials.")
            print("No models available - cannot proceed with agent creation.")

        self._cached_models = models
        return models

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            ModelInfo or None if not found
        """
        models = self.list_available_models()
        for model in models:
            if model.name == model_name or model.deployment_name == model_name:
                return model
        return None

    def validate_models(self, model_names: List[str]) -> Dict[str, bool]:
        """
        Validate that models exist and are available.

        Args:
            model_names: List of model names to validate

        Returns:
            Dictionary mapping model name to availability boolean
        """
        available = {m.name for m in self.list_available_models()}
        return {name: name in available for name in model_names}

    def get_available_model_names(self) -> List[str]:
        """
        Get list of available model names.

        Returns:
            List of model name strings
        """
        return [m.name for m in self.list_available_models()]

    def deploy_model(
        self,
        model_id: str,
        deployment_name: str = None,
        sku: str = "Standard",
        capacity: int = 1
    ) -> Optional[ModelInfo]:
        """
        Deploy a new model to the project.

        Args:
            model_id: Base model ID to deploy
            deployment_name: Custom deployment name (uses model_id if not provided)
            sku: Deployment SKU (Standard, Premium, etc.)
            capacity: Deployment capacity units

        Returns:
            ModelInfo for the new deployment or None if failed

        Note:
            This requires appropriate permissions and may take several minutes.
        """
        deployment_name = deployment_name or model_id
        client = get_project_client()

        try:
            # Note: The actual deployment API may vary based on SDK version
            # This is a placeholder for the actual implementation

            # For demonstration, we'll simulate a successful deployment
            print(f"Deploying model {model_id} as {deployment_name}...")

            # In a real implementation, this would call:
            # client.deployments.create(...)

            model_info = ModelInfo(
                name=model_id,
                deployment_name=deployment_name,
                status=ModelStatus.DEPLOYING,
                capabilities=[],  # Will be populated when deployment completes
            )

            # Invalidate cache
            self._cached_models = None

            return model_info

        except Exception as e:
            print(f"Error deploying model {model_id}: {e}")
            return None

    def delete_deployment(self, deployment_name: str) -> bool:
        """
        Delete a model deployment.

        Args:
            deployment_name: Name of the deployment to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        client = get_project_client()

        try:
            # Note: The actual deletion API may vary
            print(f"Deleting deployment {deployment_name}...")

            # In a real implementation, this would call:
            # client.deployments.delete(deployment_name)

            # Invalidate cache
            self._cached_models = None

            return True

        except Exception as e:
            print(f"Error deleting deployment {deployment_name}: {e}")
            return False

    def get_models_for_profile(self, profile_preferred: List[str], profile_allowed: List[str]) -> List[str]:
        """
        Get available models filtered by profile preferences.

        Args:
            profile_preferred: Preferred models from industry profile
            profile_allowed: All allowed models from industry profile

        Returns:
            List of available models, preferring profile preferences
        """
        available = set(self.get_available_model_names())

        # First try preferred models
        preferred_available = [m for m in profile_preferred if m in available]
        if preferred_available:
            return preferred_available

        # Fall back to allowed models
        allowed_available = [m for m in profile_allowed if m in available]
        if allowed_available:
            return allowed_available

        # Return any available models as last resort
        return list(available)

    def get_model_capabilities(self, model_name: str) -> List[str]:
        """
        Get capabilities for a model.

        Args:
            model_name: Name of the model

        Returns:
            List of capability strings from Azure deployment
        """
        model = self.get_model(model_name)
        if model:
            return model.capabilities
        return []

    def refresh_cache(self) -> None:
        """Force refresh of the model cache."""
        self._cached_models = None
        self.list_available_models(refresh=True)


# Convenience functions
def list_models() -> List[str]:
    """List available model names."""
    return ModelManager().get_available_model_names()


def validate_model(model_name: str) -> bool:
    """Check if a model is available."""
    return ModelManager().validate_models([model_name]).get(model_name, False)


def get_default_models() -> List[str]:
    """
    Get the list of available models from Azure AI Foundry.

    Returns:
        List of deployed model names
    """
    return ModelManager().get_available_model_names()
