"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings. Loaded from .env file via pydantic-settings."""

    # App
    app_env: str = "development"
    log_level: str = "DEBUG"

    # Database
    database_url: str = "postgresql+asyncpg://sdlc:sdlc_password@localhost:5432/agentic_sdlc"
    database_url_sync: str = "postgresql://sdlc:sdlc_password@localhost:5432/agentic_sdlc"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Object Storage (MinIO / S3)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "agentic-sdlc-artifacts"

    # LLM — primary provider
    llm_provider: str = "google"  # google, groq, cerebras, ollama, openrouter

    # Provider API keys (loaded from .env only, NEVER from shell env)
    google_ai_key: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Per-agent LLM provider overrides (empty = use default)
    ingest_llm_provider: str = ""
    discover_llm_provider: str = ""
    design_llm_provider: str = ""

    # Ollama (local LLM inference)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:14b"
    ollama_embed_model: str = "nomic-embed-text"

    # Embeddings
    embedding_provider: str = "ollama"  # ollama or fake

    # Preview Deployment (Prototype Agent)
    preview_provider: str = "local_dev"  # local_dev, local_docker, vercel, netlify, s3_static
    vercel_token: str = ""
    vercel_org_id: str = ""
    netlify_auth_token: str = ""
    docker_host: str = ""  # empty = local Docker socket

    # GitHub
    github_token: str = ""
    github_owner: str = ""

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "agentic-sdlc"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
