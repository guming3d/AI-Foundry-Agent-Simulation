import os
import csv
import random
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

load_dotenv()

# Model selection pool
AVAILABLE_MODELS = [
    "gpt-4.1-mini",
    "gpt-5.2-chat",
    "grok-4-fast-non-reasoning",
    "gpt-5.1-codex",
    "grok-4"
]

# Initialize the project client
endpoint = os.environ.get("PROJECT_ENDPOINT")
if not endpoint:
    raise SystemExit("Missing PROJECT_ENDPOINT. Set it in your environment or .env file.")

project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

def create_agent_name(base_name, org_id, agent_id):
    """Create a descriptive agent name."""
    # Remove 'Agent' suffix if present and clean up the name
    clean_name = base_name.replace(' Agent', '').strip()
    return f"{org_id}-{clean_name.replace(' ', '')}-{agent_id}"

def create_agent_instructions(purpose, tools, owner):
    """Create detailed instructions for the agent."""
    return f"""You are a specialized AI agent for {purpose}.

Your capabilities include:
- Tools: {tools}
- Department: {owner}

Please assist users with tasks related to your area of expertise while maintaining professional standards and following all applicable policies."""

def batch_create_agents(csv_file_path):
    """Read CSV and create agents for each row."""
    created_agents = []
    failed_agents = []

    with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            agent_id = row['agent_id']
            org_id = row['org_id']
            name = row['name']
            purpose = row['purpose']
            tools = row['tools']
            owner = row['owner']

            # Randomly select a model
            selected_model = random.choice(AVAILABLE_MODELS)

            # Create descriptive agent name
            agent_name = create_agent_name(name, org_id, agent_id)

            # Create detailed instructions
            instructions = create_agent_instructions(purpose, tools, owner)

            try:
                print(f"Creating agent: {agent_name} with model {selected_model}...")

                agent = project_client.agents.create_version(
                    agent_name=agent_name,
                    definition=PromptAgentDefinition(
                        model=selected_model,
                        instructions=instructions,
                    ),
                )

                created_agents.append({
                    'agent_id': agent_id,
                    'name': agent_name,
                    'azure_id': agent.id,
                    'version': agent.version,
                    'model': selected_model,
                    'org_id': org_id
                })

                print(f"✓ Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version}, model: {selected_model})")

            except Exception as e:
                print(f"✗ Failed to create agent {agent_name}: {str(e)}")
                failed_agents.append({
                    'agent_id': agent_id,
                    'name': agent_name,
                    'error': str(e)
                })

    return created_agents, failed_agents

def save_results(created_agents, failed_agents):
    """Save the results to CSV files."""
    # Save successfully created agents
    if created_agents:
        with open('created_agents_results.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['agent_id', 'name', 'azure_id', 'version', 'model', 'org_id']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(created_agents)
        print(f"\n✓ Successfully created {len(created_agents)} agents. Results saved to 'created_agents_results.csv'")

    # Save failed agents
    if failed_agents:
        with open('failed_agents_results.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['agent_id', 'name', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed_agents)
        print(f"✗ {len(failed_agents)} agents failed. Results saved to 'failed_agents_results.csv'")

if __name__ == "__main__":
    csv_file = "contoso_ai_control_plane_demo(agents).csv"

    print("=" * 80)
    print("Batch Agent Creation Script")
    print("=" * 80)
    print(f"CSV File: {csv_file}")
    print(f"Available Models: {', '.join(AVAILABLE_MODELS)}")
    print("=" * 80)
    print()

    created_agents, failed_agents = batch_create_agents(csv_file)

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total agents processed: {len(created_agents) + len(failed_agents)}")
    print(f"Successfully created: {len(created_agents)}")
    print(f"Failed: {len(failed_agents)}")
    print("=" * 80)

    save_results(created_agents, failed_agents)
