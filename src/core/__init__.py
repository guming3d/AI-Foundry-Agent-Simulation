"""
Core engine modules for Microsoft Foundry Agent Toolkit.

This module contains the business logic for:
- Azure SDK client management
- Agent CRUD operations
- Model discovery and deployment
- Simulation execution
- Metrics collection
"""

from .azure_client import AzureClientFactory, get_project_client, get_openai_client
from .agent_manager import AgentManager, create_agents_quick
from .model_manager import ModelManager, ModelInfo, ModelStatus, list_models, validate_model
from .metrics_collector import MetricsCollector, OperationMetric, GuardrailMetric
from .evaluation_engine import EvaluationEngine
from .simulation_engine import SimulationEngine, SimulationConfig

__all__ = [
    # Azure client
    "AzureClientFactory",
    "get_project_client",
    "get_openai_client",
    # Agent management
    "AgentManager",
    "create_agents_quick",
    # Model management
    "ModelManager",
    "ModelInfo",
    "ModelStatus",
    "list_models",
    "validate_model",
    # Metrics collection
    "MetricsCollector",
    "OperationMetric",
    "GuardrailMetric",
    # Evaluation engine
    "EvaluationEngine",
    # Simulation engine
    "SimulationEngine",
    "SimulationConfig",
]
