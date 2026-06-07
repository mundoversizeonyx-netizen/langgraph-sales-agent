from __future__ import annotations
from langchain_core.language_models import BaseChatModel
from src.config.tenant_config import TenantConfig
import os

def create_llm(tenant_config: TenantConfig) -> BaseChatModel:
    cfg = tenant_config.llm
    provider = cfg.provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=cfg.model, temperature=cfg.temperature, max_tokens=cfg.max_tokens)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=cfg.model, temperature=cfg.temperature, max_tokens=cfg.max_tokens)

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        from langchain_openai import ChatOpenAI

        mistral = ChatMistralAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        cloudflare = ChatOpenAI(
            model="@cf/mistral/mistral-7b-instruct-v0.1",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/v1",
            api_key=os.getenv("CLOUDFLARE_API_TOKEN"),
        )
        return mistral.with_fallbacks([cloudflare])

    if provider == "cloudflare":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/v1",
            api_key=os.getenv("CLOUDFLARE_API_TOKEN"),
        )

    raise ValueError(f"Proveedor desconocido: '{provider}'. Soportados: openai, anthropic, mistral, cloudflare")