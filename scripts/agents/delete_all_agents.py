#!/usr/bin/env python3
"""
Delete All Agents from Azure AI Foundry Project

This script lists and deletes all agents from the Azure AI Foundry project
specified in the .env file.

Usage:
    # Dry run - list agents without deleting
    python delete_all_agents.py --dry-run

    # Delete all agents (with confirmation)
    python delete_all_agents.py

    # Delete all agents without confirmation prompt
    python delete_all_agents.py --yes

    # Delete specific agents by name pattern
    python delete_all_agents.py --pattern "ORG01-*"
"""

import os
import sys
import argparse
import fnmatch
from datetime import datetime
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()


def get_project_client():
    """Initialize and return the Azure AI Project client."""
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        raise SystemExit("Missing PROJECT_ENDPOINT. Set it in your environment or .env file.")

    return AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())


def list_all_agents(client):
    """List all agents in the project."""
    agents = []
    try:
        for agent in client.agents.list():
            agents.append({
                'id': agent.id,
                'name': agent.name,
                'version': getattr(agent, 'version', None),
                'model': getattr(agent, 'model', None),
            })
    except Exception as e:
        print(f"Error listing agents: {e}")
        raise
    return agents


def delete_agent(client, agent_name):
    """Delete a specific agent by name."""
    try:
        client.agents.delete(agent_name=agent_name)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='Delete all agents from Azure AI Foundry project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='List agents without deleting them')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')
    parser.add_argument('--pattern', type=str, default=None,
                        help='Only delete agents matching this pattern (e.g., "ORG01-*")')
    parser.add_argument('--output', type=str, default=None,
                        help='Save deletion results to CSV file')

    args = parser.parse_args()

    print("=" * 80)
    print("Azure AI Foundry - Delete Agents")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'DELETE'}")
    if args.pattern:
        print(f"Pattern filter: {args.pattern}")
    print("=" * 80)
    print()

    # Initialize client
    print("Connecting to Azure AI Foundry...")
    client = get_project_client()
    print("Connected successfully.\n")

    # List all agents
    print("Fetching agent list...")
    all_agents = list_all_agents(client)
    print(f"Found {len(all_agents)} total agents in the project.\n")

    if not all_agents:
        print("No agents found. Nothing to delete.")
        return

    # Filter by pattern if specified
    if args.pattern:
        agents_to_delete = [a for a in all_agents if fnmatch.fnmatch(a['name'], args.pattern)]
        print(f"Agents matching pattern '{args.pattern}': {len(agents_to_delete)}")
    else:
        agents_to_delete = all_agents

    if not agents_to_delete:
        print("No agents match the specified criteria. Nothing to delete.")
        return

    # Display agents
    print("\nAgents to be deleted:")
    print("-" * 80)
    print(f"{'#':<4} {'Agent Name':<50} {'ID':<30}")
    print("-" * 80)
    for i, agent in enumerate(agents_to_delete, 1):
        print(f"{i:<4} {agent['name']:<50} {agent['id']:<30}")
    print("-" * 80)
    print(f"Total: {len(agents_to_delete)} agents")
    print()

    # Dry run mode - just list and exit
    if args.dry_run:
        print("DRY RUN mode - no agents were deleted.")
        print("Run without --dry-run to actually delete the agents.")
        return

    # Confirmation prompt
    if not args.yes:
        print(f"\n*** WARNING: This will permanently delete {len(agents_to_delete)} agents! ***")
        confirmation = input("\nType 'DELETE' to confirm deletion: ")
        if confirmation != 'DELETE':
            print("Deletion cancelled.")
            return

    # Delete agents
    print("\nDeleting agents...")
    print("-" * 80)

    deleted = []
    failed = []

    for i, agent in enumerate(agents_to_delete, 1):
        agent_name = agent['name']
        print(f"[{i}/{len(agents_to_delete)}] Deleting {agent_name}...", end=" ")

        success, error = delete_agent(client, agent_name)

        if success:
            print("OK")
            deleted.append(agent)
        else:
            print(f"FAILED ({error})")
            failed.append({**agent, 'error': error})

    # Summary
    print("\n" + "=" * 80)
    print("Deletion Summary")
    print("=" * 80)
    print(f"Successfully deleted: {len(deleted)}")
    print(f"Failed: {len(failed)}")
    print("=" * 80)

    if failed:
        print("\nFailed deletions:")
        for agent in failed:
            print(f"  - {agent['name']}: {agent['error']}")

    # Save results to CSV if requested
    if args.output:
        import csv
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'id', 'status', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for agent in deleted:
                writer.writerow({'name': agent['name'], 'id': agent['id'], 'status': 'deleted', 'error': ''})
            for agent in failed:
                writer.writerow({'name': agent['name'], 'id': agent['id'], 'status': 'failed', 'error': agent['error']})
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
