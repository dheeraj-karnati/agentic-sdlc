"""Centralized LLM factory — supports Google, Groq, OpenRouter, Ollama, Cerebras.

All providers use the OpenAI-compatible API format via the openai SDK.
Includes automatic fallback chain and JSON parsing helpers.
"""

import json
import logging
import os

from openai import AsyncOpenAI

from src.config import settings

logger = logging.getLogger(__name__)

PROVIDERS = {
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GOOGLE_AI_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "default_model": "llama-3.3-70b",
    },
    "ollama": {
        "base_url": None,
        "api_key_env": None,
        "default_model": "qwen2.5-coder:14b",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "google/gemini-2.5-flash-preview",
    },
}

# Fallback chain: try these in order if the primary provider fails
_FALLBACK_CHAIN = ["google", "groq", "cerebras", "openrouter", "ollama"]


def get_llm_client(provider: str | None = None) -> AsyncOpenAI:
    """Create an AsyncOpenAI client for the given provider."""
    provider = provider or settings.llm_provider
    config = PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unknown LLM provider: {provider}. Choose from: {list(PROVIDERS.keys())}")

    if provider == "ollama":
        return AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )

    # Try settings attribute first (loaded from .env by pydantic), then env var
    settings_attr = (config["api_key_env"] or "").lower()
    api_key = getattr(settings, settings_attr, "") or os.getenv(config["api_key_env"] or "", "")
    if not api_key:
        raise ValueError(
            f"API key not set for {provider}. "
            f"Set {config['api_key_env']} in .env"
        )
    return AsyncOpenAI(
        base_url=config["base_url"],
        api_key=api_key,
    )


def get_default_model(provider: str | None = None) -> str:
    """Get the default model for a provider."""
    provider = provider or settings.llm_provider
    return PROVIDERS.get(provider, {}).get("default_model", "gemini-2.5-flash")


async def llm_complete(
    prompt: str,
    system: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    response_format: dict | None = None,
) -> str:
    """Send a chat completion request. Falls back through provider chain on failure."""
    provider = provider or settings.llm_provider
    model = model or get_default_model(provider)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        client = get_llm_client(provider)

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # JSON mode for providers that support it
        if response_format and provider in ("google", "groq", "openrouter", "cerebras"):
            kwargs["response_format"] = response_format

        logger.info("LLM call: provider=%s model=%s tokens=%d", provider, model, max_tokens)
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.info("LLM response: provider=%s model=%s length=%d", provider, model, len(content))
        return content

    except Exception as e:
        logger.warning("LLM call failed with %s/%s: %s", provider, model, e)

        # Try fallback
        fallback = _get_fallback(provider)
        if fallback:
            logger.info("Falling back to %s", fallback)
            return await llm_complete(
                prompt, system,
                provider=fallback,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        raise


async def llm_complete_json(
    prompt: str,
    system: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.1,
) -> dict:
    """Get a JSON response from the LLM. Parses and returns a dict."""
    json_system = (system or "") + (
        "\n\nRespond ONLY with valid JSON. "
        "No markdown, no code fences, no explanation. "
        "Just the JSON object."
    )

    result = await llm_complete(
        prompt=prompt,
        system=json_system,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=8000,
    )

    # Clean response: strip markdown code fences if present
    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    if cleaned.startswith("json"):
        cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    return json.loads(cleaned)


def _get_fallback(current: str) -> str | None:
    """Get the next provider in the fallback chain."""
    try:
        idx = _FALLBACK_CHAIN.index(current)
        if idx < len(_FALLBACK_CHAIN) - 1:
            return _FALLBACK_CHAIN[idx + 1]
    except ValueError:
        pass
    return None


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


# ─── Legacy compatibility ───
# The old codebase uses get_llm() returning a LangChain BaseChatModel.
# Keep this for existing code that hasn't been migrated yet.

def get_llm(max_tokens: int = 8192):
    """Legacy: return a LangChain chat model for backward compatibility."""
    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            max_tokens=max_tokens,
        )

    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        num_predict=max_tokens,
        keep_alive="10m",
        timeout=600,
        format="json",
    )
