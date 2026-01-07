from __future__ import annotations

from .types import GeneratedAgent


def build_agent_instructions(agent: GeneratedAgent) -> str:
    return (
        f"You are a specialized AI agent for {agent.purpose}.\n\n"
        "Your capabilities include:\n"
        f"- Tools: {agent.tools}\n"
        f"- Department: {agent.owner}\n\n"
        "Please assist users with tasks related to your area of expertise while maintaining professional "
        "standards and following all applicable policies."
    )

