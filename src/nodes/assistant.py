"""Node: LLM assistant — the core chat node.

Loads tenant config, builds the system prompt, binds tools,
and invokes the model. Uses Command for routing: if the LLM
makes tool calls → go to "tools", otherwise → END.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.llm_provider import create_llm
from src.config.tenant_config import get_tenant
from src.state.agent_state import SalesAgentState
from src.tools import ALL_TOOLS


def _build_system_prompt(tenant_id: str) -> str:
    """Build a system prompt from the tenant's config."""
    tc = get_tenant(tenant_id)
    agent = tc.agent

    products_hint = (
        "You have tools to search products, find promotions, "
        "send product images, and find similar items by image description. "
        "USE THESE TOOLS — do not invent products."
    )

    return (
        f"You are {agent.name}, a {agent.role} at {tc.business_name}.\n\n"
        f"{agent.personality}\n\n"
        f"## Rules\n"
        + "\n".join(f"- {r}" for r in agent.rules)
        + f"\n\n## Important\n{products_hint}\n"
        f"Language: {tc.language}\n"
    )


async def assistant_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command[Literal["tools", "__end__"]]:
    """Invoke the LLM and route based on whether it made tool calls."""
    tenant_id = config["configurable"]["tenant_id"]
    tc = get_tenant(tenant_id)

    # Create provider-agnostic LLM from tenant config
    model = create_llm(tc).bind_tools(ALL_TOOLS)

    # Prepare messages: system prompt + conversation history
    system = SystemMessage(content=_build_system_prompt(tenant_id))
    messages = [system] + state["messages"]

    # Invoke
    response = await model.ainvoke(messages, config=config)

    # Route: tool calls → tools node, otherwise → end
    if response.tool_calls:
        return Command(
            update={"messages": [response]},
            goto="tools",
        )

    return Command(
        update={"messages": [response]},
        goto="__end__",
    )
