import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

load_dotenv()

project_client = AIProjectClient(
    #endpoint=os.environ["PROJECT_ENDPOINT"],
    endpoint='https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane',
    credential=DefaultAzureCredential(),
)

agent = project_client.agents.create_version(
    # agent_name=os.environ["AGENT_NAME"],
    agent_name="my-agent-from-sdk",
    definition=PromptAgentDefinition(
        # model=os.environ["MODEL_DEPLOYMENT_NAME"],
        model="gpt-4.1-mini",
        instructions="You are a helpful assistant that answers general questions",
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
