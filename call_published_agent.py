# Before running the sample:
#    pip install --pre azure-ai-projects>=2.0.0b1
#    pip install azure-identity

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# ORG01-FinanceAnalyst-AG009
# https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane/applications/ORG01-FinanceAnalyst-AG009/protocols/openai/responses?api-version=2025-11-15-preview
# https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane/applications/ORG01-FinanceAnalyst-AG009/protocols/activityprotocol?api-version=2025-11-15-preview
import os

myEndpoint = os.environ.get("PROJECT_ENDPOINT")
if not myEndpoint:
    raise SystemExit("Missing PROJECT_ENDPOINT. Set it in your environment or .env file.")

project_client = AIProjectClient(
    endpoint=myEndpoint,
    credential=DefaultAzureCredential(),
)

myAgent = "ORG01-FinanceAnalyst-AG009"
# Get an existing agent
agent = project_client.agents.get(agent_name=myAgent)
print(f"Retrieved agent: {agent.name}")

openai_client = project_client.get_openai_client()

# Reference the agent to get a response
response = openai_client.responses.create(
    input=[{"role": "user", "content": "Tell me what you can help with."}],
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)

print(f"Response output: {response.output_text}")


