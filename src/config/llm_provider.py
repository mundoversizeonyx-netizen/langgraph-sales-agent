from __future__ import annotations
from langchain_core.language_models import BaseChatModel
from src.config.tenant_config import TenantConfig
import os

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
        from langchain_openai import ChatOpenAI
        from langchain_core.runnables import RunnableLambda
        import httpx

        mistral = ChatMistralAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        cloudflare = ChatOpenAI(
            model="@cf/mistral/mistral-7b-instruct-v0.1",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
            api_key=api_token,
        )

        class MistralWithFallback:
            def __init__(self, primary, fallback):
                self.primary = primary
                self.fallback = fallback

            def invoke(self, *args, **kwargs):
                try:
                    return self.primary.invoke(*args, **kwargs)
                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        print("[LLM] Mistral rate limit - usando Cloudflare fallback")
                        return self.fallback.invoke(*args, **kwargs)
                    raise

            async def ainvoke(self, *args, **kwargs):
                try:
                    return await self.primary.ainvoke(*args, **kwargs)
                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        print("[LLM] Mistral rate limit - usando Cloudflare fallback")
                        return await self.fallback.ainvoke(*args, **kwargs)
                    raise

            def __getattr__(self, name):
                return getattr(self.primary, name)

        return MistralWithFallback(mistral, cloudflare)

    if provider == "cloudflare":
        from langchain_openai import ChatOpenAI
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