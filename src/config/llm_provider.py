from __future__ import annotations
from langchain_core.language_models import BaseChatModel
from src.config.tenant_config import TenantConfig

def create_llm(tenant_config: TenantConfig) -> BaseChatModel:
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

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if provider == "cloudflare":
        from langchain_openai import ChatOpenAI
        import os
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
            api_key=api_token,
        )

    raise ValueError(
        f"Proveedor LLM desconocido: '{provider}'. "
        f"Soportados: openai, anthropic, mistral, cloudflare"
    )
