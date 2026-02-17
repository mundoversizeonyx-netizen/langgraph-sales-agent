"""LLM provider factory.

Clean, modular provider system. Each tenant picks their provider
and model in config.yaml. Adding a new provider = one elif branch.

Supported providers:
  - openai   → ChatOpenAI  (gpt-4o-mini, gpt-4o, etc.)
  - anthropic → ChatAnthropic (claude-sonnet, claude-haiku, etc.)
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from src.config.tenant_config import TenantConfig


def create_llm(tenant_config: TenantConfig) -> BaseChatModel:
    """Create an LLM instance based on tenant config.

    The provider is determined by the `llm.provider` field in config.yaml.
    Each provider maps to a LangChain chat model class.
    """
    cfg = tenant_config.llm
    provider = cfg.provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        f"Supported: openai, anthropic"
    )
