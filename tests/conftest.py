from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_stubbed_dependencies() -> None:
    if "azure" not in sys.modules:
        azure = types.ModuleType("azure")
        identity = types.ModuleType("azure.identity")
        ai = types.ModuleType("azure.ai")
        projects = types.ModuleType("azure.ai.projects")
        projects_models = types.ModuleType("azure.ai.projects.models")

        class DefaultAzureCredential:
            pass

        class AIProjectClient:
            def __init__(self, *args, **kwargs):
                pass

            def get_openai_client(self):
                return None

        class PromptAgentDefinition:
            def __init__(self, *args, **kwargs):
                pass

        identity.DefaultAzureCredential = DefaultAzureCredential
        projects.AIProjectClient = AIProjectClient
        projects_models.PromptAgentDefinition = PromptAgentDefinition

        azure.identity = identity
        azure.ai = ai
        ai.projects = projects

        sys.modules["azure"] = azure
        sys.modules["azure.identity"] = identity
        sys.modules["azure.ai"] = ai
        sys.modules["azure.ai.projects"] = projects
        sys.modules["azure.ai.projects.models"] = projects_models

    if "openai" not in sys.modules:
        openai = types.ModuleType("openai")
        openai_types = types.ModuleType("openai.types")
        openai_eval = types.ModuleType("openai.types.eval_create_params")

        class DataSourceConfigCustom:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        openai_eval.DataSourceConfigCustom = DataSourceConfigCustom
        openai_types.eval_create_params = openai_eval
        openai.types = openai_types

        sys.modules["openai"] = openai
        sys.modules["openai.types"] = openai_types
        sys.modules["openai.types.eval_create_params"] = openai_eval


_ensure_stubbed_dependencies()
