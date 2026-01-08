#!/usr/bin/env python3
"""
Quick test script to check Azure AI Foundry connectivity.
Run this to diagnose connection issues before using the TUI.
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    print("=" * 60)
    print("Azure AI Foundry Connection Test")
    print("=" * 60)

    # Check environment
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    print(f"\n1. Checking environment...")
    print(f"   PROJECT_ENDPOINT: {endpoint or 'NOT SET'}")

    if not endpoint:
        print("   [ERROR] PROJECT_ENDPOINT not set in .env file!")
        return False

    # Test credential
    print(f"\n2. Testing Azure credential...")
    start = time.time()
    try:
        from azure.identity import DefaultAzureCredential
        print("   Creating DefaultAzureCredential...")
        credential = DefaultAzureCredential()
        print(f"   Credential created in {time.time() - start:.1f}s")
    except Exception as e:
        print(f"   [ERROR] Credential failed: {e}")
        print("\n   Try running: az login")
        return False

    # Test project client
    print(f"\n3. Testing AIProjectClient...")
    start = time.time()
    try:
        from azure.ai.projects import AIProjectClient
        print(f"   Connecting to {endpoint}...")
        client = AIProjectClient(endpoint=endpoint, credential=credential)
        print(f"   Client created in {time.time() - start:.1f}s")
    except Exception as e:
        print(f"   [ERROR] Client failed: {e}")
        return False

    # Test OpenAI client
    print(f"\n4. Testing OpenAI client...")
    start = time.time()
    try:
        print("   Getting OpenAI client...")
        openai_client = client.get_openai_client()
        print(f"   OpenAI client ready in {time.time() - start:.1f}s")
    except Exception as e:
        print(f"   [ERROR] OpenAI client failed: {e}")
        return False

    # Test conversation
    print(f"\n5. Testing conversation creation...")
    start = time.time()
    try:
        print("   Creating conversation...")
        conversation = openai_client.conversations.create()
        print(f"   Conversation created in {time.time() - start:.1f}s")
        print(f"   Conversation ID: {conversation.id}")
    except Exception as e:
        print(f"   [ERROR] Conversation failed: {e}")
        return False

    # Test agent call (optional - requires an agent name)
    print(f"\n6. Testing agent call...")

    # Try to load agents from CSV
    agents_csv = "created_agents_results.csv"
    if os.path.exists(agents_csv):
        import csv
        with open(agents_csv, 'r') as f:
            reader = csv.DictReader(f)
            agents = list(reader)

        if agents:
            agent_name = agents[0].get('name', agents[0].get('agent_name'))
            print(f"   Calling agent: {agent_name}")
            start = time.time()
            try:
                response = openai_client.responses.create(
                    conversation=conversation.id,
                    extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
                    input="Hello, can you help me?",
                )
                print(f"   Response received in {time.time() - start:.1f}s")
                print(f"   Response: {response.output_text[:100]}...")
            except Exception as e:
                print(f"   [ERROR] Agent call failed: {e}")
                return False
        else:
            print("   [SKIP] No agents in CSV")
    else:
        print(f"   [SKIP] {agents_csv} not found")

    print("\n" + "=" * 60)
    print("All tests passed! Azure connection is working.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
